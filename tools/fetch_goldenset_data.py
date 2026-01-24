#!/usr/bin/env python3
"""
Fetch Goldenset Data
====================
Fetches fresh data from BOTH Telegram and Twitter to populate the cache
for Goldenset generation.
"""

import os
import sys
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
from dotenv import load_dotenv

load_dotenv()

from config import TARGET_TELEGRAM_CHANNEL_ID, TEMP_IMG_DIR
from src.telegram_client import TelegramManager
from src.twitter_client import TwitterManager
from src.deduplicator import Deduplicator
from src.ocr_handler import extract_text_batch
from src.utils import clean_text_for_ai
from src.auto_processor import auto_select_messages

CACHE_DIR = PROJECT_ROOT / "data" / "cache"


def save_cache(name, data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Saved {name} to {path}")


async def main():
    print("=== FETCHING FRESH DATA (TELEGRAM + TWITTER) ===")

    # 1. Clear Cache
    # We won't delete the directory, but we will overwrite files.

    # 2. Date Setup (Yesterday ET)
    ET = timezone(timedelta(hours=-5))
    now_et = datetime.now(ET)
    yesterday_et = now_et - timedelta(days=1)
    target_date = yesterday_et.strftime("%Y-%m-%d")
    print(f"Target Date: {target_date} (ET)")

    # 3. Fetch Telegram
    tg_msgs = []
    print("\n--- Telegram ---")
    if TARGET_TELEGRAM_CHANNEL_ID:
        try:
            tg = TelegramManager()
            await tg.connect_client()
            print(f"Fetching from {TARGET_TELEGRAM_CHANNEL_ID}...")
            tg_msgs = await tg.fetch_messages([TARGET_TELEGRAM_CHANNEL_ID], target_date)
            print(f"Fetched {len(tg_msgs)} Telegram messages")
        except Exception as e:
            print(f"Telegram Error: {e}")
    else:
        print("Skipping Telegram (No Channel ID)")

    # 4. Fetch Twitter
    tw_msgs = []
    print("\n--- Twitter ---")
    try:
        tw = TwitterManager()
        # TwitterManager fetches from hardcoded list in src/twitter_client.py
        tw_msgs = await tw.fetch_tweets(target_date=target_date)
        print(f"Fetched {len(tw_msgs)} Tweets")
    except Exception as e:
        print(f"Twitter Error: {e}")

    # 5. Merge & Deduplicate
    all_msgs = tg_msgs + tw_msgs
    print(f"\nTotal Raw Messages: {len(all_msgs)}")

    if not all_msgs:
        print("No messages found! Exiting.")
        return

    unique_msgs = Deduplicator.merge_messages(all_msgs)
    print(f"After Deduplication: {len(unique_msgs)}")

    # 6. Auto-Select (Classification)
    # We want to filter for likely picks before OCR to save time/resources,
    # OR we can just OCR everything since this is a "goldenset" generator and we want high quality.
    # Let's OCR everything that has images.

    # 7. OCR
    print("\n--- Running OCR ---")
    ocr_tasks = []
    for i, msg in enumerate(unique_msgs):
        msg["ocr_texts"] = []  # Init

        images = msg.get("images", [])
        if not images and msg.get("image"):
            images = [msg["image"]]

        if images:
            for img_path in images:
                # Ensure path is absolute or resolvable
                if img_path.startswith("/static"):
                    # Assuming it's in TEMP_IMG_DIR
                    fname = os.path.basename(img_path)
                    fpath = os.path.join(TEMP_IMG_DIR, fname)
                    ocr_tasks.append((i, fpath))
                else:
                    ocr_tasks.append((i, img_path))

    ocr_results_map = {}  # path -> result

    if ocr_tasks:
        paths = [t[1] for t in ocr_tasks]
        print(f"Processing {len(paths)} images...")
        results = extract_text_batch(paths)

        for idx, (t_idx, path) in enumerate(zip([t[0] for t in ocr_tasks], paths)):
            text = results[idx]
            if text and not text.startswith("[Error"):
                cleaned = clean_text_for_ai(text)

                # Attach to message
                unique_msgs[t_idx]["ocr_texts"].append(cleaned)
                unique_msgs[t_idx]["ocr_text"] = "\n".join(
                    unique_msgs[t_idx]["ocr_texts"]
                )

                # Store in map for cache file
                ocr_results_map[path] = {
                    "msg_id": unique_msgs[t_idx].get("id"),
                    "text": cleaned,
                    "length": len(cleaned),
                }

    print("OCR Complete.")

    # 8. Re-run Selection with OCR data (Better classification)
    print("Running AI Classification...")
    classified = auto_select_messages(unique_msgs, use_ai=True)

    # 9. Save to Cache
    # structure expected by generate_goldenset.py:
    # messages.json -> {"messages": [...]}
    # ocr_results.json -> {"results": {path: {...}}}

    save_cache(
        "messages",
        {
            "messages": classified,
            "date": target_date,
            "source": "Fetch Goldenset Script",
        },
    )

    save_cache(
        "ocr_results", {"results": ocr_results_map, "count": len(ocr_results_map)}
    )

    print("\nDONE! Data cached.")
    print(f"Messages: {len(classified)}")
    print(f"Selected as Picks: {sum(1 for m in classified if m.get('selected'))}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal Error: {e}")
        import traceback

        traceback.print_exc()
