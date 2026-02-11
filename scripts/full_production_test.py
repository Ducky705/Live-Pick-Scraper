#!/usr/bin/env python3
"""
Full Production Test Script
---------------------------
Performs a FRESH, read-only validation of the entire pipeline:
1. Cleans up any existing cache for the target date (Yesterday ET).
2. Scrapes data from Yesterday (ET) from all sources (Telegram, Twitter, Discord).
3. Runs Extraction Pipeline (AI).
4. Grades the picks against live scores.
5. Generates a diagnostic report AND prints a detailed Raw vs Parsed comparison.

Usage:
    python scripts/full_production_test.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Add project root AND src to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "src"))

from src.config import DATA_DIR, OUTPUT_DIR, TARGET_DISCORD_CHANNEL_ID
from dotenv import load_dotenv

# Clients
from src.telegram_client import tg_manager
from src.twitter_client import twitter_manager
from src.discord_client import discord_manager

# Pipeline
from src.extraction_pipeline import ExtractionPipeline
from src.score_fetcher import async_fetch_scores_for_date
from src.grading.engine import GraderEngine
from src.grading.parser import PickParser

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(DATA_DIR, "logs", "full_production_test.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("FullTest")

load_dotenv()

def get_yesterday_et():
    """Calculate 'Yesterday' in Eastern Time."""
    # US-001: Explicitly define ET as UTC-5 (Standard) or UTC-4 (DST)
    # For simplicity in this script, we rely on server time or fixed offset
    # Better: Use pytz if available, but staying dependency-light
    ET_OFFSET = timezone(timedelta(hours=-5))
    now_et = datetime.now(ET_OFFSET)
    yesterday = now_et - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")

def cleanup_cache(target_date):
    """Force a fresh run by removing existing caches."""
    logger.info(f"Cleaning up caches for {target_date}...")
    
    files_to_remove = [
        os.path.join(DATA_DIR, f"picks_cache_{target_date}.json"),
        os.path.join(DATA_DIR, f"debug_extraction_log_{target_date}.json")
    ]
    
    for fpath in files_to_remove:
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                logger.info(f"Removed cache file: {fpath}")
            except Exception as e:
                logger.warning(f"Failed to remove {fpath}: {e}")
        else:
            logger.info(f"Cache file not found (good): {fpath}")

async def scrape_all_sources(target_date):
    """Fetch messages from all configured sources."""
    logger.info(f"--- Starting Scraping for Date: {target_date} ---")
    
    all_messages = []
    
    # 1. Telegram
    try:
        t0 = time.time()
        logger.info("Initializing Telegram...")
        authorized = await tg_manager.connect_client()
        if authorized:
            channels = await tg_manager.get_channels()
            logger.info(f"Telegram: Found {len(channels)} channels.")
            
            # Extract IDs
            channel_ids = [c["id"] for c in channels]
            if channel_ids:
                msgs = await tg_manager.fetch_messages(channel_ids, target_date)
                logger.info(f"Telegram: Fetched {len(msgs)} messages in {time.time() - t0:.2f}s")
                all_messages.extend(msgs)
            else:
                logger.warning("Telegram: No channels found.")
        else:
            logger.error("Telegram: Not authorized. Skipping.")
    except Exception as e:
        logger.error(f"Telegram Scraping Failed: {e}", exc_info=True)

    # 2. Twitter
    try:
        t0 = time.time()
        logger.info("Initializing Twitter...")
        # Fetch tweets - target_date handles 'since' query
        tweets = await twitter_manager.fetch_tweets(target_date, limit=200) 
        logger.info(f"Twitter: Fetched {len(tweets)} tweets in {time.time() - t0:.2f}s")
        all_messages.extend(tweets)
    except Exception as e:
        logger.error(f"Twitter Scraping Failed: {e}", exc_info=True)

    # 3. Discord
    try:
        t0 = time.time()
        logger.info("Initializing Discord...")
        # Fetch IDs from env or config
        channel_ids_str = os.getenv("DISCORD_CHANNEL_IDS", "")
        discord_ids = [cid.strip() for cid in channel_ids_str.split(",") if cid.strip()]
        
        # Fallback to single target if list is empty
        if not discord_ids and TARGET_DISCORD_CHANNEL_ID:
            discord_ids = [TARGET_DISCORD_CHANNEL_ID]
            
        if discord_ids:
            logger.info(f"Discord: Target channels: {discord_ids}")
            d_msgs = []
            for cid in discord_ids:
                m = await discord_manager.fetch_messages(cid, limit=50) # Limit per channel
                d_msgs.extend(m)
            
            logger.info(f"Discord: Fetched {len(d_msgs)} messages in {time.time() - t0:.2f}s")
            all_messages.extend(d_msgs)
        else:
            logger.warning("Discord: No channel IDs configured (DISCORD_CHANNEL_IDS).")
    except Exception as e:
        logger.error(f"Discord Scraping Failed: {e}", exc_info=True)

    return all_messages

async def run_grading(picks, target_date):
    """Run grading engine on extracted picks."""
    logger.info(f"--- Starting Grading for {target_date} ---")
    
    # Fetch Scores (Async)
    scores = await async_fetch_scores_for_date(target_date)
    if not scores:
        logger.error("No scores found for date. Cannot grade.")
        return [], {"WIN": 0, "LOSS": 0, "PUSH": 0, "VOID": 0, "PENDING": 0, "ERROR": 0}

    engine = GraderEngine(scores)
    graded_results = []
    stats = {"WIN": 0, "LOSS": 0, "PUSH": 0, "VOID": 0, "PENDING": 0, "ERROR": 0}

    for p in picks:
        try:
            # Parse
            pick_text = p.get("pick", "")
            league = p.get("league", "Other")
            
            parsed = PickParser.parse(pick_text, league, target_date)
            grade_result = engine.grade(parsed)
            
            # Record result
            status = grade_result.grade.name # Enum to str
            p["grade"] = status
            p["score_summary"] = grade_result.score_summary
            p["grading_details"] = grade_result.details
            
            if status in stats:
                stats[status] += 1
            else:
                stats["ERROR"] += 1
                
        except Exception as e:
            p["grade"] = "ERROR"
            p["grading_error"] = str(e)
            stats["ERROR"] += 1
            
        graded_results.append(p)

    return graded_results, stats

def analyze_and_print_comparison(target_date):
    """
    Reads the debug log and prints a detailed Raw vs Parsed comparison.
    """
    debug_file = os.path.join(DATA_DIR, f"debug_extraction_log_{target_date}.json")
    if not os.path.exists(debug_file):
        logger.warning(f"No debug extraction log found at {debug_file}")
        return None

    try:
        with open(debug_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        print("\n" + "="*80)
        print(f"RAW VS PARSED COMPARISON (First 5 Non-Empty Batches)")
        print("="*80)

        count = 0
        for entry in data:
            parsed = entry.get("parsed_picks", [])
            raw = entry.get("raw_response", "")
            
            # Only show if we have parsed picks or if raw is non-empty but parsed is empty (missing info)
            if parsed or (raw.strip() and len(raw) > 50): 
                if count >= 5:
                    break
                    
                print(f"\n--- Batch {entry.get('batch_index')} ---")
                print(f"[RAW AI OUTPUT]:")
                # Truncate raw if too long for console
                clean_raw = raw.strip()
                if len(clean_raw) > 500:
                    print(clean_raw[:500] + "... [TRUNCATED]")
                else:
                    print(clean_raw)
                    
                print(f"\n[PARSED JSON]:")
                print(json.dumps(parsed, indent=2, default=str))
                print("-" * 40)
                
                count += 1
        
        print("\n" + "="*80)
        
        # Return stats like the dry run script
        stats = {
            "total_batches": len(data),
            "total_raw_items": 0,
            "total_parsed_items": 0,
            "empty_responses": 0,
            "parse_rate": 0.0,
            "batches_with_discrepancy": []
        }
        
        for entry in data:
            raw = entry.get("raw_response", "")
            parsed = entry.get("parsed_picks", [])
            
            try:
                # Naive raw item count
                clean_raw = raw.replace("```json", "").replace("```", "").strip()
                # Attempt to find number of "pick" keys
                stats["total_raw_items"] += raw.count('"pick":')
            except:
                pass

            stats["total_parsed_items"] += len(parsed)
            if not parsed and raw.strip():
                stats["empty_responses"] += 1

        if stats["total_raw_items"] > 0:
            stats["parse_rate"] = (stats["total_parsed_items"] / stats["total_raw_items"]) * 100
            
        return stats, data

    except Exception as e:
        logger.error(f"Failed to analyze extraction quality: {e}")
        return None

def generate_report(target_date, messages, picks, graded_picks, stats, time_taken, extraction_analysis=None):
    """Generate Markdown report."""
    report_path = os.path.join(OUTPUT_DIR, f"full_production_test_{target_date}.md")
    
    total_graded = stats["WIN"] + stats["LOSS"] + stats["PUSH"]
    accuracy = (stats["WIN"] / total_graded * 100) if total_graded > 0 else 0.0
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Full Production Test Report - {target_date}\n\n")
        f.write(f"**generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 1. Executive Summary\n")
        f.write(f"- **Target Date:** {target_date} (Yesterday ET)\n")
        f.write(f"- **Total Time:** {time_taken:.2f}s\n")
        f.write(f"- **Messages Scraped:** {len(messages)}\n")
        f.write(f"- **Picks Extracted:** {len(picks)}\n")
        f.write(f"- **Gradable Picks:** {total_graded}\n")
        f.write(f"- **Accuracy:** {accuracy:.2f}%\n\n")
        
        # New Section: Extraction Quality
        if extraction_analysis:
            estats, raw_data = extraction_analysis
            f.write("## 2. Extraction Quality (Raw vs Parsed)\n")
            f.write(f"- **Total Batches:** {estats['total_batches']}\n")
            f.write(f"- **Potential Raw Items:** {estats['total_raw_items']}\n")
            f.write(f"- **Successfully Parsed:** {estats['total_parsed_items']}\n")
            f.write(f"- **Approx Parse Rate:** {estats['parse_rate']:.2f}%\n")
            f.write(f"- **Empty Responses (No picks found):** {estats['empty_responses']}\n\n")
            
            f.write("### Raw vs Parsed Comparison (Sample)\n")
            f.write("Showing first 10 batches with picks:\n\n")
            
            count = 0
            for entry in raw_data:
                if entry.get("parsed_picks") and count < 10:
                    f.write(f"**Batch {entry['batch_index']}**\n")
                    f.write("<details>\n<summary>See Raw Output</summary>\n\n")
                    f.write("```json\n")
                    f.write(entry['raw_response'])
                    f.write("\n```\n</details>\n\n")
                    
                    f.write("**Parsed Output:**\n")
                    f.write("```json\n")
                    f.write(json.dumps(entry['parsed_picks'], indent=2, default=str))
                    f.write("\n```\n\n")
                    f.write("---\n\n")
                    count += 1
            f.write("\n")

        f.write("## 3. Grading Statistics\n")
        f.write("| Grade | Count |\n")
        f.write("| :--- | :---: |\n")
        for k, v in stats.items():
            f.write(f"| {k} | {v} |\n")
        f.write("\n")
        
        f.write("## 4. Performance Breakdown\n")
        perc = (len(picks) / len(messages) * 100) if messages else 0
        f.write(f"- **Extraction Yield:** {perc:.2f}% (Picks/Messages)\n")
        f.write("\n")
        
        f.write("## 5. Missed/Error Cases (Diagnosis)\n")
        errors = [p for p in graded_picks if p.get("grade") in ["ERROR", "PENDING", "VOID"]]
        if errors:
            f.write(f"Found {len(errors)} items that could not be graded definitively.\n\n")
            f.write("| Pick | League | Grade | Reason/Details |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for e in errors:
                reason = e.get("grading_details") or e.get("grading_error") or "Unknown"
                pick_clean = str(e.get('pick')).replace("|", r"\|")
                grade = e.get("grade")
                f.write(f"| {pick_clean} | {e.get('league')} | {grade} | {reason} |\n")
        else:
            f.write("No grading errors found.\n")
            
        f.write("\n## 6. Detailed Pick List\n")
        f.write("| Capper | League | Pick | Odds | Grade | Summary |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        
        for p in graded_picks:
            capper = p.get("capper_name", "Unknown")
            grade = p.get("grade", "N/A")
            summary = p.get("score_summary", "")
            pick_val = str(p.get("pick", "")).replace("|", r"\|") # Escape pipe for markdown table
            
            # Add emoji
            icon = ""
            if grade == "WIN": icon = "✅ "
            elif grade == "LOSS": icon = "❌ "
            elif grade == "PUSH": icon = "➖ "
            
            f.write(f"| {capper} | {p.get('league')} | {pick_val} | {p.get('odds')} | {icon}{grade} | {summary} |\n")
            
    return report_path

async def main():
    start_time = time.time()
    
    # 0. Date Setup
    target_date = get_yesterday_et()
    logger.info(f"Target Date (Yesterday ET): {target_date}")
    
    # Clean cache
    cleanup_cache(target_date)
    
    # 1. Scrape
    messages = await scrape_all_sources(target_date)
    if not messages:
        logger.error("No messages found from any source. Aborting.")
        return

    # 2. Extract
    logger.info("--- Starting Extraction Pipeline ---")
    t_extract_start = time.time()
    
    try:
        # Use ExtractionPipeline with caching disabled in effect by previous cleanup
        picks = ExtractionPipeline.run(messages, target_date=target_date)
        # Verify if picks empty - if so, try to read from debug log just in case pipeline crashed but saved log?
        # No, pipeline returns picks.
    except Exception as e:
        logger.error(f"Extraction Pipeline Failed: {e}", exc_info=True)
        return
        
    logger.info(f"Extraction Complete. Found {len(picks)} picks in {time.time() - t_extract_start:.2f}s")
    
    # 3. Grade
    graded_picks, stats = await run_grading(picks, target_date)
    
    # 4. Analysis & Report
    extraction_analysis = analyze_and_print_comparison(target_date)
    
    total_time = time.time() - start_time
    report_file = generate_report(target_date, messages, picks, graded_picks, stats, total_time, extraction_analysis)
    
    print("\n" + "="*60)
    print(f"FULL PRODUCTION TEST COMPLETE")
    print(f"Report Generated: {report_file}")
    
    # Save picks cache
    cache_path = os.path.join(DATA_DIR, f"picks_cache_{target_date}.json")
    with open(cache_path, "w") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"Picks Cached: {cache_path}")

    print("="*60)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Aborted by user.")
