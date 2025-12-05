import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.ERROR)

async def main():
    print("="*60)
    print("📡 TELEGRAM CHANNEL LISTER")
    print("="*60)

    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    session_str = os.getenv('TELEGRAM_SESSION_NAME')

    if not all([api_id, api_hash, session_str]):
        print("❌ Error: Missing credentials in .env file.")
        print("Ensure TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_SESSION_NAME are set.")
        return

    try:
        client = TelegramClient(StringSession(session_str), int(api_id), api_hash)
        await client.start()
        
        print(f"{'ID':<20} | {'TYPE':<10} | {'NAME'}")
        print("-" * 60)
        
        count = 0
        async for dialog in client.iter_dialogs():
            # Filter for Channels and Supergroups (Megagroups)
            if dialog.is_channel:
                entity_type = "Channel"
                # Telethon might return the ID without the -100 prefix for some objects,
                # but for API usage, we usually need the full ID.
                # We can get the proper ID from the entity.
                
                # Note: Telethon handles IDs smartly, but for config files, 
                # it's safest to use the ID exactly as Telethon reports it here.
                print(f"{dialog.id:<20} | {entity_type:<10} | {dialog.title}")
                count += 1
            elif dialog.is_group:
                print(f"{dialog.id:<20} | {'Group':<10} | {dialog.title}")
                count += 1

        print("-" * 60)
        print(f"✅ Found {count} channels/groups.")
        print("\n👉 Copy the IDs above (e.g., -100123456789) into your TELEGRAM_CHANNEL_URLS variable.")
        print("   Separate multiple IDs with commas.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())