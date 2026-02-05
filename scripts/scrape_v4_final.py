import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta

# Setup
sys.path.insert(0, os.path.abspath("."))
from config import (
    TARGET_TELEGRAM_CHANNEL_ID, 
    TARGET_DISCORD_CHANNEL_ID,
    DISCORD_TOKEN,
    API_ID,
    API_HASH
)

from src.telegram_client import tg_manager
from src.twitter_client import twitter_manager
from src.discord_client import discord_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ScraperFinal")

OUTPUT_FILE = "data/cache/fresh_benchmark_raw_final.json"

async def main():
    logger.info("Starting FINAL Benchmark Scrape (Deep History)...")
    
    results = {
        "telegram": [],
        "twitter": [],
        "discord": []
    }

    # 1. Telegram (Deep Fetch)
    if TARGET_TELEGRAM_CHANNEL_ID and API_ID and API_HASH:
        tg_channels = [ch.strip() for ch in TARGET_TELEGRAM_CHANNEL_ID.split(",") if ch.strip()]
        logger.info(f"Scraping Telegram Channels: {tg_channels}")
        
        try:
            connected = await tg_manager.connect_client()
            if connected:
                # Fetch back to Jan 1st 2026
                msgs = await tg_manager.fetch_messages(tg_channels, "2026-01-01")
                results["telegram"] = msgs
                logger.info(f"Got {len(msgs)} Telegram messages.")
            else:
                logger.error("Telegram Auth Failed")
        except Exception as e:
            logger.error(f"Telegram Scrape Failed: {e}")

    # 2. Twitter (Retry)
    logger.info("Scraping Twitter...")
    try:
        tweets = await twitter_manager.fetch_tweets(limit=100)
        results["twitter"] = tweets
        logger.info(f"Got {len(tweets)} Tweets.")
    except Exception as e:
        logger.error(f"Twitter Scrape Failed: {e}")

    # 3. Discord (We have enough, but fetch to be safe)
    discord_token = DISCORD_TOKEN
    discord_channels = os.getenv("DISCORD_CHANNEL_IDS", "")
    if not discord_channels and TARGET_DISCORD_CHANNEL_ID:
        discord_channels = TARGET_DISCORD_CHANNEL_ID
        
    if discord_token and discord_channels:
        d_ch_list = [ch.strip() for ch in discord_channels.split(",") if ch.strip()]
        logger.info(f"Scraping Discord Channels: {d_ch_list}")
        try:
            all_d = []
            for ch in d_ch_list:
                d_msgs = discord_manager.fetch_messages(ch, limit=60)
                if d_msgs: all_d.extend(d_msgs)
            results["discord"] = all_d
            logger.info(f"Got {len(all_d)} Discord messages.")
        except Exception as e:
             logger.error(f"Discord Scrape Failed: {e}")

    # Save
    combined = []
    for source, items in results.items():
        for item in items:
            item["source"] = source
            combined.append(item)
            
    with open(OUTPUT_FILE, "w") as f:
        json.dump(combined, f, indent=2)
        
    logger.info(f"Saved {len(combined)} to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
