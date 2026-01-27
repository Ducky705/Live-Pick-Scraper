#!/usr/bin/env python3
"""
Run Audit Dry Run
=================
Fetches recent data (Telegram/Twitter) or uses cached data,
runs the full extraction pipeline (Dry Run),
and generates a comprehensive Markdown Audit Report.

Usage:
    python tools/run_audit_dry_run.py
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import TARGET_TELEGRAM_CHANNEL_ID, OUTPUT_DIR, LOG_DIR
from src.telegram_client import TelegramManager
from src.twitter_client import TwitterManager
from src.deduplicator import Deduplicator
from src.ocr_handler import extract_text_batch
from src.auto_processor import auto_select_messages
from src.utils import clean_text_for_ai
from src.extraction_pipeline import ExtractionPipeline

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("AuditRunner")


async def main():
    print("=" * 60)
    print("   AUDIT DRY RUN: Full Extraction & Reporting   ")
    print("=" * 60)

    # 1. SETUP
    load_dotenv()
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 2. FETCH DATA (Yesterday/Today)
    ET = timezone(timedelta(hours=-5))
    now_et = datetime.now(ET)
    target_date = now_et.strftime("%Y-%m-%d")

    print(f"\nTarget Date: {target_date} (ET)")

    # --- TELEGRAM ---
    from config import API_ID, API_HASH

    tg_msgs = []
    if API_ID and API_HASH and TARGET_TELEGRAM_CHANNEL_ID:
        tg = TelegramManager()
        if await tg.connect_client():
            target_ids = [
                tid.strip()
                for tid in TARGET_TELEGRAM_CHANNEL_ID.split(",")
                if tid.strip()
            ]
            logger.info(f"Fetching from Telegram channels: {target_ids}")
            tg_msgs = await tg.fetch_messages(target_ids, target_date)

    # --- TWITTER ---
    # tw = TwitterManager()
    # tw_msgs = await tw.fetch_tweets(target_date=target_date)
    tw_msgs = []  # Skip twitter for now to be fast, or uncomment if needed

    all_msgs = tg_msgs + tw_msgs

    # FALLBACK: If no live data, look for cached data
    if not all_msgs:
        logger.warning("No live messages found. Checking for cached raw data...")
        cached_file = os.path.join(OUTPUT_DIR, f"raw_messages_{target_date}.json")
        if os.path.exists(cached_file):
            with open(cached_file, "r") as f:
                all_msgs = json.load(f)
            logger.info(f"Loaded {len(all_msgs)} cached messages.")
        else:
            # Fallback to ANY raw message file for demo
            import glob

            files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "raw_messages_*.json")))
            if files:
                latest = files[-1]
                logger.info(f"Loading older cache: {latest}")
                with open(latest, "r") as f:
                    all_msgs = json.load(f)
            else:
                # Fallback to Golden Set if absolutely nothing
                logger.warning("No cache found. Using Golden Set for demonstration.")
                golden_path = os.path.join(
                    os.path.dirname(__file__), "../new_golden_set.json"
                )
                if os.path.exists(golden_path):
                    with open(golden_path, "r", encoding="utf-8") as f:
                        test_cases = json.load(f)
                        # Convert to message format
                        all_msgs = []
                        for case in test_cases:
                            all_msgs.append(
                                {
                                    "id": case["id"],
                                    "text": case["text"],
                                    "date": case["date"],
                                    "images": case.get("images", []),
                                    "channel_name": "GoldenSet",
                                    "author": "TestCapper",
                                }
                            )

    if not all_msgs:
        logger.error("No data available to audit.")
        return

    # 3. PROCESS
    logger.info("Deduplicating...")
    unique_msgs = Deduplicator.merge_messages(all_msgs)

    logger.info("Running OCR...")
    ocr_tasks = []
    for i, msg in enumerate(unique_msgs):
        msg["ocr_texts"] = []
        images = msg.get("images", []) or (
            [msg.get("image")] if msg.get("image") else []
        )
        if msg.get("do_ocr") and images:
            for img in images:
                ocr_tasks.append((i, img))

    if ocr_tasks:
        results = extract_text_batch([t[1] for t in ocr_tasks])
        for t_idx, text_result in enumerate(results):
            original_idx = ocr_tasks[t_idx][0]
            if text_result and not text_result.startswith("[Error"):
                cleaned = clean_text_for_ai(text_result)
                unique_msgs[original_idx]["ocr_texts"].append(cleaned)
                unique_msgs[original_idx]["ocr_text"] = "\n".join(
                    unique_msgs[original_idx]["ocr_texts"]
                )

    logger.info("Classifying...")
    classified_msgs = auto_select_messages(unique_msgs, use_ai=True)
    selected_msgs = [m for m in classified_msgs if m.get("selected")]

    if not selected_msgs:
        logger.warning("No picks selected! The report will be empty.")
        # Force select all for audit purposes if classification filters everything
        selected_msgs = unique_msgs[:5]
        logger.info(
            f"Forcing selection of first {len(selected_msgs)} messages for audit."
        )

    # 4. RUN PIPELINE (Generates Report)
    logger.info("Running Extraction Pipeline...")
    ExtractionPipeline.run(selected_msgs, target_date)

    report_path = os.path.join(OUTPUT_DIR, f"verification_report_{target_date}.md")

    print("\n" + "=" * 60)
    print("   AUDIT COMPLETE   ")
    print("=" * 60)
    if os.path.exists(report_path):
        print(f"Report generated: {report_path}")
        print("Review this file to see Raw Source vs. Parsed Picks for every message.")
    else:
        print("Report generation failed.")


if __name__ == "__main__":
    asyncio.run(main())
