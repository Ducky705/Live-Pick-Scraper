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
    target_username = "leakedcaps"
    
    # Calculate "Yesterday" in Eastern Time
    # Current mocked time is 2026-02-15, so yesterday is 2026-02-14
    # ideally we use datetime, but for this specific request:
    target_date = "2026-02-14"
    
    print("--- Twitter Sports Pick Scraper (Deep Debug Mode) ---")
    print(f"Target: @{target_username}")
    print(f"Target Date: From {target_date} (Yesterday ET)")
    
    # 1. Authenticate & Fetch
    try:
        # Fetch tweets until we hit the date before target_date
        messages = await twitter_manager.get_user_tweets(target_username, limit=100, min_date_str=target_date)
    except ValueError as e:
        print(f"\n[ERROR] Authentication failed: {e}")
        return
    except Exception as e:
        print(f"\n[ERROR] Failed to fetch tweets: {e}")
        return

    if not messages:
        print("No tweets found.")
        return

    # Filter to ensure we only have tweets from Yesterday and Today (since min_date_str fetch might include today)
    # The user asked for "posts from yesterday", usually implying starting from yesterday.
    filtered_messages = []
    print(f"Fetched {len(messages)} tweets. Filtering for date >= {target_date}...")
    
    for msg in messages:
        # msg['date'] is formatted as "%Y-%m-%d %H:%M ET"
        msg_date_str = msg.get("date", "").split(" ")[0] # Just the YYYY-MM-DD part
        if msg_date_str >= target_date:
            filtered_messages.append(msg)
            
    messages = filtered_messages
    print(f"Retained {len(messages)} tweets after date filtering.")

    if not messages:
        print("No tweets found for the specified timeframe.")
        return

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

    # 3. Process in Batches
    BATCH_SIZE = 15
    all_picks = []
    full_response_text = ""
    
    total_tweets = len(processed_messages)
    print(f"Processing {total_tweets} tweets in batches of {BATCH_SIZE}...")

    for i in range(0, total_tweets, BATCH_SIZE):
        batch = processed_messages[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (total_tweets + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"--- Batch {batch_num}/{total_batches} ({len(batch)} tweets) ---")
        
        # Generate Prompt for Batch
        batch_prompt = generate_ai_prompt(batch)
        
        # Call AI
        print(f"Sending Batch {batch_num} to AI...")
        try:
            # Use a good model for parsing
            model = "google/gemini-2.0-flash-exp:free" 

            result_str = openrouter_completion(batch_prompt, model=model)
            full_response_text += f"\n--- Batch {batch_num} ---\n{result_str}\n"
            
            # Parse Result
            batch_picks = normalize_response(result_str)
            if batch_picks:
                print(f"Batch {batch_num} found {len(batch_picks)} picks.")
                all_picks.extend(batch_picks)
            else:
                print(f"Batch {batch_num} returned no valid picks.")
                
        except Exception as e:
            print(f"Error processing batch {batch_num}: {e}")
            
        # Small delay
        import time
        time.sleep(1)

    # DEBUG: Save Aggregated Response
    with open("debug_ai_response.txt", "w", encoding="utf-8") as f:
        f.write(full_response_text)
    print("Saved aggregated AI response to debug_ai_response.txt")

    # Final Output processing
    if all_picks:
        print(f"\n--- Found {len(all_picks)} Total Picks ---")

        # Sort by date desc
        all_picks.sort(key=lambda x: x.get("date", ""), reverse=True)

        for p in all_picks:
            # Format: [DATE] LEAGUE - Capper: Pick (Odds)
            print(
                f"[{p.get('date')}] {p.get('league')} - {p.get('capper_name')}: {p.get('pick')} ({p.get('odds') or 'No Odds'})"
            )

        # Save to file
        with open("twitter_picks.json", "w") as f:
            json.dump({"picks": all_picks}, f, indent=2)
        print("\nSaved picks to twitter_picks.json")
    else:
        print("\nAI returned no valid picks from any batch.")


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
