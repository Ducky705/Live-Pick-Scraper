
import asyncio
import os
import sys
# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from telegram_client import tg_manager
from twitter_client import twitter_manager
from discord_client import discord_manager
from config import TARGET_TELEGRAM_CHANNEL_ID, TARGET_DISCORD_CHANNEL_ID

async def test_telegram():
    print("\n--- Testing Telegram Scraper ---")
    authorized = await tg_manager.connect_client()
    if not authorized:
        print("Telegram not authorized. Skipping fetch.")
        return

    # Use default target or input
    channel = TARGET_TELEGRAM_CHANNEL_ID
    if not channel:
        print("No TARGET_TELEGRAM_CHANNEL_ID in .env")
        return

    channels = channel.split(",") if "," in channel else [channel]
    
    for ch_id in channels:
        ch_id = ch_id.strip()
        print(f"Fetching from Telegram Channel {ch_id}...")
        try:
            msgs = await tg_manager.fetch_messages([ch_id], target_date_str=None) 
            print(f"Success! Fetched {len(msgs)} messages from {ch_id}.")
            if msgs:
                print(f"Sample: {msgs[0]['text'][:50]}...")
        except Exception as e:
            print(f"Error fetching {ch_id}: {e}")
    print(f"Success! Fetched {len(msgs)} messages.")
    if msgs:
        print(f"Sample: {msgs[0]['text'][:50]}...")

async def test_twitter():
    print("\n--- Testing Twitter Scraper ---")
    # Twitter manager uses monitored accounts from env
    # Search since 2024 to ensure we get results if auth works
    msgs = await twitter_manager.fetch_tweets(limit=5, target_date="2024-01-01")
    print(f"Success! Fetched {len(msgs)} tweets.")
    if msgs:
        print(f"Sample: {msgs[0]['text'][:50]}...")

async def test_discord():
    print("\n--- Testing Discord Scraper ---")
    channel = TARGET_DISCORD_CHANNEL_ID
    if not channel:
        print("No TARGET_DISCORD_CHANNEL_ID in .env")
        return

    channels = channel.split(",") if "," in channel else [channel]
    
    for ch_id in channels:
        ch_id = ch_id.strip()
        print(f"Fetching from Discord Channel {ch_id}...")
        msgs = await discord_manager.fetch_messages(ch_id, limit=5)
        print(f"Success! Fetched {len(msgs)} messages from {ch_id}.")
        if msgs:
            print(f"Sample: {msgs[0]['text'][:50]}...")

async def main():
    print("Starting Scraper Connectivity Tests...")
    
    try:
        await test_telegram()
    except Exception as e:
        print(f"Telegram Test Failed: {e}")

    try:
        await test_twitter()
    except Exception as e:
        print(f"Twitter Test Failed: {e}")

    try:
        await test_discord()
    except Exception as e:
        print(f"Discord Test Failed: {e}")

    print("\nTests Completed.")

if __name__ == "__main__":
    asyncio.run(main())
