import asyncio
import os
import sys
from dotenv import load_dotenv
from twikit import Client

# Load env vars
load_dotenv()


async def main():
    print("--- Twitter Search Efficiency Test ---")

    client = Client("en-US")
    cookies_path = "data/sessions/twitter_cookies.json"
    if os.path.exists(cookies_path):
        client.load_cookies(cookies_path)
    else:
        print("No cookies found.")
        return

    # 1. Define Query
    # Using specific accounts from our list
    # Note: Twitter search syntax: (from:user1 OR from:user2) since:YYYY-MM-DD
    accounts = ["EZMSports", "ExclusiveCapper", "ItsCappersPicks"]
    from_clause = " OR ".join([f"from:{acc}" for acc in accounts])
    target_date = "2026-01-24"
    query = f"({from_clause}) since:{target_date}"

    print(f"\nQuery: {query}")

    try:
        print("Searching...")
        # 'Latest' tab is usually best for scraping
        results = await client.search_tweet(query, product="Latest", count=40)

        print(f"Found {len(results)} tweets.")
        for tweet in results:
            print(
                f"- [@{tweet.user.screen_name}] {tweet.created_at}: {tweet.text[:50]}..."
            )

    except Exception as e:
        print(f"Search Error: {e}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
