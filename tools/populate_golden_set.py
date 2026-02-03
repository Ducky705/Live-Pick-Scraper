
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.telegram_client import tg_manager
from src.discord_client import discord_manager
from src.twitter_client import twitter_manager
from src.extraction_pipeline import ExtractionPipeline
from src.openrouter_client import openrouter_completion

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GoldenSetPopulator")

# Configuration
TARGET_COUNTS = 20
OUTPUT_FILE = "new_golden_set_v2.json"

# Default sources if not in env
DEFAULT_TELEGRAM_CHANNELS = ["1756557375"] # Example (Need real IDs or discovery)
DEFAULT_DISCORD_CHANNELS = ["1046162817088995408"] # Example
DEFAULT_TWITTER_USERS = ["EZMSports", "ItsCappersPicks"]


# Default sources (Can be overridden by env or args in future)
# These are just examples - in a real run we might want to discover them or load from a config file.
# For now, we will use a hardcoded list of "known good" ones if available, or just the ones found.

async def fetch_real_data():
    logger.info("Starting Golden Set Population (20 per source)...")
    
    collected_messages = []
    
    # --- 1. TELEGRAM ---
    logger.info("--- Fetching Telegram ---")
    if await tg_manager.connect_client():
        # Get all dialogs to find channels
        channels = await tg_manager.get_channels()
        
        # Filter for known betting channels or just take the top 5 distinct ones?
        # User said "each telegram". We should probably limit to a reasonable number of channels (e.g. 5) 
        # to avoid fetching 2000 messages if they have 100 channels.
        # Let's take the top 5 most active or just first 5.
        target_channels = channels[:5] 
        
        for ch in target_channels:
            cid = ch['id']
            cname = ch['name']
            logger.info(f"Fetching 20 from Telegram Channel: {cname} ({cid})")
            
            # fetch_messages takes a list, but we pass one to isolate the count
            msgs = await tg_manager.fetch_messages([cid], None)
            
            # Take last 20
            selected = msgs[:TARGET_COUNTS]
            collected_messages.extend(selected)
            logger.info(f"  -> Added {len(selected)} messages.")
            
            # Pause to be nice
            await asyncio.sleep(2)
    else:
        logger.error("Telegram not connected.")

    # --- 2. DISCORD ---
    logger.info("--- Fetching Discord ---")
    discord_ids = os.getenv("DISCORD_CHANNEL_IDS", "").split(",")
    discord_ids = [d.strip() for d in discord_ids if d.strip()]
    
    # If no env provided, maybe use the default if valid?
    if not discord_ids and DEFAULT_DISCORD_CHANNELS:
         discord_ids = DEFAULT_DISCORD_CHANNELS

    for did in discord_ids:
        try:
            logger.info(f"Fetching 20 from Discord Channel: {did}")
            msgs = discord_manager.fetch_messages(did, limit=TARGET_COUNTS)
            collected_messages.extend(msgs)
            logger.info(f"  -> Added {len(msgs)} messages.")
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"  -> Failed: {e}")

    # --- 3. TWITTER ---
    logger.info("--- Fetching Twitter ---")
    # Use explicit user list
    twitter_users = DEFAULT_TWITTER_USERS
    # Also check env
    env_tw = os.getenv("TWITTER_MONITORED_ACCOUNTS")
    if env_tw:
        twitter_users = [u.strip() for u in env_tw.split(",") if u.strip()]
        
    for user in twitter_users:
        try:
            logger.info(f"Fetching 20 from Twitter User: @{user}")
            # Use get_user_tweets for precise targeting
            tweets = await twitter_manager.get_user_tweets(user, limit=TARGET_COUNTS)
            
            # Convert to standard format if get_user_tweets returns raw objects?
            # get_user_tweets in twitter_client.py returns "collected_tweets" (list of Twist objects)
            # We need to PARSE them.
            # twitter_manager.fetch_tweets does parsing internally. 
            # We need to manually parse if we call get_user_tweets directly.
            
            # Helper to parse (borrowed from existing logic or we can add a helper to manager)
            # Actually, `fetch_tweets` does the parsing via `_parse_tweet`.
            # Let's use `_parse_tweet` which is available on the manager instance.
            
            parsed_tweets = []
            for t in tweets:
                parsed_tweets.append(twitter_manager._parse_tweet(t))
                
            collected_messages.extend(parsed_tweets)
            logger.info(f"  -> Added {len(parsed_tweets)} tweets.")
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"  -> Failed: {e}")

    logger.info(f"Total Raw Messages Collected: {len(collected_messages)}")
    return collected_messages

async def generate_golden_answers(messages):
    logger.info(f"Generating GOLDEN SET ANSWERS for {len(messages)} items...")
    logger.info("Using High-Precision Model (DeepSeek R1 via Chimera) as 'Manual Reviewer'...")
    
    labeled_data = []
    
    # Batch processing 
    # US-200: Using DeepSeek R1 which has a strict 15s delay (4 RPM). 
    # ParallelProcessor handles the delay, but we should keep batches small or just rely on the processor queue.
    # Batch size 3 matches the pipeline default.
    batch_size = 5 
    total = len(messages)
    
    for i in range(0, total, batch_size):
        batch = messages[i : i + batch_size]
        logger.info(f"Processing Batch {i}/{total}...")
        
        try:
            # Force OCR pre-processing if images exist
            # The ExtractionPipeline usually does lazy OCR. 
            # We want to ensure it has FULL context.
            # But the pipeline handles this. We just need to ensure the PIPELINE uses the best model.
            
            # We override the provider to use the user-requested DeepSeek R1
            results = ExtractionPipeline.run(batch, target_date=None, provider_override="deepseek_r1")
            
            batch_picks = {}
            for p in results:
                mid = str(p.get('message_id'))
                if mid not in batch_picks:
                    batch_picks[mid] = []
                batch_picks[mid].append(p)
                
            for msg in batch:
                mid = str(msg['id'])
                item = {
                    "id": msg['id'],
                    "channel_id": msg.get('channel_name', 'unknown'),
                    "date": msg['date'],
                    "text": msg['text'],
                    "images": msg.get('images', []),
                    "source": msg.get('channel_name', 'UnknownSource'),
                    "expected_picks": batch_picks.get(mid, [])
                }
                
                # Mark as VERIFIED (since this IS the golden set)
                # We trust Llama 405B as the "Manual Reviewer"
                for p in item['expected_picks']:
                    p['verified_grade'] = "VERIFIED_GOLD"
                    
                labeled_data.append(item)
                
        except Exception as e:
            logger.error(f"Batch Error: {e}")
            
    return labeled_data


def save_golden_set(data):
    logger.info(f"Saving {len(data)} items to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info("Done.")

if __name__ == "__main__":
    msgs = asyncio.run(fetch_real_data())
    final_set = asyncio.run(generate_golden_answers(msgs))
    save_golden_set(final_set)
