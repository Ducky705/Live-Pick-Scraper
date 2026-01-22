import asyncio
import logging
import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
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
from src.prompt_builder import generate_ai_prompt, generate_compact_prompt
from src.provider_pool import pooled_completion
from src.utils import clean_text_for_ai, smart_merge_odds
from src.two_pass_verifier import TwoPassVerifier
from src.multi_pick_validator import validate_and_flag_missing
from src.multi_capper_verifier import verify_all_picks
from src.pick_deduplicator import deduplicate_by_capper

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
        logging.info("Session not found or expired. Starting interactive authentication...")
        try:
            client = await tg.get_client()
            # Interactive login in the terminal
            await client.start()
            
            if not await client.is_user_authorized():
                logging.error("Authentication failed. Please try again.")
                return
            logging.info("Authentication successful!")
        except Exception as e:
            logging.error(f"Authentication Error: {e}")
            return

    # Twitter
    tw = TwitterManager()
    
    # 2. FETCH DATA (Yesterday in Eastern Time)
    ET = timezone(timedelta(hours=-5))  # EST (use -4 for EDT if needed)
    now_et = datetime.now(ET)
    yesterday_et = now_et - timedelta(days=1)
    target_date = yesterday_et.strftime("%Y-%m-%d")
    logging.info(f"Target Date: {target_date} (Eastern Time, now ET: {now_et.strftime('%Y-%m-%d %H:%M')})")
    
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

    # 6. PARSING (AI FILL) - HYBRID PARALLEL STRATEGY
    logging.info("Generating AI Prompts and Parsing (Hybrid Mode)...")
    
    # Configuration
    BATCH_SIZE = 10  # Messages per batch (reduced for better accuracy)
    MAX_WORKERS = 3  # Parallel threads (respects rate limits)
    
    def process_batch(batch_msgs, batch_idx):
        """Process a single batch of messages using hybrid strategy."""
        try:
            # Use compact prompt for fast models
            compact_prompt = generate_compact_prompt(batch_msgs)
            
            # Call Hybrid Pool (tries fast models first, then DeepSeek R1)
            result_str = pooled_completion(compact_prompt, timeout=120)
            
            if not result_str:
                logging.warning(f"Batch {batch_idx}: No result from pool.")
                return []
            
            result_obj = json.loads(result_str)
            
            if isinstance(result_obj, dict) and 'picks' in result_obj:
                return result_obj['picks']
            elif isinstance(result_obj, list):
                return result_obj
            else:
                return []
                
        except json.JSONDecodeError as e:
            logging.error(f"Batch {batch_idx}: Invalid JSON - {e}")
            return []
        except Exception as e:
            logging.error(f"Batch {batch_idx}: Error - {e}")
            return []
    
    # Split into batches
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    batches = [selected_msgs[i:i+BATCH_SIZE] for i in range(0, len(selected_msgs), BATCH_SIZE)]
    logging.info(f"Processing {len(batches)} batches ({BATCH_SIZE} msgs each) with {MAX_WORKERS} workers...")
    
    all_raw_picks = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_batch, batch, idx): idx for idx, batch in enumerate(batches)}
        
        for future in as_completed(futures):
            batch_idx = futures[future]
            try:
                batch_picks = future.result()
                all_raw_picks.extend(batch_picks)
                logging.info(f"Batch {batch_idx}: Extracted {len(batch_picks)} picks.")
            except Exception as e:
                logging.error(f"Batch {batch_idx}: Failed - {e}")
    
    # Remap minified keys to full keys
    result_json_str = None
    try:
        remapped = []
        for p in all_raw_picks:
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

        logging.info(f"Extracted {len(picks)} raw picks.")
        
        # 6.5 POST-PARSE DEDUPLICATION
        # Different leakers often repost the same capper's picks with different formatting
        # Deduplicate by normalized (capper_name, pick) after parsing
        logging.info("Deduplicating parsed picks...")
        picks = deduplicate_by_capper(picks)
        logging.info(f"After dedup: {len(picks)} unique picks.")
        
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

        # 7.5 GRADING
        logging.info("Grading picks against ESPN scores...")
        try:
            from src.grader import grade_picks
            from src.score_fetcher import fetch_scores_for_date
            
            scores = fetch_scores_for_date(target_date)
            logging.info(f"Fetched {len(scores)} game scores")
            
            picks = grade_picks(picks, scores)
            
            # Count results
            wins = sum(1 for p in picks if p.get('result') == 'Win')
            losses = sum(1 for p in picks if p.get('result') == 'Loss')
            pending = sum(1 for p in picks if p.get('result') in ['Pending', 'Pending/Unknown', None, ''])
            
            logging.info(f"Grading complete: {wins} Wins, {losses} Losses, {pending} Pending")
        except Exception as e:
            logging.error(f"Grading failed: {e}")

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
    print(f"{'CAPPER':<20} | {'SPORT':<10} | {'PICK':<35} | {'ODDS':<6} | {'RESULT':<8}")
    print("-" * 95)
    for p in picks:
        capper = (p.get('capper_name') or "Unknown")[:19]
        sport = (p.get('league') or "Unknown")[:9]
        pick_val = (p.get('pick') or "Unknown")[:34]
        odds = str(p.get('odds') or "")[:5]
        result = (p.get('result') or "")[:7]
        print(f"{capper:<20} | {sport:<10} | {pick_val:<35} | {odds:<6} | {result:<8}")
    print("-" * 95)
    
    # 9. SUPABASE UPLOAD
    # Check for --dry-run or --no-upload flag
    dry_run = '--dry-run' in sys.argv or '--no-upload' in sys.argv
    
    if dry_run:
        logging.info("Skipping Supabase upload (--dry-run mode)")
        print("\n[DRY RUN] Supabase upload skipped. Review picks above and run without --dry-run to upload.")
    else:
        logging.info("Uploading picks to Supabase...")
        try:
            from src.supabase_client import upload_picks
            
            result = upload_picks(picks, target_date)
            
            if result.get('success'):
                logging.info(f"Successfully uploaded {result.get('count', 0)} picks to Supabase")
                print(f"\n[SUPABASE] Uploaded {result.get('count', 0)} picks successfully!")
            else:
                logging.error(f"Supabase upload failed: {result.get('error')}")
                if result.get('details'):
                    for detail in result['details'][:5]:
                        logging.warning(f"  {detail}")
        except Exception as e:
            logging.error(f"Supabase upload error: {e}")
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScraper stopped by user.")
    except Exception as e:
        logging.error(f"Fatal Error: {e}", exc_info=True)
