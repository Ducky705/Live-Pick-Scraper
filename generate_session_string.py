import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

async def main():
    print("="*60)
    print("🔐 TELEGRAM SESSION GENERATOR")
    print("="*60)
    print("This script will generate a session string for your .env file.")
    print("You will need your API ID and API HASH from https://my.telegram.org")
    print("-" * 60)

    # 1. Get Credentials
    api_id_input = input("Enter your API ID: ").strip()
    api_hash = input("Enter your API HASH: ").strip()

    if not api_id_input or not api_hash:
        print("❌ Error: API ID and Hash are required.")
        return

    try:
        api_id = int(api_id_input)
    except ValueError:
        print("❌ Error: API ID must be a number.")
        return

    # 2. Initialize Client
    print("\nConnecting to Telegram...")
    client = TelegramClient(StringSession(), api_id, api_hash)

    try:
        await client.start()
    except Exception as e:
        print(f"\n❌ Login Failed: {e}")
        return

    # 3. Generate String
    print("\n✅ Login Successful!")
    session_string = client.session.save()

    print("\n" + "="*60)
    print("YOUR SESSION STRING (COPY BELOW):")
    print("-" * 60)
    print(session_string)
    print("-" * 60)
    print("👉 Paste this into your .env file as TELEGRAM_SESSION_NAME")
    print("="*60)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())