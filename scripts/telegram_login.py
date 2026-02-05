import asyncio
import os
import sys

# Ensure src is in path to find config and modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from telegram_client import tg_manager

async def main():
    print("\n===========================================")
    print("      TELEGRAM INTERACTIVE LOGIN")
    print("===========================================")
    print("1. You will be asked for your Phone Number (international format, e.g., +1234567890).")
    print("2. Telegram will send a login code to your Telegram App.")
    print("3. Enter the code when prompted.")
    print("4. If you have 2FA enabled, you will be asked for your password.")
    print("===========================================\n")

    # Get the client instance (configured with session path from config)
    client = await tg_manager.get_client()
    
    # Start interactive login flow
    # This will use the current terminal for input/output
    await client.start()
    
    print("\n-------------------------------------------")
    print("Verifying session...")
    me = await client.get_me()
    
    if me:
        print(f"✅ SUCCESS! Logged in as: {me.first_name} (@{me.username})")
        print("Session saved. You can now run the scraper.")
    else:
        print("❌ Login completed but failed to verify user identity.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nUser failed to complete login (Interrupted).")
    except Exception as e:
        print(f"\n\nAn error occurred during login: {e}")
