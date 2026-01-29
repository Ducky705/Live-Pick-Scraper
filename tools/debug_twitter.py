import asyncio
import os
import sys

import requests
from dotenv import load_dotenv
from twikit import Client

# Load env vars
load_dotenv()


async def main():
    print("--- Twitter Connectivity Check ---")

    # 1. Basic Requests Check
    print("\n[1] Testing basic HTTP connectivity to x.com...")
    try:
        resp = requests.get("https://x.com", timeout=10)
        print(f"Status Code: {resp.status_code}")
        print("Basic connectivity OK.")
    except Exception as e:
        print(f"Basic connectivity FAILED: {e}")

    # 2. Twikit Check
    print("\n[2] Testing Twikit...")

    # Credentials
    username = os.getenv("TWITTER_USERNAME")
    email = os.getenv("TWITTER_EMAIL")
    password = os.getenv("TWITTER_PASSWORD")

    if not username:
        print("Error: TWITTER_USERNAME not set.")
        return

    # Initialize Client
    client = Client("en-US")

    # Try loading cookies
    cookies_path = "data/sessions/twitter_cookies.json"
    if os.path.exists(cookies_path):
        print(f"Loading cookies from {cookies_path}")
        client.load_cookies(cookies_path)
    else:
        print("No cookies found. Attempting login...")
        if not username or not password:
            print("Missing credentials!")
            return
        await client.login(auth_info_1=username, auth_info_2=email, password=password)
        client.save_cookies(cookies_path)
        print("Logged in and saved cookies.")

    # Test User Fetch
    targets = ["EZMSports", "PropJoeSends", "The_Matty_Ice_"]

    for target_user in targets:
        print(f"\nAttempting to fetch user: {target_user}")
        try:
            user = await client.get_user_by_screen_name(target_user)
            print(f"Success! User ID: {user.id}")

            print("Fetching recent tweets...")
            tweets = await user.get_tweets("Tweets", count=5)
            print(f"Fetched {len(tweets)} tweets.")
            if tweets:
                t = tweets[0]
                print(f"Latest: {t.text[:50]}...")
                if hasattr(t, "media") and t.media:
                    print(f"Media found: {t.media}")
                    print(f"Type of media item: {type(t.media[0])}")
                    try:
                        print(f"Trying .get(): {t.media[0].get('type')}")
                    except Exception as e:
                        print(f"No .get(): {e}")
                        # Try attribute access
                        try:
                            print(f"Attribute access: {t.media[0].type}")
                        except:
                            pass

        except Exception as e:
            print(f"Twikit Error for {target_user}: {e}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
