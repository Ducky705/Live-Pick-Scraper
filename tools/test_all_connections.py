import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.gemini_client import gemini_text_completion
from src.openrouter_client import openrouter_completion

# Configure logging to show info
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()


def safe_print(text):
    """Safely print text handling unicode errors on Windows console"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


async def test_twitter():
    print("\n--- Testing Twitter Connection ---")
    try:
        from twikit import Client

        client = Client("en-US")
        cookies_path = "data/sessions/twitter_cookies.json"

        if not os.path.exists(cookies_path):
            print("[X] Twitter cookies not found at data/sessions/twitter_cookies.json")
            return

        client.load_cookies(cookies_path)

        # Simple search
        query = "from:EZMSports"
        print(f"Searching for: {query}")

        results = await client.search_tweet(query, product="Latest", count=5)

        print(f"[OK] Found {len(results)} tweets.")
        for tweet in results:
            safe_print(f"- [@{tweet.user.screen_name}] {tweet.text[:50]}...")

    except ImportError:
        print("[X] twikit not installed.")
    except Exception as e:
        safe_print(f"[X] Twitter Error: {e}")


def test_gemini():
    print("\n--- Testing Gemini Connection ---")
    try:
        # Trying a known stable model if default fails, but here we test the function default first
        # We will override the model to 'gemini-1.5-flash' to see if that works
        print("Testing with model='gemini-1.5-flash'...")
        response = gemini_text_completion("Reply with 'Pong'", model="gemini-1.5-flash")
        if response:
            safe_print(f"[OK] Gemini Response: {response}")
        else:
            print("[X] Gemini returned None (check logs)")
    except Exception as e:
        safe_print(f"[X] Gemini Exception: {e}")


def test_openrouter():
    print("\n--- Testing OpenRouter Connection ---")
    try:
        # Using a free model for testing
        response = openrouter_completion("Reply with 'Pong'", model="meta-llama/llama-3.3-70b-instruct:free")
        if response:
            safe_print(f"[OK] OpenRouter Response: {response}")
        else:
            print("[X] OpenRouter returned None")
    except Exception as e:
        safe_print(f"[X] OpenRouter Exception: {e}")


async def main():
    await test_twitter()
    test_gemini()
    test_openrouter()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
