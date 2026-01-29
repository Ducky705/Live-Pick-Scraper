import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.telegram_client import TelegramManager

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TextScraper")

# Configuration
TARGET_CHANNELS = [
    -1001900292133,  # CAPPERS FREE
    -1002066008165,  # CAPPERS PICKS
    -1001560546587,  # Cappers leaked
]
DAYS_BACK = 3
MIN_TEXT_LENGTH = 15
KEYWORDS = [
    r"\b(ML|moneyline)\b",
    r"\b(o|u|over|under)\s*\d",
    r"\bunits?\b",
    r"[+-]\d{3}",  # American odds like -110, +150
    r"\b(spread|total|prop)\b",
    r"\d+\.?\d*u\b",  # 1u, 2.5u
]

OUTPUT_FILE = os.path.join(os.getcwd(), "data", "raw_test_candidates.json")


def is_betting_related(text):
    if not text or len(text) < MIN_TEXT_LENGTH:
        return False

    text_lower = text.lower()
    match_count = 0

    for pattern in KEYWORDS:
        if re.search(pattern, text_lower):
            match_count += 1

    # Require at least one strong keyword match
    return match_count >= 1


async def scrape_data():
    manager = TelegramManager()

    # Progress dummy
    manager.set_progress_callback(lambda p, s: print(f"[{p}%] {s}"))

    logger.info("Connecting to Telegram...")
    if not await manager.connect_client():
        logger.error("Failed to connect.")
        return

    all_candidates = []

    # Iterate dates
    start_date = datetime.now()
    dates_to_fetch = [(start_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DAYS_BACK)]

    logger.info(f"Targeting dates: {dates_to_fetch}")

    for date_str in dates_to_fetch:
        logger.info(f"Fetching messages for {date_str}...")

        # fetch_messages takes a list of IDs and a SINGLE date string
        messages = await manager.fetch_messages(TARGET_CHANNELS, date_str)

        logger.info(f"Fetched {len(messages)} raw messages.")

        for msg in messages:
            text = msg.get("text", "")

            # Smart Filtering
            if is_betting_related(text):
                # Clean up structure for storage
                clean_msg = {
                    "id": msg["id"],
                    "channel_id": msg.get(
                        "channel_id", "unknown"
                    ),  # Note: fetch_messages might not set this explicitly in dict, need to check
                    "date": msg["date"],
                    "text": text,
                    "images": msg.get("images", []),
                    "source": "Telegram",
                }
                all_candidates.append(clean_msg)

    # Dedup by ID
    seen = set()
    unique_candidates = []
    for c in all_candidates:
        if c["id"] not in seen:
            seen.add(c["id"])
            unique_candidates.append(c)

    logger.info(f"Scrape Complete. Found {len(unique_candidates)} betting-relevant messages.")

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_candidates, f, indent=2, default=str)

    logger.info(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(scrape_data())
