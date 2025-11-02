# File: ./generate_telegram_context.py
import os
import asyncio
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message

# --- Local Config Import ---
# This assumes the script is in the root directory alongside config.py
try:
    from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME, TELEGRAM_CHANNELS
except ImportError:
    print("ERROR: Could not import from config.py. Make sure this script is in the root directory.")
    exit(1)

# --- Script Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# How many recent messages to pull from each channel for the context file.
MESSAGE_LIMIT_PER_CHANNEL = 300
# The name of the output file.
OUTPUT_FILE = "telegram_message_context.json"
# Minimum text length to be considered for saving (ignores simple reactions/stickers)
MIN_TEXT_LENGTH = 5


async def main():
    """
    Connects to Telegram, scrapes a large number of recent messages from configured
    channels, and saves them to a JSON file for analysis and context.
    """
    logging.info("Starting Telegram context generation script...")

    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME, TELEGRAM_CHANNELS]):
        logging.error("Telegram credentials or channel list not found in your configuration.")
        logging.error("Please ensure TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME, and TELEGRAM_CHANNEL_URLS are set in .env")
        return

    all_messages = []
    client = TelegramClient(StringSession(TELEGRAM_SESSION_NAME), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)

    try:
        logging.info("Connecting to Telegram client...")
        await client.start()
        logging.info("Client connected successfully.")

        for channel_entity_ref in TELEGRAM_CHANNELS:
            try:
                logging.info(f"--- Processing channel: {channel_entity_ref} ---")
                entity = await client.get_entity(channel_entity_ref)
                channel_name = getattr(entity, 'title', str(channel_entity_ref))
                logging.info(f"Scraping up to {MESSAGE_LIMIT_PER_CHANNEL} messages from '{channel_name}'...")

                message_count = 0
                async for message in client.iter_messages(entity, limit=MESSAGE_LIMIT_PER_CHANNEL):
                    # We only care about messages with some text content
                    if message and message.text and len(message.text.strip()) >= MIN_TEXT_LENGTH:
                        message_data = {
                            "channel_name": channel_name,
                            "channel_id": entity.id,
                            "message_id": message.id,
                            "date_utc": message.date.isoformat(),
                            "text": message.text,
                            "is_reply": message.is_reply,
                            "reply_to_msg_id": message.reply_to_msg_id if message.is_reply else None,
                        }
                        all_messages.append(message_data)
                        message_count += 1
                
                logging.info(f"Found and saved {message_count} relevant messages from '{channel_name}'.")

            except Exception as e:
                logging.error(f"Could not process channel '{channel_entity_ref}'. Error: {e}")
                continue # Move to the next channel

    except Exception as e:
        logging.error(f"A critical error occurred: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()
            logging.info("Telegram client disconnected.")

    if all_messages:
        logging.info(f"\nTotal messages collected from all channels: {len(all_messages)}")
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_messages, f, indent=2, ensure_ascii=False)
            logging.info(f"✅ Successfully saved all messages to '{OUTPUT_FILE}'")
            print(f"\nContext generation complete. You can now use the file '{OUTPUT_FILE}' to provide context.")
        except Exception as e:
            logging.error(f"Failed to write to output file '{OUTPUT_FILE}'. Error: {e}")
    else:
        logging.warning("No messages were collected. The output file was not created.")


if __name__ == "__main__":
    asyncio.run(main())