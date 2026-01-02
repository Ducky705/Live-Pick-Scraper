import sys
import os
import json
import shutil
import argparse
import asyncio
from datetime import datetime

# Add root to sys.path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from src.ocr_handler import extract_text
from src.prompt_builder import generate_ai_prompt
from src.openrouter_client import openrouter_completion
from config import BASE_DIR

MANIFEST_PATH = os.path.join(current_dir, 'manifest.json')
SAMPLES_DIR = os.path.join(current_dir, 'samples')

def load_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return []
    with open(MANIFEST_PATH, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_manifest(data):
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def add_test_case(image_path, text_content=None, auto_baseline=False):
    if not os.path.exists(SAMPLES_DIR):
        os.makedirs(SAMPLES_DIR)
        
    filename = os.path.basename(image_path)
    target_path = os.path.join(SAMPLES_DIR, filename)
    
    # Copy file
    if os.path.abspath(image_path) != os.path.abspath(target_path):
        shutil.copy2(image_path, target_path)
    
    print(f"Running OCR on {filename}...")
    # Use relative path for ocr_handler as it expects
    rel_path_for_ocr = os.path.join('tests', 'samples', filename)
    ocr_result = extract_text(rel_path_for_ocr)
    
    expected_data = []
    
    if auto_baseline:
        print("Generating auto-baseline with AI...")
        fake_item = {
            'id': 0,
            'text': text_content or '',
            'ocr_texts': [ocr_result],
            'ocr_text': ocr_result
        }
        prompt = generate_ai_prompt([fake_item])
        try:
            result_str = openrouter_completion(prompt)
            result_json = json.loads(result_str)
            expected_data = result_json.get('picks', [])
            print(f"AI found {len(expected_data)} picks.")
        except Exception as e:
            print(f"Auto-baseline failed: {e}")
            expected_data = []
    else:
        print("\n--- OCR Result ---")
        print(ocr_result)
        print("------------------\n")
        print("Please enter the expected JSON output for this image.")
        print("Format: [{'cn': 'CapperName', 'p': 'Team -5', ...}]")
        print("Ensure you enter valid JSON array.")
        
        while True:
            try:
                user_input = input("Expected JSON: ")
                expected_data = json.loads(user_input)
                if not isinstance(expected_data, list):
                    print("Error: Must be a list of picks.")
                    continue
                break
            except json.JSONDecodeError:
                print("Error: Invalid JSON. Try again.")
            
    case_id = f"case_{int(datetime.now().timestamp())}_{filename.split('.')[0]}"
    
    new_case = {
        "id": case_id,
        "image_file": f"samples/{filename}",
        "description": f"Imported from {filename}",
        "input_text": text_content or "",
        "expected_picks": expected_data
    }
    
    manifest = load_manifest()
    manifest.append(new_case)
    save_manifest(manifest)
    print(f"Test case {case_id} added successfully.")

def run_test_case(case):
    print(f"Running Case: {case['id']} ({case.get('description')})")
    
    # Prepare Input
    # ocr_handler expects path relative to BASE_DIR (root)
    # Our manifest has 'samples/filename.jpg', which is relative to tests/
    # So we need 'tests/samples/filename.jpg'
    rel_image_path = os.path.join('tests', case['image_file'])
    
    # 1. OR OCR (We run it again to ensure pipeline is tested, though we could cache)
    ocr_text = extract_text(rel_image_path)
    if "Error" in ocr_text and not "OCR Error" in ocr_text: # Loose check
         pass # might be valid error if image missing
         
    # 2. Build Prompt
    fake_item = {
        'id': case['id'],
        'text': case.get('input_text', ''),
        'ocr_texts': [ocr_text],
        'ocr_text': ocr_text # Fallback
    }
    
    prompt = generate_ai_prompt([fake_item])
    
    # 3. Call AI
    try:
        print("  Sending to AI...")
        result_str = openrouter_completion(prompt)
        result_json = json.loads(result_str)
        actual_picks = result_json.get('picks', [])
        
        # 4. Compare
        expected = case['expected_picks']
        return compare_results(expected, actual_picks)
        
    except Exception as e:
        print(f"  FAILED: Execution Error - {e}")
        return False

def compare_results(expected, actual):
    # exact match on 'p' (pick) and 'cn' (capper) is most important
    # verification is strict: list length must match
    
    validation_passed = True
    
    print(f"  Expected {len(expected)} picks, Got {len(actual)} picks.")
    
    if len(expected) != len(actual):
        print("  [FAIL] Count Mismatch")
        validation_passed = False
    
    # Check for missing picks
    for exp in expected:
        found = False
        exp_pick = exp.get('p')
        exp_pick_norm = exp_pick.lower().strip() if exp_pick else ""
        
        for act in actual:
            act_pick = act.get('p')
            act_pick_norm = act_pick.lower().strip() if act_pick else ""
            
            # Match logic
            # If both are None/Empty -> Match
            if not exp_pick_norm and not act_pick_norm:
                found = True
            # If content matches loosely
            elif exp_pick_norm and act_pick_norm and (exp_pick_norm in act_pick_norm or act_pick_norm in exp_pick_norm):
                found = True
            
            if found:
                # basic check on capper
                exp_cn = exp.get('cn')
                act_cn = act.get('cn')
                if exp_cn and act_cn:
                    if exp_cn.lower() not in act_cn.lower():
                        print(f"  [WARN] Capper mismatch for {exp_pick}: Exp '{exp_cn}' vs Act '{act_cn}'")
                break
        
        if not found:
            print(f"  [FAIL] Missing Pick: {exp.get('p')}")
            validation_passed = False
            
    if validation_passed:
        print("  [PASS] All expected picks found.")
        return True
    else:
        print("  [FAIL] Verification Failed.")
        print(f"  Actual Output: {json.dumps(actual, indent=2)}")
        return False

async def fetch_from_telegram(channel_idx=None, msg_idx=None, list_only=False, auto_baseline=False):
    from src.telegram_client import tg_manager
    from config import TEMP_IMG_DIR
    
    # Connect
    if not await tg_manager.connect_client():
        print("Error: Could not connect to Telegram. Check auth.")
        return

    # 1. Channel Selection
    channels = await tg_manager.get_channels()
    
    selected_ch = None
    if channel_idx:
        if 1 <= channel_idx <= len(channels):
            selected_ch = channels[channel_idx-1]
        else:
            print(f"Error: Invalid channel index {channel_idx}")
            return
    else:
        # Interactive
        print("\nAvailable Channels:")
        for i, ch in enumerate(channels):
            print(f"{i+1}. {ch['name']} (ID: {ch['id']})")
            
        try:
            val = input("\nSelect Channel # (or 0 to cancel): ")
            idx = int(val) - 1
            if idx < 0: return
            selected_ch = channels[idx]
        except:
            print("Invalid selection.")
            return
            
    print(f"\nFetching recent messages from {selected_ch['name']}...")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    messages = await tg_manager.fetch_messages([selected_ch['id']], today_str)
    image_msgs = [m for m in messages if m.get('images') or m.get('image')]
    
    if not image_msgs:
        print(f"No messages with images found for TODAY ({today_str}). Trying YESTERDAY...")
        from datetime import timedelta
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        messages = await tg_manager.fetch_messages([selected_ch['id']], yesterday_str)
        image_msgs = [m for m in messages if m.get('images') or m.get('image')]
        
    if not image_msgs:
        print("No matches found in last 2 days.")
        return
        
    print(f"\nFound {len(image_msgs)} messages with images:")
    for i, m in enumerate(image_msgs):
        caption = (m.get('text') or "")[:50].replace('\n', ' ')
        try:
            # Safe print for emoji captions
            safe_cap = caption.encode('utf-8', 'replace').decode('utf-8')
            print(f"{i+1}. [ID: {m['id']}] {safe_cap}...")
        except:
            print(f"{i+1}. [ID: {m['id']}] (Caption Error)...")

    if list_only:
        return

    # 2. Message Selection
    target_msg = None
    if msg_idx:
        if 1 <= msg_idx <= len(image_msgs):
            target_msg = image_msgs[msg_idx-1]
        else:
            print(f"Error: Invalid message index {msg_idx}. Only {len(image_msgs)} available.")
            return
    else:
        try:
            val = input("\nSelect Message # to import: ")
            sel_idx = int(val) - 1
            target_msg = image_msgs[sel_idx]
        except:
            print("Invalid selection.")
            return

    # Process Selection
    src_images = target_msg.get('images', [])
    if not src_images and target_msg.get('image'):
        src_images = [target_msg.get('image')]
        
    if not src_images:
        print("Error: Message has no image path.")
        return
        
    # Take first image for now
    web_path = src_images[0]
    filename = os.path.basename(web_path)
    # config.TEMP_IMG_DIR is absolute path
    abs_src_path = os.path.join(TEMP_IMG_DIR, filename)
    
    if not os.path.exists(abs_src_path):
        print(f"Error: Image file missing at {abs_src_path}")
        return
        
    print(f"\nImporting {filename}...")
    add_test_case(abs_src_path, target_msg.get('text'), auto_baseline=auto_baseline)

def main():
    parser = argparse.ArgumentParser(description='Scraper Verify Tool')
    subparsers = parser.add_subparsers(dest='command')
    
    # Add Command
    add_parser = subparsers.add_parser('add', help='Add a test case')
    add_parser.add_argument('image', help='Path to image file')
    add_parser.add_argument('--text', help='Caption text', default='')
    add_parser.add_argument('--auto-baseline', action='store_true', help='Use AI to generate initial expectation')
    
    # Run Command
    run_parser = subparsers.add_parser('run', help='Run all tests')
    
    # Fetch Command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch samples from Telegram')
    fetch_parser.add_argument('--channel', type=int, help='Channel Index (1-based)')
    fetch_parser.add_argument('--msg', type=int, help='Message Index (1-based)')
    fetch_parser.add_argument('--list-only', action='store_true', help='List messages and exit')
    fetch_parser.add_argument('--auto-baseline', action='store_true', help='Use AI to generate initial expectation')
    
    # List Command
    list_parser = subparsers.add_parser('list', help='List available Telegram channels')

    # Update Baselines Command
    update_parser = subparsers.add_parser('update-baselines', help='Re-generate expected picks for all cases')

    args = parser.parse_args()
    
    if args.command == 'add':
        add_test_case(args.image, args.text, args.auto_baseline)
    elif args.command == 'run':
        manifest = load_manifest()
        if not manifest:
            print("No test cases found.")
            return
            
        passed = 0
        total = 0
        for case in manifest:
            total += 1
            if run_test_case(case):
                passed += 1
        
        print(f"\nSummary: {passed}/{total} Passed")
    elif args.command == 'fetch':
        asyncio.run(fetch_from_telegram(channel_idx=args.channel, msg_idx=args.msg, list_only=args.list_only, auto_baseline=args.auto_baseline))
    elif args.command == 'list':
        asyncio.run(list_channels())
    elif args.command == 'update-baselines':
        manifest = load_manifest()
        if not manifest:
            print("No test cases found.")
            return
            
        print(f"Updating baselines for {len(manifest)} cases...")
        updated_count = 0
        
        for case in manifest:
            print(f"Updating Case: {case['id']} ({case.get('description')})")
            
            # Prepare Input
            rel_image_path = os.path.join('tests', case['image_file'])
            
            # 1. New OCR
            ocr_text = extract_text(rel_image_path)
            if "Error" in ocr_text and not "OCR Error" in ocr_text: 
                 print(f"  [WARN] OCR Error: {ocr_text}")
                 
            # 2. Build Prompt
            fake_item = {
                'id': case['id'],
                'text': case.get('input_text', ''),
                'ocr_texts': [ocr_text],
                'ocr_text': ocr_text 
            }
            
            prompt = generate_ai_prompt([fake_item])
            
            # 3. Call AI
            try:
                print("  Sending to AI...")
                result_str = openrouter_completion(prompt)
                result_json = json.loads(result_str)
                new_picks = result_json.get('picks', [])
                
                case['expected_picks'] = new_picks
                print(f"  -> Updated with {len(new_picks)} picks.")
                updated_count += 1
                
            except Exception as e:
                print(f"  FAILED: Execution Error - {e}")
        
        if updated_count > 0:
            save_manifest(manifest)
            print(f"\nSuccessfully updated {updated_count} test cases.")
    else:
        # Default to interactive fetch if no command? No, help.
        parser.print_help()

if __name__ == "__main__":
    main()
