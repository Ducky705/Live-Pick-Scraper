import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

# Ensure src is in path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "src"))

from config import LOG_DIR, OUTPUT_DIR, TARGET_DISCORD_CHANNEL_ID, TARGET_TELEGRAM_CHANNEL_ID
from src.auto_processor import auto_select_messages
from src.deduplicator import Deduplicator
from src.discord_client import DiscordScraper
from src.ocr_handler import extract_text_batch
from src.telegram_client import TelegramManager
from src.twitter_client import TwitterManager
from src.utils import clean_text_for_ai

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "cli_scraper.log")),
        logging.StreamHandler(sys.stdout),
    ],
)


async def main():
    print("=" * 50)
    print("   TELEGRAM & TWITTER SCRAPER CLI   ")
    print("=" * 50)

    # 1. INITIALIZATION
    logging.info("Initializing Clients...")

    # Early validation of critical env vars
    if not os.getenv("OPENROUTER_API_KEY"):
        logging.warning("OPENROUTER_API_KEY not set — AI extraction will fail. Set it in .env or environment.")
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        logging.warning("SUPABASE_URL/SUPABASE_KEY not set — uploads will fail if enabled.")

    # Telegram
    from config import API_HASH, API_ID

    tg = TelegramManager()

    if not API_ID or not API_HASH:
        logging.warning("Telegram credentials missing (API_ID/API_HASH). Skipping Telegram fetch.")
        tg_msgs = []
    else:
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
    if not API_ID or not API_HASH:
        logging.info("Skipping Telegram fetch (Missing Credentials).")
        tg_msgs = []
    else:
        # Support multiple comma-separated channel IDs from env
        target_ids = []
        if TARGET_TELEGRAM_CHANNEL_ID:
            target_ids = [tid.strip() for tid in TARGET_TELEGRAM_CHANNEL_ID.split(",") if tid.strip()]

        if target_ids:
            logging.info(f"Fetching Telegram messages from {len(target_ids)} channels: {target_ids}...")
            tg_msgs = await tg.fetch_messages(target_ids, target_date)
            logging.info(f"Fetched {len(tg_msgs)} Telegram messages.")
        else:
            logging.warning("No TARGET_TELEGRAM_CHANNEL_ID configured.")
            tg_msgs = []

    # Fetch Twitter
    logging.info("Fetching Tweets...")
    tw_msgs = await tw.fetch_tweets(target_date=target_date)
    logging.info(f"Fetched {len(tw_msgs)} Tweets.")

    # Fetch Discord
    discord_msgs = []
    if TARGET_DISCORD_CHANNEL_ID:
        logging.info("Fetching Discord messages...")
        ds = DiscordScraper()

        # Support multiple comma-separated channel IDs
        discord_ids = [did.strip() for did in TARGET_DISCORD_CHANNEL_ID.split(",") if did.strip()]

        for did in discord_ids:
            logging.info(f"Fetching from Discord Channel: {did}...")
            msgs = ds.fetch_messages(did, limit=50)
            discord_msgs.extend(msgs)

        logging.info(f"Fetched {len(discord_msgs)} Discord messages.")
    else:
        logging.info("Skipping Discord fetch (No TARGET_DISCORD_CHANNEL_ID).")

    # Combine
    all_msgs = tg_msgs + tw_msgs + discord_msgs

    # 3. DEDUPLICATION
    logging.info("Deduplicating messages...")
    unique_msgs = Deduplicator.merge_messages(all_msgs)
    logging.info(f"Unique Messages: {len(unique_msgs)}")

    # Parse --limit
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            try:
                limit = int(arg.split("=")[1])
            except: pass
    
    if limit and len(unique_msgs) > limit:
        logging.info(f"Limiting to first {limit} messages (requested via CLI).")
        unique_msgs = unique_msgs[:limit]

    if not unique_msgs:
        logging.warning("No messages found. Exiting.")
        return

    # 4. OCR & IMAGE PROCESSING
    logging.info("Starting OCR processing (Smart Mode)...")
    
    # 4b. START ASYNC SCORE FETCHING EARLY (Parallel Optimization)
    # We fetch ALL leagues to be safe and populate cache while OCR/LLM runs.
    from src.score_fetcher import async_fetch_scores_for_date
    logging.info("Starting background score fetching for all leagues...")
    score_fetch_task = asyncio.create_task(async_fetch_scores_for_date(target_date))

    # Prepare batch
    ocr_tasks = []  # (msg_index, image_path)

    for i, msg in enumerate(unique_msgs):
        msg["ocr_texts"] = []

        # Get all images
        images = []
        if msg.get("images"):
            images = msg["images"]
        elif msg.get("image"):
            images = [msg["image"]]

        if msg.get("do_ocr") and images:
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
                unique_msgs[original_msg_idx]["ocr_texts"].append(cleaned)
                # Combine into main ocr_text field for prompts
                unique_msgs[original_msg_idx]["ocr_text"] = "\n".join(unique_msgs[original_msg_idx]["ocr_texts"])

    logging.info("OCR Complete.")

    # DEBUG: Save messages for feedback loop
    debug_file = os.path.join(OUTPUT_DIR, "debug_msgs.json")
    with open(debug_file, "w", encoding="utf-8") as f:
        json.dump(unique_msgs, f, indent=2, default=str)
    logging.info(f"Saved debug messages to {debug_file}")

    # 5. AUTO-CLASSIFICATION
    logging.info("Classifying messages...")
    classified_msgs = auto_select_messages(unique_msgs, use_ai=True)

    # Filter only "selected" messages (likely picks)
    selected_msgs = [m for m in classified_msgs if m.get("selected")]
    logging.info(f"Selected {len(selected_msgs)} likely pick messages out of {len(classified_msgs)}.")

    if not selected_msgs:
        logging.warning("No picks detected after classification.")
        # Determine if we should wait for scores or just cancel
        if not score_fetch_task.done():
            score_fetch_task.cancel()
        return

    # 6. EXTRACTION PIPELINE (Rule-Based + AI + Validation)
    logging.info("Starting Extraction Pipeline...")
    from src.extraction_pipeline import ExtractionPipeline

    picks = ExtractionPipeline.run(selected_msgs, target_date)

    # 7. GRADING
    logging.info("Grading picks against ESPN scores...")
    try:
        from src.grader import grade_picks
        from src.grading.constants import LEAGUE_ALIASES_MAP
        # from src.score_fetcher import fetch_scores_for_date # Deprecated sync call

        logging.info(f"Waiting for score fetching to complete...")
        scores = await score_fetch_task
        logging.info(f"Fetched {len(scores)} game scores")

        picks = grade_picks(picks, scores)

        # Count results
        wins = sum(1 for p in picks if p.get("result") == "Win")
        losses = sum(1 for p in picks if p.get("result") == "Loss")
        pending = sum(1 for p in picks if p.get("result") in ["Pending", "Pending/Unknown", None, ""])

        logging.info(f"Grading complete: {wins} Wins, {losses} Losses, {pending} Pending")
    except Exception as e:
        logging.error(f"Grading failed: {e}")

    # 8. OUTPUT
    output_file = os.path.join(OUTPUT_DIR, f"picks_{target_date}.json")
    with open(output_file, "w") as f:
        json.dump(picks, f, indent=2)

    # RALPH LOOP ITERATION 11: Export to Client Public Folder for Live Dashboard
    try:
        import shutil

        client_public_dir = os.path.join(os.path.dirname(__file__), "client", "public")
        if not os.path.exists(client_public_dir):
            os.makedirs(client_public_dir)

        latest_picks_file = os.path.join(client_public_dir, "latest_picks.json")
        shutil.copy2(output_file, latest_picks_file)
        logging.info(f"Deployed picks to Dashboard: {latest_picks_file}")
    except Exception as e:
        logging.error(f"Failed to deploy picks to Dashboard: {e}")

    print("\n" + "=" * 50)
    print("   RESULTS   ")
    print("=" * 50)
    print(f"Total Unique Messages: {len(unique_msgs)}")
    print(f"Messages with Picks: {len(selected_msgs)}")
    print(f"Extracted Picks: {len(picks)}")
    print(f"Saved to: {output_file}")

    # Simple Table Output
    print(f"{'CAPPER':<20} | {'SPORT':<10} | {'PICK':<35} | {'ODDS':<6} | {'RESULT':<8}")
    print("-" * 95)
    for p in picks:
        capper_raw = p.get("capper_name") or "Unknown"
        capper = capper_raw.encode("ascii", "replace").decode("ascii")[:19]

        sport = (p.get("league") or "Unknown")[:9]

        pick_raw = p.get("pick") or "Unknown"
        pick_val = pick_raw.encode("ascii", "replace").decode("ascii")[:34]

        odds = str(p.get("odds") or "")[:5]
        result = (p.get("result") or "")[:7]
        print(f"{capper:<20} | {sport:<10} | {pick_val:<35} | {odds:<6} | {result:<8}")
    print("-" * 95)

    # 9. SUPABASE UPLOAD
    # Check for --dry-run or --no-upload flag
    # FORCE DRY RUN per user instruction
    dry_run = True  # '--dry-run' in sys.argv or '--no-upload' in sys.argv

    if dry_run:
        logging.info("Skipping Supabase upload (--dry-run mode)")
        print("\n[DRY RUN] Supabase upload skipped. Review picks above and run without --dry-run to upload.")
    else:
        logging.info("Uploading picks to Supabase...")
        try:
            from src.supabase_client import upload_picks

            result = upload_picks(picks, target_date)

            if result.get("success"):
                logging.info(f"Successfully uploaded {result.get('count', 0)} picks to Supabase")
                print(f"\n[SUPABASE] Uploaded {result.get('count', 0)} picks successfully!")
            else:
                logging.error(f"Supabase upload failed: {result.get('error')}")
                if result.get("details"):
                    for detail in result["details"][:5]:
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
