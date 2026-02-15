import json
import logging
import os
import sys
import asyncio
from datetime import datetime, timedelta

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR, LOG_DIR
from src.auto_processor import auto_select_messages
from src.extraction_pipeline import ExtractionPipeline
from src.grader import grade_picks
from src.score_fetcher import fetch_scores_for_date
from src.grading.constants import LEAGUE_ALIASES_MAP

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

async def main():
    print("=" * 50)
    print("   PARSER DEBUG LOOP   ")
    print("=" * 50)

    # 1. LOAD DEBUG MESSAGES
    # Use comprehensive set if available
    comp_file = os.path.join(OUTPUT_DIR, "comprehensive_debug_set.json")
    debug_file = os.path.join(OUTPUT_DIR, "debug_msgs.json")
    
    target_file = comp_file if os.path.exists(comp_file) else debug_file
    
    if not os.path.exists(target_file):
        # Fallback
        target_file = debug_file
        if not os.path.exists(target_file):
             logging.error(f"Debug file not found: {target_file}")
             return

    logging.info(f"Loading messages from {target_file}...")
    with open(target_file, "r", encoding="utf-8") as f:
        unique_msgs = json.load(f)

    logging.info(f"Loaded {len(unique_msgs)} messages.")
    
    # LIMIT FOR DEBUGGING SPEED
    # unique_msgs = unique_msgs[:10]
    logging.info(f"Processing all {len(unique_msgs)} messages.")

    # 2. AUTO-CLASSIFICATION (WITH CACHING)
    logging.info("Classifying messages...")
    
    # Caching Logic for Classification
    class_cache_file = os.path.join(OUTPUT_DIR, "classification_cache.json")
    class_cache = {}
    if os.path.exists(class_cache_file):
        try:
            with open(class_cache_file, "r") as f:
                class_cache = json.load(f)
        except:
             pass
    
    # Filter messages that need classification
    msgs_to_classify = []
    cached_msgs = []
    
    for m in unique_msgs:
        mid = str(m.get("id"))
        if mid in class_cache:
            # Use cached result
            m["selected"] = class_cache[mid].get("selected", False)
            m["rejection_reason"] = class_cache[mid].get("rejection_reason")
            cached_msgs.append(m)
        else:
            msgs_to_classify.append(m)
            
    if msgs_to_classify:
        logging.info(f"Classifying {len(msgs_to_classify)} new messages via AI...")
        classified_new = auto_select_messages(msgs_to_classify, use_ai=True)
        
        # Update Cache
        for m in classified_new:
            mid = str(m.get("id"))
            class_cache[mid] = {
                "selected": m.get("selected", False),
                "rejection_reason": m.get("rejection_reason")
            }
        
        # Save Cache
        with open(class_cache_file, "w") as f:
            json.dump(class_cache, f, indent=2)
            
        classified_msgs = cached_msgs + classified_new
    else:
        logging.info("All messages classified from cache.")
        classified_msgs = cached_msgs

    # DEBUG 10891: Write status to file
    with open("debug_10891_status.txt", "w", encoding="utf-8") as f:
        m10891 = next((m for m in classified_msgs if str(m.get("id")) == "10891"), None)
        if m10891:
            f.write(f"10891 FOUND in classified_msgs.\n")
            f.write(f"Selected: {m10891.get('selected')}\n")
            f.write(f"Rejection: {m10891.get('rejection_reason')}\n")
            f.write(f"Text Content: {m10891.get('text', '')[:100]}...\n")
        else:
            f.write("10891 NOT FOUND in classified_msgs.\n")
            
        # Check duplicate
        m12793 = next((m for m in classified_msgs if str(m.get("id")) == "12793"), None)
        if m12793:
            f.write(f"12793 (Dup) FOUND. Selected: {m12793.get('selected')}\n")
        else:
             f.write("12793 NOT FOUND.\n")

    # Filter only "selected" messages (likely picks)
    selected_msgs = [m for m in classified_msgs if m.get("selected")]
    logging.info(f"Selected {len(selected_msgs)} likely pick messages out of {len(classified_msgs)}.")
    
    # DEBUG: Filter to ONLY 10891/12793/2015115794125090973
    # selected_msgs = [m for m in selected_msgs if str(m.get("id")) in ["10891", "12793", "2015115794125090973"]]
    # logging.info(f"DEBUG: Processing ONLY {len(selected_msgs)} messages (10891 et al).")

    # 3. EXTRACTION
    target_date = "2026-02-08" # Hardcoded for this loop
    logging.info(f"Extracting picks for date: {target_date}...")
    
    # USE CACHE FOR EXTRACTION
    extraction_cache = os.path.join(OUTPUT_DIR, "extraction_cache.json")
    picks = ExtractionPipeline.run(selected_msgs, target_date, extraction_cache_path=extraction_cache)
    logging.info(f"Extracted {len(picks)} picks.")

    # 4. GRADING
    logging.info("Grading picks...")
    
    # OPTIMIZATION: Extract leagues from picks to fetch only what's needed
    relevant_leagues = set()
    for p in picks:
        lg = (p.get("league") or p.get("lg") or "").lower()
        if lg:
            relevant_leagues.add(LEAGUE_ALIASES_MAP.get(lg, lg))

    scores = fetch_scores_for_date(
        target_date,
        requested_leagues=list(relevant_leagues) if relevant_leagues else None,
    )
    
    picks = grade_picks(picks, scores)

    # 5. RESULTS AND ANALYSIS
    wins = sum(1 for p in picks if p.get("result") == "Win")
    losses = sum(1 for p in picks if p.get("result") == "Loss")
    pending = sum(1 for p in picks if p.get("result") in ["Pending", "Pending/Unknown", None, ""])
    errors = sum(1 for p in picks if p.get("result") == "Error")

    print("\n" + "=" * 50)
    print(f"   RESULTS (Wins: {wins}, Losses: {losses}, Pending: {pending}, Errors: {errors})   ")
    print("=" * 50)

    # Print any unexpected Errors for immediate attention
    if errors > 0:
        print("\n--- ERRORS ---")
        for p in picks:
            if p.get("result") == "Error":
                print(f"Pick: {p.get('pick')}")
                print(f"Error: {p.get('score_summary')}")
                print("-" * 20)

    # Save results
    output_file = os.path.join(OUTPUT_DIR, "debug_loop_results.json")
    with open(output_file, "w") as f:
        json.dump(picks, f, indent=2)
    logging.info(f"Results saved to {output_file}")
    
    # Analyze Potential Missed Picks (Ads/Promo detection check)
    print("\n--- ANALYZING REJECTED MESSAGES (ADS/NOISE) ---")
    rejected_msgs = [m for m in classified_msgs if not m.get("selected")]
    
    potential_misses = []
    for m in rejected_msgs:
        # Simple heuristic: if it has digits and keywords, maybe it was a miss?
        text = m.get("text", "") or ""
        ocr = m.get("ocr_text", "") or ""
        content = (text + "\n" + ocr).lower()
        
        # Check for strong pick signals in rejected messages
        if any(kw in content for kw in ["units", "odds", "-110", "+100", "over", "under"]) and \
           any(kw in content for kw in ["patriots", "seahawks", "nfl", "nba"]):
             potential_misses.append(m)

    print(f"Found {len(potential_misses)} rejected messages that look like they might have picks.")
    for i, m in enumerate(potential_misses[:5]):
        print(f"\n[Potential Miss #{i+1}] Reason: {m.get('rejection_reason', 'Unknown')}")
        print(f"Text snippet: {(m.get('text') or m.get('ocr_text') or '')[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
