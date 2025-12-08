# main.py
import sys
import os
import threading
import asyncio
import logging
import time
import platform
import webview # Requires: pip install pywebview
from flask import Flask, render_template, request, jsonify

# Import config to get paths
from config import TEMP_IMG_DIR, BASE_DIR, EXEC_DIR

# --- LOGGING SETUP ---
# Redirect stdout/stderr to a log file if frozen, so you can debug crashes
if getattr(sys, 'frozen', False):
    log_path = os.path.join(EXEC_DIR, 'app_debug.log')
    try:
        sys.stdout = open(log_path, 'w')
        sys.stderr = sys.stdout
    except Exception:
        pass

from src.telegram_client import tg_manager
from src.ocr_handler import extract_text
from src.prompt_builder import generate_ai_prompt, generate_revision_prompt, generate_smart_fill_prompt
from src.utils import detect_common_watermark, filter_text, backfill_odds, is_ad_content, cleanup_temp_images
from src.score_fetcher import fetch_scores_for_date
from src.grader import grade_picks

try:
    from src.supabase_client import fetch_all_cappers, upload_picks
except ImportError:
    def fetch_all_cappers(): return []
    def upload_picks(p, d): return {'success': False, 'error': 'Supabase module missing'}

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- ASYNC LOOP SETUP ---
loop = asyncio.new_event_loop()

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

t = threading.Thread(target=start_background_loop, args=(loop,), daemon=True)
t.start()

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

_score_cache = {}

def background_score_fetch(target_date):
    try:
        scores = fetch_scores_for_date(target_date)
        _score_cache[target_date] = scores
    except Exception as e:
        print(f"[Background] Score fetch failed: {e}")

# --- FLASK ROUTES ---

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    try:
        is_authorized = run_async(tg_manager.connect_client())
        return jsonify({'authorized': is_authorized})
    except Exception as e: return jsonify({'authorized': False, 'error': str(e)})

@app.route('/api/send_code', methods=['POST'])
def send_code():
    phone = request.json.get('phone')
    try:
        run_async(tg_manager.send_code(phone))
        return jsonify({'status': 'success'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/verify_code', methods=['POST'])
def verify_code():
    code = request.json.get('code')
    password = request.json.get('password')
    try:
        result = run_async(tg_manager.sign_in(code, password))
        return jsonify({'status': result})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/get_channels', methods=['GET'])
def get_channels():
    try:
        channels = run_async(tg_manager.get_channels())
        return jsonify(channels)
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/fetch_messages', methods=['POST'])
def fetch_messages():
    cleanup_temp_images(TEMP_IMG_DIR)
    data = request.json
    channel_ids = data.get('channel_id')
    target_date = data.get('date')
    
    if target_date:
        threading.Thread(target=background_score_fetch, args=(target_date,), daemon=True).start()

    try:
        msgs = run_async(tg_manager.fetch_messages(channel_ids, target_date))
        return jsonify(msgs)
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/detect_watermark', methods=['POST'])
def api_detect_watermark():
    data = request.json
    messages = data.get('messages', [])
    ocr_texts = []
    for msg in messages:
        if msg.get('ocr_text'): ocr_texts.append(msg.get('ocr_text'))
        if msg.get('text'): ocr_texts.append(msg['text'])
    detected = detect_common_watermark(ocr_texts)
    return jsonify({'watermark': detected})

@app.route('/api/generate_prompt', methods=['POST'])
def api_generate_prompt():
    data = request.json
    selected_messages = data.get('messages', [])
    watermark_filter = data.get('watermark', '').strip()
    
    processed_messages = []
    
    for msg in selected_messages:
        full_text = (msg.get('text', '') + " " + (msg.get('ocr_text', '') or "")).strip()
        if is_ad_content(full_text):
            continue 

        processed_msg = msg.copy()
        
        if msg.get('image') and msg.get('do_ocr') and not msg.get('ocr_text'):
            try:
                raw_ocr = extract_text(msg['image'])
                processed_msg['ocr_text'] = raw_ocr
            except Exception as e:
                processed_msg['ocr_text'] = "" 
        else:
             processed_msg['ocr_text'] = msg.get('ocr_text', "")

        if processed_msg.get('ocr_text'):
            processed_msg['ocr_text'] = filter_text(processed_msg['ocr_text'], watermark_filter)
        if processed_msg.get('text'):
            processed_msg['text'] = filter_text(processed_msg['text'], watermark_filter)
            
        processed_messages.append(processed_msg)
            
    MAX_CHARS = 150000 
    prompts = []
    current_batch = []
    current_chars = 0
    
    for msg in processed_messages:
        msg_len = len(msg.get('text', '')) + len(msg.get('ocr_text', '')) + 200
        if current_chars + msg_len > MAX_CHARS and current_batch:
            prompts.append(generate_ai_prompt(current_batch))
            current_batch = []
            current_chars = 0
        current_batch.append(msg)
        current_chars += msg_len
        
    if current_batch:
        prompts.append(generate_ai_prompt(current_batch))
    
    return jsonify({
        'prompts': prompts,
        'updated_messages': processed_messages 
    })

@app.route('/api/validate_picks', methods=['POST'])
def api_validate_picks():
    data = request.json
    picks = data.get('picks', [])
    original_messages = data.get('original_messages', [])
    msg_map = {m['id']: f"[CAPTION]: {m.get('text','')}\n[OCR]: {m.get('ocr_text','')}" for m in original_messages}
    
    failed_items = []
    for pick in picks:
        capper = pick.get('capper_name', 'Unknown')
        league = pick.get('league', 'Unknown')
        
        if capper == "Unknown" or league == "Unknown" or league == "Other":
            msg_id = pick.get('message_id')
            failed_items.append({
                "message_id": msg_id,
                "capper_name": capper,
                "league": league,
                "pick": pick.get('pick'),
                "original_text": msg_map.get(msg_id, "")[:1500] 
            })

    if not failed_items: return jsonify({'status': 'clean'})
    revision_prompt = generate_revision_prompt(failed_items)
    return jsonify({'status': 'needs_revision', 'failed_count': len(failed_items), 'revision_prompt': revision_prompt})

@app.route('/api/merge_revisions', methods=['POST'])
def api_merge_revisions():
    data = request.json
    original_picks = data.get('original_picks', [])
    revised_picks = data.get('revised_picks', [])
    
    revised_map = {}
    for r in revised_picks:
        mid = r.get('message_id')
        if mid:
            if mid not in revised_map: revised_map[mid] = []
            revised_map[mid].append(r)
            
    merged = []
    for orig in original_picks:
        mid = orig.get('message_id')
        if (orig.get('capper_name') == 'Unknown' or orig.get('league') == 'Unknown') and mid in revised_map:
            if len(revised_map[mid]) > 0:
                replacement = revised_map[mid].pop(0)
                if replacement.get('capper_name') != "Unknown": 
                    orig['capper_name'] = replacement.get('capper_name')
                if replacement.get('league') != "Unknown":
                    orig['league'] = replacement.get('league')
                if replacement.get('type'): orig['type'] = replacement.get('type')
                if replacement.get('pick'): orig['pick'] = replacement.get('pick')
        merged.append(orig)
    return jsonify({'merged_picks': merged})

@app.route('/api/generate_smart_fill', methods=['POST'])
def api_generate_smart_fill():
    data = request.json
    picks = data.get('picks', [])
    original_messages = data.get('original_messages', [])
    
    unknowns = []
    msg_map = {m['id']: m for m in original_messages}
    
    for p in picks:
        if not p.get('capper_name') or p.get('capper_name') == 'Unknown' or p.get('capper_name') == 'N/A':
            mid = p.get('message_id')
            m = msg_map.get(mid)
            if m:
                context_str = f"[CAPTION]: {m.get('text','')[:200]}\n[OCR]: {m.get('ocr_text','')[:200]}"
                unknowns.append({
                    "message_id": mid,
                    "pick": p.get('pick'),
                    "context": context_str
                })
            
    if not unknowns:
        return jsonify({'prompt': None})
        
    prompt = generate_smart_fill_prompt(unknowns)
    return jsonify({'prompt': prompt})

@app.route('/api/prefetch_scores', methods=['POST'])
def api_prefetch_scores():
    target_date = request.json.get('date')
    if not target_date: return jsonify({'status': 'skipped'})
    threading.Thread(target=background_score_fetch, args=(target_date,), daemon=True).start()
    return jsonify({'status': 'started'})

@app.route('/api/grade_picks', methods=['POST'])
def api_grade_picks():
    data = request.json
    picks = data.get('picks', [])
    target_date = data.get('date')
    if not picks: return jsonify([])
    
    picks = backfill_odds(picks)
    
    if target_date in _score_cache:
        scores = _score_cache[target_date]
    else:
        try:
            scores = fetch_scores_for_date(target_date)
            _score_cache[target_date] = scores
        except Exception as e:
            print(f"Score fetch failed: {e}")
            return jsonify({'error': 'Score fetch failed'}), 500
            
    graded_data = grade_picks(picks, scores)
    return jsonify(graded_data)

@app.route('/api/get_cappers', methods=['GET'])
def api_get_cappers():
    try:
        cappers = fetch_all_cappers() 
        return jsonify(cappers)
    except Exception as e: return jsonify([])

@app.route('/api/upload', methods=['POST'])
def api_upload():
    data = request.json
    picks = data.get('picks', [])
    target_date = data.get('date')
    if not picks: return jsonify({'success': False, 'error': 'No picks'})
    result = upload_picks(picks, target_date)
    return jsonify(result)

# --- APP LAUNCHER ---
def start_flask():
    # Run Flask in a thread, daemon=True means it dies when main thread dies
    app.run(port=5000, debug=False, use_reloader=False, threaded=True)

if __name__ == '__main__':
    cleanup_temp_images(TEMP_IMG_DIR)
    
    # 1. Start Flask in background
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()
    
    # 2. Start Native Window (Blocks until closed)
    # This creates a window without address bar/tabs
    webview.create_window("CapperSuite", "http://127.0.0.1:5000", width=1200, height=800)
    webview.start()
    
    # 3. When window closes, script ends here.
    print("Window closed. Exiting...")
    sys.exit(0)
