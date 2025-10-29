import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME')

async def main():
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME]):
        logging.error("Telegram credentials not found in .env file. Cannot run.")
        return

    client = TelegramClient(TELEGRAM_SESSION_NAME, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    
    print("Connecting to Telegram...")
    await client.start()
    print("Client connected. Fetching your dialogs (chats/channels)...")

    print("\n--- Your Channels/Chats ---")
    print(f"{'ID':<15} | {'Type':<10} | {'Name'}")
    print("-" * 50)

    async for dialog in client.iter_dialogs():
        entity_type = "Channel" if dialog.is_channel else "Group" if dialog.is_group else "User"
        # For channels/supergroups, the ID needs a -100 prefix for API calls
        api_id = dialog.id
        if dialog.is_channel:
            # Telethon handles the -100 prefix automatically when you use the full ID, 
            # but it's good to know the raw format.
            pass

        print(f"{api_id:<15} | {entity_type:<10} | {dialog.name}")

    print("-" * 50)
    print("\nFind the private channel in the list above.")
    print("Copy its full numerical ID (including the '-') for the next step.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())