import asyncio
import os
import sys
import json
import logging
import platform

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.append(os.getcwd())

from src.discord_client import discord_manager
from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt
from src.utils import clean_text_for_ai

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    print("--- Discord Sports Pick Scraper ---")
    
    # 1. Configuration
    channel_ids_str = os.getenv("DISCORD_CHANNEL_IDS", "")
    if not channel_ids_str:
        print("[ERROR] DISCORD_CHANNEL_IDS not set in .env")
        return
        
    channel_ids = [cid.strip() for cid in channel_ids_str.split(",") if cid.strip()]
    print(f"Targets: {len(channel_ids)} channels")
    
    all_messages = []
    
    # 2. Fetch Messages
    for cid in channel_ids:
        msgs = discord_manager.fetch_messages(cid, limit=50)
        print(f"Channel {cid}: Fetched {len(msgs)} messages.")
        all_messages.extend(msgs)
        
    if not all_messages:
        print("No messages found.")
        return

    print(f"Total fetched: {len(all_messages)} messages.")
    
    # DEBUG: Save raw messages
    with open("debug_raw_discord.json", "w", encoding="utf-8") as f:
        json.dump(all_messages, f, indent=2, default=str)
    print("Saved raw data to debug_raw_discord.json")

    # 3. Pre-process (Clean text)
    processed_messages = []
    print("Pre-processing text...")
    for msg in all_messages:
        msg['text'] = clean_text_for_ai(msg['text'])
        # Ensure ocr_texts exists for prompt builder
        msg['ocr_texts'] = [] 
        processed_messages.append(msg)

    # 4. Generate Prompt
    print("Generating AI Prompt...")
    master_prompt = generate_ai_prompt(processed_messages)
    
    # 5. Call AI
    print("Sending to AI Model (parsing picks)...")
    try:
        # Use a good model for parsing
        model = "mistralai/devstral-2512:free" # Or use from config if available
        
        result_str = openrouter_completion(master_prompt, model=model)
        
        # 5. Parse Result using decoder for compact format support
        from src.prompts.decoder import normalize_response
        try:
            # Use decoder to handle both compact and full format
            picks = normalize_response(result_str, expand=True)
            
            if picks:
                print(f"\n--- Found {len(picks)} Picks ---")
                
                picks.sort(key=lambda x: x.get('date', ''), reverse=True)
                
                for p in picks:
                    print(f"[{p.get('date')}] {p.get('league')} - {p.get('capper_name')}: {p.get('pick')} ({p.get('odds') or 'No Odds'})")
                
                # Save to file (with full field names)
                with open("discord_picks.json", "w") as f:
                    json.dump({"picks": picks}, f, indent=2)
                print("\nSaved picks to discord_picks.json")
            else:
                print("\nAI returned no picks.")
                print(result_str[:500]) # Print start of response for debug
                
        except Exception as parse_err:
            print(f"\nParsing error: {parse_err}")
            print(result_str)

    except Exception as e:
        print(f"\nAI Error: {e}")

if __name__ == "__main__":
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
