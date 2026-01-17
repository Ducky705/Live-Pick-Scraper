import argparse
import asyncio
import json
import os
import sys
import logging
from datetime import datetime
from pprint import pprint
import re
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Mock config if needed, or rely on src.config
from config import SESSION_FILE_PATH, TEMP_IMG_DIR
from src.telegram_client import TelegramManager
from src.auto_processor import auto_select_messages
from src.ocr_handler import extract_text_batch, extract_text_ai
from src.prompt_builder import generate_ai_prompt
from src.openrouter_client import openrouter_completion

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Dummy progress callback
def progress_callback(percent, status):
    print(f"[PROGRESS {percent}%] {status}")

async def list_channels():
    manager = TelegramManager()
    manager.set_progress_callback(progress_callback)
    
    print("Connecting to Telegram...")
    if not await manager.connect_client():
        print("Failed to connect. Session file might be missing or invalid.")
        return

    print("Fetching channels...")
    channels = await manager.get_channels()
    
    print("\n--- Available Channels ---")
    for ch in channels:
        name = ch['name'].encode('ascii', 'replace').decode('ascii')
        print(f"ID: {ch['id']} | Name: {name}")
    print("--------------------------\n")
    return channels

async def fetch_messages(channel_id, limit=10, date=None):
    manager = TelegramManager()
    manager.set_progress_callback(progress_callback)
    
    print(f"Connecting to Telegram (Channel: {channel_id})...")
    if not await manager.connect_client():
        print("Failed to connect.")
        return []

    # fetch_messages takes a list of ids
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    print(f"Fetching messages for date: {date}...")
    # Note: The underlying fetch_messages fetches by DATE, not count.
    # It will fetch everything for that date.
    messages = await manager.fetch_messages([channel_id], date)
    
    print(f"\nFetched {len(messages)} messages.")
    
    # Save to file for inspection
    with open('test_messages.json', 'w', encoding='utf-8') as f:
        serializable_msgs = []
        for m in messages:
            m_copy = m.copy()
            if 'pending_download' in m_copy: del m_copy['pending_download']
            if 'pending_downloads' in m_copy: del m_copy['pending_downloads']
            serializable_msgs.append(m_copy)
            
        json.dump(serializable_msgs, f, indent=2, default=str)
        
    print("Saved raw messages to test_messages.json")
    return messages

def assess_quality(original_msgs, parsed_result):
    """
    Analyzes the quality of OCR and Parsing.
    """
    print("\n" + "="*40)
    print("       QUALITY ASSESSMENT REPORT       ")
    print("="*40)
    
    # 1. OCR Quality
    print("\n--- OCR QUALITY ---")
    ocr_empty = 0
    ocr_short = 0
    ocr_good = 0
    total_images = 0
    
    for m in original_msgs:
        if m.get('images') or m.get('image'):
            ocr_texts = m.get('ocr_texts', [])
            if not ocr_texts:
                # Did we try OCR?
                if m.get('selected'):
                    print(f"[Msg {m['id']}] WARNING: Selected but no OCR text found.")
            
            for text in ocr_texts:
                total_images += 1
                clean_text = text.strip()
                if not clean_text:
                    ocr_empty += 1
                    print(f"[Msg {m['id']}] FAILED: OCR returned empty string.")
                elif len(clean_text) < 20:
                    ocr_short += 1
                    print(f"[Msg {m['id']}] POOR: OCR text very short (<20 chars): '{clean_text}'")
                else:
                    ocr_good += 1
                    # print(f"[Msg {m['id']}] OK: {len(clean_text)} chars extracted.")
    
    if total_images > 0:
        print(f"Total Images: {total_images}")
        print(f"Success Rate: {ocr_good}/{total_images} ({ocr_good/total_images*100:.1f}%)")
    else:
        print("No images found in selected messages.")

    # 2. Parser Quality
    print("\n--- PARSER QUALITY ---")
    
    if not parsed_result:
        print("FATAL: No result returned from AI.")
        return

    try:
        # Check if result is wrapped in JSON code block
        if isinstance(parsed_result, str):
            # Try cleaning markdown
            clean_res = parsed_result.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```")[1].split("```")[0].strip()
            
            data = json.loads(clean_res)
        else:
            data = parsed_result

        picks = data.get('picks', [])
        print(f"Total Picks Extracted: {len(picks)}")
        
        # Grading Criteria
        valid_picks = 0
        missing_critical = 0
        unknowns = 0
        
        for p in picks:
            is_valid = True
            issues = []
            
            # Critical Fields
            if not p.get('p') and not p.get('pick'):
                issues.append("Missing Pick Value")
                is_valid = False
            
            if p.get('od') is None and p.get('odds') is None:
                issues.append("Missing Odds")
                # Not necessarily invalid, but lower quality
            
            # Check for "Unknown" placeholders
            capper = p.get('cn') or p.get('capper_name')
            league = p.get('lg') or p.get('league')
            
            if capper in ["Unknown", "N/A", None]:
                issues.append("Unknown Capper")
                unknowns += 1
            
            if league in ["Unknown", "Other", None]:
                issues.append("Unknown League")
                unknowns += 1
                
            if is_valid:
                valid_picks += 1
            else:
                missing_critical += 1
            
            status = "[OK]" if not issues else "[FLAG]"
            print(f"{status} [Pick] {p.get('p') or p.get('pick')} | Issues: {', '.join(issues) if issues else 'None'}")

        print(f"Valid Picks (Structurally): {valid_picks}/{len(picks)}")
        print(f"Unknown Metadata Rate: {unknowns} occurrences")

    except json.JSONDecodeError:
        print("FATAL: AI Response was not valid JSON.")
        print("Raw Response preview:", str(parsed_result)[:500])
    except Exception as e:
        print(f"Error analyzing parser quality: {e}")

async def run_pipeline(channel_id, limit=5, date=None):
    # 1. Fetch
    messages = await fetch_messages(channel_id, limit, date)
    if not messages:
        return

    # Slice to limit (fetch_messages gets whole day)
    messages = messages[:int(limit)]
    print(f"Processing first {len(messages)} messages from the batch...")

    # 2. Auto Classification
    print("Running Auto-Classification (Heuristic)...")
    messages = auto_select_messages(messages, use_ai=False) 
    
    selected_msgs = [m for m in messages if m.get('selected')]
    print(f"Selected {len(selected_msgs)} potential picks.")

    if not selected_msgs:
        print("No messages selected for processing.")
        return

    # 3. OCR
    print("Running OCR on selected messages (Batch Mode)...")
    all_ocr_tasks = []
    # Collect all image paths
    for i, msg in enumerate(selected_msgs):
        images_to_process = []
        if msg.get('images'): images_to_process = msg['images']
        elif msg.get('image'): images_to_process = [msg['image']]
        
        if images_to_process:
            for img_path in images_to_process:
                all_ocr_tasks.append((i, img_path))
    
    if all_ocr_tasks:
        # Process in sub-batches of 10 images to prevent timeouts
        BATCH_SIZE = 10
        total_tasks = len(all_ocr_tasks)
        print(f"Total images to OCR: {total_tasks}. Processing in batches of {BATCH_SIZE}...")
        
        for i in range(0, total_tasks, BATCH_SIZE):
            batch_tasks = all_ocr_tasks[i:i+BATCH_SIZE]
            batch_paths = [t[1] for t in batch_tasks]
            
            print(f"  Processing OCR batch {i//BATCH_SIZE + 1}/{(total_tasks+BATCH_SIZE-1)//BATCH_SIZE}...")
            results = extract_text_batch(batch_paths)
            
            for b_idx, text_result in enumerate(results):
                original_msg_idx = batch_tasks[b_idx][0]
                if 'ocr_texts' not in selected_msgs[original_msg_idx]:
                    selected_msgs[original_msg_idx]['ocr_texts'] = []
                selected_msgs[original_msg_idx]['ocr_texts'].append(text_result)
                
                # Print preview for CLI user
                print(f"\n[OCR Preview - Msg {original_msg_idx}]")
                preview_text = text_result[:200] if len(text_result) > 200 else text_result
                safe_preview = preview_text.encode('ascii', 'replace').decode('ascii')
                print(f"{safe_preview}...")
            
            # Small pause between batches
            await asyncio.sleep(2)

    # 4. Generate Prompt
    print("\nGenerating AI Prompt...")
    master_prompt = generate_ai_prompt(selected_msgs)
    
    # 5. Call AI
    print("Calling AI for Parsing (Model: google/gemini-2.0-flash-exp:free)...")
    try:
        response = openrouter_completion(master_prompt, model="google/gemini-2.0-flash-exp:free")
        
        # Save raw result
        with open('test_results_raw.txt', 'w', encoding='utf-8') as f:
            f.write(response)
            
        print("\n--- AI Response Received ---")
        
        # Try parse
        try:
            # Handle potential markdown wrapping
            clean_res = response.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(clean_res)
            
            # Save structured results
            with open('test_results.json', 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2)
            
            # Run Quality Assessment
            assess_quality(selected_msgs, parsed)
                
        except json.JSONDecodeError:
            print("Response was not valid JSON.")
            print(response[:500])
            
    except Exception as e:
        print(f"AI Call failed: {e}")

async def debug_image(image_path):
    print(f"Debugging Image: {image_path}")
    if not os.path.exists(image_path):
        print("File not found.")
        return

    print("Running AI OCR (Single Image)...")
    text = extract_text_ai(image_path)
    print("\n--- OCR Result ---")
    print(text)
    print("------------------")

def main():
    parser = argparse.ArgumentParser(description="Telegram Scraper CLI Test Suite")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # List Channels
    subparsers.add_parser('list-channels', help='List available Telegram channels')

    # Fetch
    fetch_parser = subparsers.add_parser('fetch', help='Fetch messages from a channel')
    fetch_parser.add_argument('channel_id', help='Channel ID')
    fetch_parser.add_argument('--limit', default=10, help='Limit number of messages')
    fetch_parser.add_argument('--date', help='Target date (YYYY-MM-DD)')

    # Pipeline
    pipe_parser = subparsers.add_parser('pipeline', help='Run full pipeline on a channel')
    pipe_parser.add_argument('channel_id', help='Channel ID')
    pipe_parser.add_argument('--limit', default=5, help='Number of messages to process')
    pipe_parser.add_argument('--date', help='Target date (YYYY-MM-DD)')

    # Debug Image
    img_parser = subparsers.add_parser('debug-image', help='Run OCR on a specific image')
    img_parser.add_argument('path', help='Path to image file')

    args = parser.parse_args()

    if args.command == 'list-channels':
        asyncio.run(list_channels())
    elif args.command == 'fetch':
        asyncio.run(fetch_messages(args.channel_id, args.limit, args.date))
    elif args.command == 'pipeline':
        asyncio.run(run_pipeline(args.channel_id, args.limit, args.date))
    elif args.command == 'debug-image':
        asyncio.run(debug_image(args.path))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
