import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# Ensure we can import from src
sys.path.append(os.path.join(os.getcwd(), ".."))
sys.path.append(os.getcwd())

from config import OUTPUT_DIR
from src.discord_client import discord_manager
from src.telegram_client import TelegramManager
from src.twitter_client import TwitterManager

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    load_dotenv()

    # 1. Calculate Yesterday ET
    ET_OFFSET = timezone(timedelta(hours=-5))
    now_et = datetime.now(ET_OFFSET)
    yesterday_et = now_et - timedelta(days=1)
    target_date_str = yesterday_et.strftime("%Y-%m-%d")
    target_date_obj = yesterday_et.date()

    print(f"--- Verifying Messages for {target_date_str} (ET) ---")

    all_messages = []

    # --- DISCORD ---
    print("\n[1/3] Fetching Discord...")
    channel_ids_str = os.getenv("DISCORD_CHANNEL_IDS", "")
    if channel_ids_str:
        discord_channels = [cid.strip() for cid in channel_ids_str.split(",") if cid.strip()]
        for cid in discord_channels:
            try:
                # Fetch last 100 to ensure we cover the whole day
                msgs = discord_manager.fetch_messages(cid, limit=100)

                # Filter for target date
                count = 0
                for m in msgs:
                    # m['date'] is "YYYY-MM-DD HH:MM ET"
                    msg_date_str = m.get("date", "").split(" ")[0]
                    if msg_date_str == target_date_str:
                        m["source"] = "discord"
                        all_messages.append(m)
                        count += 1
                print(f"  Channel {cid}: Found {count} messages from yesterday.")
            except Exception as e:
                print(f"  Error fetching Discord channel {cid}: {e}")
    else:
        print("  Skipping Discord (DISCORD_CHANNEL_IDS not set)")

    # --- TWITTER ---
    print("\n[2/3] Fetching Twitter...")
    try:
        tw_manager = TwitterManager()
        # fetch_tweets handles filtering internally
        tw_msgs = await tw_manager.fetch_tweets(target_date=target_date_str)
        for m in tw_msgs:
            m["source"] = "twitter"
        all_messages.extend(tw_msgs)
        print(f"  Found {len(tw_msgs)} tweets from yesterday.")
    except Exception as e:
        print(f"  Error fetching Twitter: {e}")

    # --- TELEGRAM ---
    print("\n[3/3] Fetching Telegram...")
    tg_channel_ids_str = os.getenv("TARGET_TELEGRAM_CHANNEL_ID")
    if tg_channel_ids_str:
        tg_channel_ids = [tid.strip() for tid in tg_channel_ids_str.split(",") if tid.strip()]
        try:
            tg_manager = TelegramManager()
            authorized = await tg_manager.connect_client()
            if not authorized:
                print("  Telegram not authorized. Skipping.")
            else:
                # fetch_messages handles date filtering
                tg_msgs = await tg_manager.fetch_messages(tg_channel_ids, target_date_str)
                for m in tg_msgs:
                    m["source"] = "telegram"
                all_messages.extend(tg_msgs)
                print(f"  Found {len(tg_msgs)} Telegram messages from yesterday.")
        except Exception as e:
            print(f"  Error fetching Telegram: {e}")
    else:
        print("  Skipping Telegram (TARGET_TELEGRAM_CHANNEL_ID not set)")

    # --- SAVE ---
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    output_file = os.path.join(OUTPUT_DIR, f"verified_messages_{target_date_str}.json")

    # Sort by date
    all_messages.sort(key=lambda x: x.get("date", ""))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_messages, f, indent=2, default=str)

    print(f"\n[COMPLETE] Saved {len(all_messages)} total messages to:\n{output_file}")

    # Summary
    print("\nSummary by Source:")
    by_source = {}
    for m in all_messages:
        s = m.get("source", "unknown")
        by_source[s] = by_source.get(s, 0) + 1

    for s, c in by_source.items():
        print(f"  {s.title()}: {c}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
