import os
import asyncio
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

async def main():
    print("Attempting to generate a Telethon session string...")
    
    # Load environment variables from .env file
    load_dotenv()
    
    api_id_str = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')

    if not api_id_str or not api_hash:
        print("ERROR: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in your .env file.")
        return
        
    api_id = int(api_id_str)

    # We use an in-memory StringSession to generate the session string.
    # The user will be prompted to log in.
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        # The session string is now generated and stored within the session object.
        # We can access it directly.
        session_string = client.session.save()
        
        print("\n" + "="*50)
        print("SESSION STRING GENERATED SUCCESSFULLY")
        print("="*50)
        print("\nYour session string is:\n")
        print(session_string)
        print("\n" + "="*50)
        print("ACTION REQUIRED:")
        print("1. Copy the ENTIRE string above (it's very long).")
        print("2. Open your .env file.")
        print("3. Paste it as the value for the TELEGRAM_SESSION_NAME variable.")
        print("   Example: TELEGRAM_SESSION_NAME='1Bv...=='")
        print("4. Also, add this string to your GitHub repository secrets with the same name.")
        print("="*50 + "\n")

if __name__ == "__main__":
    # In recent versions of Telethon, it's better to run async code this way.
    asyncio.run(main())