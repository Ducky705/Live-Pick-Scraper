import asyncio
import logging
import os
import sys
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import TARGET_TELEGRAM_CHANNEL_ID
from src.telegram_client import TelegramManager
from src.twitter_client import TwitterManager
from src.deduplicator import Deduplicator
from src.ocr_handler import extract_text_batch
from src.auto_processor import auto_select_messages
from src.prompt_builder import generate_ai_prompt
from src.provider_pool import pooled_completion
from src.utils import clean_text_for_ai, smart_merge_odds
from src.two_pass_verifier import TwoPassVerifier
from src.multi_pick_validator import validate_and_flag_missing
from src.multi_capper_verifier import verify_all_picks

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cli_scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

async def main():
    print("="*50)
    print("   TELEGRAM & TWITTER SCRAPER CLI   ")
    print("="*50)

    # 1. INITIALIZATION
    logging.info("Initializing Clients...")
    
    # Telegram
    tg = TelegramManager()
    tg_connected = await tg.connect_client()
    if not tg_connected:
        logging.error("Telegram Auth Failed! Please run the GUI first to authenticate.")
        return

    # Twitter
    tw = TwitterManager()
    
    # 2. FETCH DATA (Yesterday by default)
    target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    logging.info(f"Target Date: {target_date} (Eastern Time)")
    
    # Fetch Telegram
    logging.info(f"Fetching Telegram messages from {TARGET_TELEGRAM_CHANNEL_ID}...")
    tg_msgs = await tg.fetch_messages([TARGET_TELEGRAM_CHANNEL_ID], target_date)
    logging.info(f"Fetched {len(tg_msgs)} Telegram messages.")
    
    # Fetch Twitter
    logging.info("Fetching Tweets...")
    tw_msgs = await tw.fetch_tweets(target_date=target_date)
    logging.info(f"Fetched {len(tw_msgs)} Tweets.")
    
    # Combine
    all_msgs = tg_msgs + tw_msgs
    
    # 3. DEDUPLICATION
    logging.info("Deduplicating messages...")
    unique_msgs = Deduplicator.merge_messages(all_msgs)
    logging.info(f"Unique Messages: {len(unique_msgs)}")
    
    if not unique_msgs:
        logging.warning("No messages found. Exiting.")
        return

    # 4. OCR & IMAGE PROCESSING
    logging.info("Starting OCR processing (Smart Mode)...")
    
    # Prepare batch
    ocr_tasks = [] # (msg_index, image_path)
    
    for i, msg in enumerate(unique_msgs):
        msg['ocr_texts'] = []
        
        # Get all images
        images = []
        if msg.get('images'):
            images = msg['images']
        elif msg.get('image'):
            images = [msg['image']]
            
        if msg.get('do_ocr') and images:
            for img_path in images:
                ocr_tasks.append((i, img_path))
                
    if ocr_tasks:
        image_paths = [t[1] for t in ocr_tasks]
        logging.info(f"Processing {len(image_paths)} images...")
        
        # Run Batch OCR
        results = extract_text_batch(image_paths)
        
        # Map results back
        for t_idx, text_result in enumerate(results):
            original_msg_idx = ocr_tasks[t_idx][0]
            if text_result and not text_result.startswith("[Error"):
                cleaned = clean_text_for_ai(text_result)
                unique_msgs[original_msg_idx]['ocr_texts'].append(cleaned)
                # Combine into main ocr_text field for prompts
                unique_msgs[original_msg_idx]['ocr_text'] = "\n".join(unique_msgs[original_msg_idx]['ocr_texts'])
    
    logging.info("OCR Complete.")

    # 5. AUTO-CLASSIFICATION
    logging.info("Classifying messages...")
    classified_msgs = auto_select_messages(unique_msgs, use_ai=True)
    
    # Filter only "selected" messages (likely picks)
    selected_msgs = [m for m in classified_msgs if m.get('selected')]
    logging.info(f"Selected {len(selected_msgs)} likely pick messages out of {len(classified_msgs)}.")
    
    if not selected_msgs:
        logging.warning("No picks detected after classification.")
        return

    # 6. PARSING (AI FILL)
    logging.info("Generating AI Prompts and Parsing...")
    
    # Generate Prompt
    master_prompt = generate_ai_prompt(selected_msgs)
    
    # Call AI
    logging.info("Sending to AI Provider Pool...")
    result_json_str = None
    try:
        # Enforce a stronger model for the complex parsing task
        # Mistral-tiny often fails with large JSONs. Gemini Flash is better.
        result_json_str = pooled_completion(master_prompt, model="google/gemini-2.0-flash-exp:free", timeout=120)
        
        if not result_json_str:
            logging.error("AI Provider Pool failed to return data.")
            return

        result_obj = json.loads(result_json_str)
        
        # Post-Process: Unwrap if needed
        if isinstance(result_obj, dict) and 'picks' in result_obj:
            raw_picks = result_obj['picks']
            remapped = []
            for p in raw_picks:
                remapped.append({
                    "message_id": p.get("id"),
                    "capper_name": p.get("cn"),
                    "league": p.get("lg"),
                    "type": p.get("ty"),
                    "pick": p.get("p"),
                    "odds": p.get("od"),
                    "units": p.get("u", 1.0)
                })
            picks = smart_merge_odds(remapped)
        else:
            picks = result_obj if isinstance(result_obj, list) else []

        logging.info(f"Extracted {len(picks)} raw picks.")
        
        # 7. VALIDATION
        logging.info("Validating picks...")
        
        # Two-Pass Verification (Parsing Check)
        if not TwoPassVerifier.verify_parsing_result(picks):
             logging.warning("Low confidence in parsing. Result might be imperfect.")
             
        # Multi-Pick Validation
        _, reparse_ids = validate_and_flag_missing(selected_msgs, picks)
        if reparse_ids:
            logging.warning(f"Potential missing picks in {len(reparse_ids)} messages.")
            
        # Capper Verification
        # capper_results = verify_all_picks(selected_msgs, picks)
        # (Logging detail omitted for brevity)

    except json.JSONDecodeError:
        logging.error("AI returned invalid JSON.")
        logging.debug(result_json_str)
        return
    except Exception as e:
        logging.error(f"Parsing failed: {e}")
        return

    # 8. OUTPUT
    output_file = f"picks_{target_date}.json"
    with open(output_file, 'w') as f:
        json.dump(picks, f, indent=2)
        
    print("\n" + "="*50)
    print("   RESULTS   ")
    print("="*50)
    print(f"Total Unique Messages: {len(unique_msgs)}")
    print(f"Messages with Picks: {len(selected_msgs)}")
    print(f"Extracted Picks: {len(picks)}")
    print(f"Saved to: {output_file}")
    
    # Simple Table Output
    print(f"{'CAPPER':<20} | {'SPORT':<10} | {'PICK':<40} | {'ODDS':<6}")
    print("-" * 85)
    for p in picks:
        capper = (p.get('capper_name') or "Unknown")[:19]
        sport = (p.get('league') or "Unknown")[:9]
        pick_val = (p.get('pick') or "Unknown")[:39]
        odds = str(p.get('odds') or "")
        print(f"{capper:<20} | {sport:<10} | {pick_val:<40} | {odds:<6}")
    print("-" * 85)
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScraper stopped by user.")
    except Exception as e:
        logging.error(f"Fatal Error: {e}", exc_info=True)
