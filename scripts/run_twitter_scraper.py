import asyncio
import json
import logging
import os
import platform
import sys

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add src to path if needed (it is in root, so should be fine)
sys.path.append(os.path.join(os.getcwd(), ".."))  # Append parent dir if running from scripts/

from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt
from src.prompts.decoder import normalize_response
from src.twitter_client import twitter_manager
from src.utils import clean_text_for_ai

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def main():
    target_username = "EZMSports"
    TWEET_COUNT = 50

    print("--- Twitter Sports Pick Scraper (Deep Debug Mode) ---")
    print(f"Target: @{target_username}")
    print(f"Fetching last {TWEET_COUNT} tweets...")

    # 1. Authenticate & Fetch
    try:
        messages = await twitter_manager.get_user_tweets(target_username, count=TWEET_COUNT)
    except ValueError as e:
        print(f"\n[ERROR] Authentication failed: {e}")
        return
    except Exception as e:
        print(f"\n[ERROR] Failed to fetch tweets: {e}")
        return

    if not messages:
        print("No tweets found.")
        return

    print(f"Fetched {len(messages)} tweets.")

    # DEBUG: Save raw messages
    with open("debug_raw_tweets.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, default=str)
    print("Saved raw tweets to debug_raw_tweets.json")

    # 2. Pre-process (Clean text)
    processed_messages = []
    print("Pre-processing text...")
    for msg in messages:
        # Mimic main.py api_generate_prompt logic
        msg["text"] = clean_text_for_ai(msg["text"])
        msg["ocr_texts"] = []
        processed_messages.append(msg)

    # 3. Generate Prompt
    print("Generating AI Prompt...")
    master_prompt = generate_ai_prompt(processed_messages)

    # DEBUG: Save Prompt
    with open("debug_prompt.txt", "w", encoding="utf-8") as f:
        f.write(master_prompt)
    print("Saved AI prompt to debug_prompt.txt")

    # 4. Call AI
    print("Sending to AI Model (parsing picks)...")
    try:
        # Use a good model for parsing
        model = "mistralai/devstral-2512:free"

        result_str = openrouter_completion(master_prompt, model=model)

        # DEBUG: Save Raw Response
        with open("debug_ai_response.txt", "w", encoding="utf-8") as f:
            f.write(result_str)
        print("Saved raw AI response to debug_ai_response.txt")

        # 5. Parse Result
        picks = normalize_response(result_str)

        # Print Result nicely
        if picks:
            print(f"\n--- Found {len(picks)} Picks ---")

            # Sort by date desc
            picks.sort(key=lambda x: x.get("date", ""), reverse=True)

            for p in picks:
                # Format: [DATE] LEAGUE - Capper: Pick (Odds)
                print(
                    f"[{p.get('date')}] {p.get('league')} - {p.get('capper_name')}: {p.get('pick')} ({p.get('odds') or 'No Odds'})"
                )

            # Save to file
            with open("twitter_picks.json", "w") as f:
                json.dump({"picks": picks}, f, indent=2)
            print("\nSaved picks to twitter_picks.json")
        else:
            print("\nAI returned no valid picks.")

    except Exception as e:
        print(f"\nAI Error: {e}")


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
