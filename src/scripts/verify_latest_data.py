
import json
import logging
import os
import sys
from datetime import datetime

# Setup path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "src"))

# from src.extraction_pipeline import ExtractionPipeline  # Moved to local import
from src.supabase_client import get_matcher_candidates, get_supabase
from src.capper_matcher import capper_matcher

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Verification")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def verify_capper_matching(picks):
    """
    Simulates the capper matching process without writing to DB.
    """
    logger.info("Verifying Capper Matching (Dry Run)...")
    
    # 1. Fetch Candidates (ReadOnly)
    try:
        candidates = get_matcher_candidates()
        logger.info(f"Loaded {len(candidates)} capper candidates from DB.")
    except Exception as e:
        logger.error(f"Failed to load candidates from DB: {e}")
        candidates = []

    active_candidates = [c for c in candidates if c["is_active"]]
    
    results = []
    
    for p in picks:
        raw_name = p.get("capper_name", "Unknown")
        if raw_name.lower() == "unknown":
            results.append({
                "pick": p,
                "match_type": "UNKNOWN",
                "matched_name": None,
                "status": "MISSING_NAME"
            })
            continue
            
        clean_lookup = str(raw_name).strip()
        
        # Simulation Logic identical to supabase_client.py but without writes
        
        # 1. Smart Match Active
        match = capper_matcher.smart_match(clean_lookup, active_candidates)
        
        if match:
            results.append({
                "pick": p,
                "match_type": "EXISTING_ACTIVE",
                "matched_name": match["name"],
                "score": match["score"],
                "status": "MATCHED"
            })
            continue
            
        # 2. Smart Match All
        match_all = capper_matcher.smart_match(clean_lookup, candidates)
        
        if match_all:
            results.append({
                "pick": p,
                "match_type": "EXISTING_INACTIVE",
                "matched_name": match_all["name"],
                "score": match_all["score"],
                "status": "MATCHED"
            })
            continue
            
        # 3. New Capper
        results.append({
            "pick": p,
            "match_type": "NEW_CAPPER",
            "matched_name": clean_lookup,
            "status": "WOULD_CREATE"
        })
        
    return results

def main():
    # 1. Load Data
    data_file = os.path.join(root_dir, "src", "data", "output", "debug_msgs.json")
    if not os.path.exists(data_file):
        logger.error(f"File not found: {data_file}")
        return
        
    logger.info(f"Loading messages from {data_file}...")
    messages = load_json(data_file)
    logger.info(f"Loaded {len(messages)} messages.")
    
    # 2. Run Pipeline
    logger.info("Running Extraction Pipeline...")
    # Use a fixed date for consistency or use today's date
    target_date = datetime.now().strftime("%Y-%m-%d")
    
    # We only process messages that have been "selected" (or we force selection for test)
    # The debug_msgs.json usually contains all messages, some might not be selected.
    # Let's filter for selected ones if the field exists, or process all if mainly testing.
    selected_msgs = [m for m in messages if m.get("selected")]
    if not selected_msgs:
        logger.info("No messages marked 'selected' in debug file. Using all messages with text/images.")
        selected_msgs = [m for m in messages if m.get("text") or m.get("images")]
    
    logger.info(f"Processing {len(selected_msgs)} messages...")
    
    try:
        # Import groq_client (now urllib-based)
        import src.groq_client as groq 
        from src.extraction_pipeline import ExtractionPipeline
        
        # Override Groq client internally if needed, but our patch handles it
        picks = ExtractionPipeline.run(selected_msgs, target_date)
            
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}", exc_info=True)
        return

    logger.info(f"Extracted {len(picks)} picks.")
    
    # 3. Verify Capper Matching
    match_results = verify_capper_matching(picks)
    
    # 4. Generate Report
    report_file = os.path.join(root_dir, "src", "data", "output", f"verification_latest_report_{target_date}.md")
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Verification Report: Latest Data (Dry Run)\n\n")
        f.write(f"**Date:** {target_date}\n")
        f.write(f"**Mode:** Simulation (Offline Cache)\n")
        f.write(f"**Input Messages:** {len(selected_msgs)}\n")
        f.write(f"**Extracted Picks:** {len(picks)}\n\n")
        
        f.write("## Capper Matching Analysis\n\n")
        
        # Group by status
        counts = {"MATCHED": 0, "WOULD_CREATE": 0, "MISSING_NAME": 0}
        for r in match_results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            
        f.write(f"- **Matched Existing:** {counts['MATCHED']}\n")
        f.write(f"- **New Cappers (To Create):** {counts['WOULD_CREATE']}\n")
        f.write(f"- **Missing Name (Unknown):** {counts['MISSING_NAME']}\n\n")
        
        f.write("### New Capper Detections (Verify These)\n")
        new_cappers = [r for r in match_results if r["status"] == "WOULD_CREATE"]
        if new_cappers:
            for r in new_cappers:
                p = r["pick"]
                f.write(f"- **{r['matched_name']}** (from '{p.get('capper_name')}')\n")
                f.write(f"  - Pick: {p.get('pick')}\n")
                f.write(f"  - Msg ID: {p.get('message_id')}\n")
        else:
            f.write("None.\n")
            
        f.write("\n### Matched Examples\n")
        matched = [r for r in match_results if r["status"] == "MATCHED"][:10]
        for r in matched:
            f.write(f"- '{r['pick'].get('capper_name')}' -> **{r['matched_name']}** ({r['match_type']})\n")
            
        f.write("\n## All Extracted Picks\n\n")
        f.write("| Capper | Sport | Pick | Odds | Units |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for p in picks:
             f.write(f"| {p.get('capper_name')} | {p.get('league')} | {p.get('pick')} | {p.get('odds')} | {p.get('units')} |\n")
             
    logger.info(f"Report saved to {report_file}")
    print(f"REPORT_PATH: {report_file}")

if __name__ == "__main__":
    main()
