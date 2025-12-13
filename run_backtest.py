import asyncio
import csv
import os
import logging
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
import config
from scrapers import TelegramScraper
from models import RawPick
import simple_parser
import ai_parser
import processing_service  # Import the cleaner!

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_backtest():
    print("="*60)
    print("🧪 LIVE BACKTEST & ACCURACY REPORT (IMPROVED)")
    print("="*60)
    print("This script simulates the FULL production pipeline logic.")
    print("-" * 60)

    # 1. Initialize Telegram Client
    if not config.TELEGRAM_SESSION_NAME:
        print("❌ Error: TELEGRAM_SESSION_NAME not found in .env")
        return

    client = TelegramClient(
        StringSession(config.TELEGRAM_SESSION_NAME), 
        int(config.TELEGRAM_API_ID), 
        config.TELEGRAM_API_HASH
    )
    
    scraper = TelegramScraper()
    results = []
    
    try:
        await client.start()
        print("✅ Telegram Connected.")
        
        for channel_id in config.TELEGRAM_CHANNELS:
            try:
                entity = await client.get_entity(channel_id)
                print(f"\n📡 Scanning: {entity.title} ({channel_id})")
                
                count = 0
                async for msg in client.iter_messages(entity, limit=30):
                    # Filter empty messages unless they have a photo
                    if not msg.text and not msg.photo: continue

                    raw_text = (msg.text or "").strip()
                    is_ocr = False
                    
                    # Simulate OCR trigger
                    if not raw_text and msg.photo:
                        print(f"   📷 Performing OCR on Msg ID {msg.id}...")
                        ocr_text = await scraper._perform_ocr(msg)
                        raw_text = ocr_text
                        is_ocr = True

                    if not raw_text: continue

                    # *** PRODUCTION CLEANING STEP ***
                    # This filters out "bets placed", "balance", and duplicate lines
                    cleaned_text = processing_service.clean_ocr_garbage(raw_text)

                    pick = RawPick(
                        source_unique_id=str(msg.id),
                        source_url=f"t.me/c/{channel_id}/{msg.id}",
                        capper_name=entity.title,
                        raw_text=cleaned_text,  # Use CLEANED text
                        pick_date=datetime.now().date()
                    )

                    # --- RUN TEST 1: REGEX ---
                    regex_picks = simple_parser.parse_with_regex(pick)
                    
                    # --- RUN TEST 2: AI (Fallback) ---
                    ai_picks = []
                    used_ai = False
                    if not regex_picks and len(cleaned_text) < 1000:
                        # Heuristic to decide if it's worth sending to AI
                        if "bet" in cleaned_text.lower() or "u" in cleaned_text.lower() or "-" in cleaned_text:
                            print(f"   🤖 Invoking AI for Msg ID {msg.id}...")
                            ai_picks = ai_parser.parse_with_ai([pick])
                            used_ai = True

                    parsed_list = regex_picks if regex_picks else ai_picks
                    
                    # Determine Status
                    status = "✅ EXTRACTED" if parsed_list else "❌ SKIPPED/FAILED"
                    
                    # Use scraper's own validator to see if we SHOULD have ignored it
                    # Note: We check against raw_text here because the scraper checks raw messages
                    if not parsed_list and not scraper._is_valid_pick_message(raw_text):
                        status = "🗑️ IGNORED (Noise)"

                    row = {
                        "Channel": entity.title,
                        "Msg ID": msg.id,
                        "Date": msg.date.strftime('%Y-%m-%d'),
                        "Cleaned Text": cleaned_text[:100].replace("\n", " ") + "...",
                        "Method": "AI" if used_ai else ("Regex" if regex_picks else "None"),
                        "Status": status,
                        "Pick": str([p.pick_value for p in parsed_list]) if parsed_list else ""
                    }
                    results.append(row)
                    count += 1
                    print(f"   Msg {msg.id}: {status} -> {row['Pick']}")

            except Exception as e:
                print(f"   ⚠️ Error scanning channel {channel_id}: {e}")

    finally:
        await client.disconnect()

    if results:
        filename = "backtest_report_v2.csv"
        keys = results[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
        print("\n" + "="*60)
        print(f"📄 REPORT GENERATED: {os.path.abspath(filename)}")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(run_backtest())
