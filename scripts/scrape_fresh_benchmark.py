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

# Import Clients
from src.telegram_client import tg_manager
from src.twitter_client import twitter_manager
from src.discord_client import discord_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ScraperBenchmark")

OUTPUT_FILE = "data/cache/fresh_benchmark_raw.json"

async def main():
    logger.info("Starting Fresh Benchmark Scrape...")
    
    results = {
        "telegram": [],
        "twitter": [],
        "discord": []
    }

    # 1. Telegram
    if TARGET_TELEGRAM_CHANNEL_ID and API_ID and API_HASH:
        # Handle comma-separated list
        tg_channels = [ch.strip() for ch in TARGET_TELEGRAM_CHANNEL_ID.split(",") if ch.strip()]
        logger.info(f"Scraping {len(tg_channels)} Telegram Channels: {tg_channels}")
        
        try:
            connected = await tg_manager.connect_client()
            if connected:
                # Fetch messages from ALL channels
                msgs = await tg_manager.fetch_messages(tg_channels, None)
                results["telegram"] = msgs
                logger.info(f"Got {len(msgs)} Telegram messages.")
            else:
                logger.error("Telegram Client Not Authorized.")
        except Exception as e:
            logger.error(f"Telegram Scrape Failed: {e}")
    else:
        logger.warning("Telegram Config Missing")

    # 2. Twitter (Existing logic is fine, but lets ensure we get enough)
    logger.info("Scraping Twitter...")
    try:
        tweets = await twitter_manager.fetch_tweets(limit=80) # increased limit
        results["twitter"] = tweets
        logger.info(f"Got {len(tweets)} Tweets.")
    except Exception as e:
        logger.error(f"Twitter Scrape Failed: {e}")

    # 3. Discord
    # Config specific fix: Load IDs from env if config is missing or check env directly for list
    discord_token = DISCORD_TOKEN
    discord_channels = os.getenv("DISCORD_CHANNEL_IDS", "")
    
    if not discord_channels and TARGET_DISCORD_CHANNEL_ID:
        discord_channels = TARGET_DISCORD_CHANNEL_ID
        
    if discord_token and discord_channels:
        d_ch_list = [ch.strip() for ch in discord_channels.split(",") if ch.strip()]
        logger.info(f"Scraping {len(d_ch_list)} Discord Channels: {d_ch_list}")
        
        all_discord = []
        try:
            for d_ch in d_ch_list:
                d_msgs = discord_manager.fetch_messages(d_ch, limit=50) # 50 per channel
                if d_msgs:
                    all_discord.extend(d_msgs)
            
            results["discord"] = all_discord
            logger.info(f"Got {len(all_discord)} Discord messages.")
        except Exception as e:
            logger.error(f"Discord Scrape Failed: {e}")
    else:
        logger.warning("Discord Config Missing (Token or Channels)")

    # Save Results
    combined = []
    for source, items in results.items():
        for item in items:
            item["source"] = source
            combined.append(item)
            
    with open(OUTPUT_FILE, "w") as f:
        json.dump(combined, f, indent=2)
        
    logger.info(f"Saved {len(combined)} raw items to {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
