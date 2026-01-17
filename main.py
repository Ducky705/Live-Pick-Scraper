import sys
import os

# Load .env file FIRST before any other imports that might need env vars
from dotenv import load_dotenv

# For frozen apps, .env is bundled inside the exe - load from there
if getattr(sys, 'frozen', False):
    _env_path = os.path.join(sys._MEIPASS, '.env')
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
else:
    load_dotenv()
import json
import threading
import asyncio
import logging
import time
import platform
from datetime import datetime
from threading import Lock # ADDED: Thread safety
import webview # Requires: pip install pywebview
from flask import Flask, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor
from src.openrouter_client import openrouter_completion, openrouter_parallel_completion
from src.utils import clean_text_for_ai

# ADDED: Production server import
try:
    from waitress import serve
except ImportError:
    pass

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

# --- LAZY LOADING FOR FASTER STARTUP ---
# Heavy modules are loaded on first use instead of at startup
_tg_manager = None
_extract_text = None
_prompt_funcs = None
_utils_funcs = None
_score_fetcher = None
_grader = None
_capper_matcher = None
_supabase_funcs = None
_auto_processor = None

def get_tg_manager():
    global _tg_manager
    if _tg_manager is None:
        from src.telegram_client import tg_manager
        _tg_manager = tg_manager
        _tg_manager.set_progress_callback(set_progress)
    return _tg_manager

def get_extract_text():
    global _extract_text
    if _extract_text is None:
        from src.ocr_handler import extract_text
        _extract_text = extract_text
    return _extract_text

def get_prompt_funcs():
    global _prompt_funcs
    if _prompt_funcs is None:
        from src.prompt_builder import generate_ai_prompt, generate_revision_prompt, generate_smart_fill_prompt, generate_multimodal_prompt
        _prompt_funcs = (generate_ai_prompt, generate_revision_prompt, generate_smart_fill_prompt, generate_multimodal_prompt)
    return _prompt_funcs

def get_utils_funcs():
    global _utils_funcs
    if _utils_funcs is None:
        from src.utils import detect_common_watermark, filter_text, backfill_odds, is_ad_content, cleanup_temp_images
        _utils_funcs = (detect_common_watermark, filter_text, backfill_odds, is_ad_content, cleanup_temp_images)
    return _utils_funcs

def get_score_fetcher():
    global _score_fetcher
    if _score_fetcher is None:
        from src.score_fetcher import fetch_scores_for_date
        _score_fetcher = fetch_scores_for_date
    return _score_fetcher

def get_grader():
    global _grader
    if _grader is None:
        from src.grader import grade_picks
        _grader = grade_picks
    return _grader

def get_capper_matcher():
    global _capper_matcher
    if _capper_matcher is None:
        from src.capper_matcher import capper_matcher
        _capper_matcher = capper_matcher
    return _capper_matcher

def get_supabase_funcs():
    global _supabase_funcs
    if _supabase_funcs is None:
        try:
            from src.supabase_client import fetch_all_cappers, upload_picks, get_or_create_capper_id
            _supabase_funcs = (fetch_all_cappers, upload_picks, get_or_create_capper_id)
        except ImportError:
            def fetch_all_cappers(): return []
            def upload_picks(p, d): return {'success': False, 'error': 'Supabase module missing'}
            def get_or_create_capper_id(n): return None
            _supabase_funcs = (fetch_all_cappers, upload_picks, get_or_create_capper_id)
    return _supabase_funcs

def get_auto_processor():
    global _auto_processor
    if _auto_processor is None:
        from src.auto_processor import auto_select_messages, PostClassification
        _auto_processor = (auto_select_messages, PostClassification)
    return _auto_processor

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
_global_progress = {"percent": 0, "status": "IDLE"}

# --- GLOBAL STATE LOCKS ---
# Critical for production stability when threaded
progress_lock = Lock()
score_cache_lock = Lock()

def set_progress(p, s):
    with progress_lock:
        _global_progress['percent'] = p
        _global_progress['status'] = s

# Note: tg_manager callback is now set lazily in get_tg_manager()

def background_score_fetch(target_date):
    try:
        scores = get_score_fetcher()(target_date)
        with score_cache_lock:
            _score_cache[target_date] = scores
    except Exception as e:
        logging.error(f"[Background] Score fetch failed: {e}")

# --- FLASK ROUTES ---

@app.route('/api/progress')
def get_progress():
    return jsonify(_global_progress)

@app.route('/')
def index(): return render_template('index.html')

# Serve temp images from writable DATA_DIR (outside bundle for App Translocation)
@app.route('/static/temp_images/<path:filename>')
def serve_temp_image(filename):
    from flask import send_from_directory
    return send_from_directory(TEMP_IMG_DIR, filename)

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    try:
        is_authorized = run_async(get_tg_manager().connect_client())
        return jsonify({'authorized': is_authorized})
    except Exception as e: return jsonify({'authorized': False, 'error': str(e)})

@app.route('/api/send_code', methods=['POST'])
def send_code():
    phone = request.json.get('phone')
    try:
        run_async(get_tg_manager().send_code(phone))
        return jsonify({'status': 'success'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/verify_code', methods=['POST'])
def verify_code():
    code = request.json.get('code')
    password = request.json.get('password')
    try:
        result = run_async(get_tg_manager().sign_in(code, password))
        return jsonify({'status': result})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/get_channels', methods=['GET'])
def get_channels():
    try:
        channels = run_async(get_tg_manager().get_channels())
        return jsonify(channels)
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/fetch_messages', methods=['POST'])
def fetch_messages():
    # cleanup_temp_images(TEMP_IMG_DIR)
    data = request.json
    channel_ids = data.get('channel_id')
    target_date = data.get('date')
    auto_classify = data.get('auto_classify', True)  # NEW: Enable auto-classification by default
    
    if target_date:
        threading.Thread(target=background_score_fetch, args=(target_date,), daemon=True).start()

    try:
        msgs = run_async(get_tg_manager().fetch_messages(channel_ids, target_date))
        
        # NEW: Auto-classify messages to set selection state
        if auto_classify and msgs:
            try:
                auto_select_messages, _ = get_auto_processor()
                set_progress(95, "Classifying posts...")
                msgs = auto_select_messages(msgs, use_ai=False)  # Fast heuristic-only for now
                set_progress(100, "Complete")
            except Exception as e:
                logging.error(f"[AutoClassify] Error: {e}")
                # If classification fails, keep all selected (safe default)
        
        return jsonify(msgs)
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/classify_messages', methods=['POST'])
def api_classify_messages():
    """
    NEW API: Classify messages using AI vision for accurate filtering.
    Call this after fetch_messages for higher accuracy classification.
    """
    data = request.json
    messages = data.get('messages', [])
    use_ai = data.get('use_ai', True)
    
    if not messages:
        return jsonify({'messages': []})
    
    try:
        auto_select_messages, PostClassification = get_auto_processor()
        classified = auto_select_messages(messages, use_ai=use_ai)
        
        # Count classifications for stats
        stats = {}
        for msg in classified:
            cls = msg.get('classification', 'UNKNOWN')
            stats[cls] = stats.get(cls, 0) + 1
        
        return jsonify({
            'messages': classified,
            'stats': stats
        })
    except Exception as e:
        logging.error(f"[ClassifyMessages] Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect_watermark', methods=['POST'])
def api_detect_watermark():
    data = request.json
    messages = data.get('messages', [])
    ocr_texts = []
    for msg in messages:
        if msg.get('ocr_text'): ocr_texts.append(msg.get('ocr_text'))
        if msg.get('text'): ocr_texts.append(msg['text'])
    detect_common_watermark = get_utils_funcs()[0]
    detected = detect_common_watermark(ocr_texts)
    return jsonify({'watermark': detected})

@app.route('/api/generate_prompt', methods=['POST'])
def api_generate_prompt():
    data = request.json
    selected_messages = data.get('messages', [])
    watermark_filter = data.get('watermark', '').strip()
    
    processed_messages = []
    total = len(selected_messages)
    
    ocr_futures = {}
    
    # --- BATCH OCR PROCESSING ---
    all_ocr_tasks = [] # List of (message_index, image_path)
    
    for i, msg in enumerate(selected_messages):
        # Clean Text Pre-processing
        if msg.get('text'):
            msg['text'] = clean_text_for_ai(msg['text'])
        
        msg['ocr_texts'] = []
        
        images_to_process = []
        if msg.get('images') and isinstance(msg['images'], list):
            images_to_process = msg['images']
        elif msg.get('image'):
            images_to_process = [msg['image']]
            
        if msg.get('do_ocr') and images_to_process:
            for img_path in images_to_process:
                all_ocr_tasks.append((i, img_path))

    # Process ALL images in one call - extract_text_batch handles chunking internally
    if all_ocr_tasks:
        from src.ocr_handler import extract_text_batch
        
        set_progress(50, f"Starting OCR: {len(all_ocr_tasks)} images...")
        
        # Extract all paths
        all_paths = [t[1] for t in all_ocr_tasks]
        
        try:
            # Single call - internal parallelization handles chunks across models
            results = extract_text_batch(all_paths)
            
            # Assign results back to messages
            for t_idx, text_result in enumerate(results):
                original_msg_idx = all_ocr_tasks[t_idx][0]
                if text_result and not text_result.startswith("[Error"):
                    cleaned = clean_text_for_ai(text_result)
                    selected_messages[original_msg_idx]['ocr_texts'].append(cleaned)
                else:
                    logging.error(f"OCR Error for Msg {original_msg_idx}: {text_result}")
                    
        except Exception as e:
            logging.error(f"OCR Failed: {e}")
        
        set_progress(95, f"OCR Complete: {len(all_ocr_tasks)} images")


    set_progress(95, "Generating Prompts...")
    
    # Generate Master Prompt
    generate_ai_prompt = get_prompt_funcs()[0]
    master_prompt = generate_ai_prompt(selected_messages)
    
    # DEBUG: Log prompt stats
    msg_with_text = sum(1 for m in selected_messages if m.get('text') or m.get('ocr_texts'))
    msg_with_ocr = sum(1 for m in selected_messages if m.get('ocr_texts') and len(m.get('ocr_texts', [])) > 0)
    logging.info(f"[Prompt Gen] Total messages: {len(selected_messages)}")
    logging.info(f"[Prompt Gen] Messages with any text: {msg_with_text}")
    logging.info(f"[Prompt Gen] Messages with OCR text: {msg_with_ocr}")
    logging.info(f"[Prompt Gen] Prompt length: {len(master_prompt)} chars")
    
    # DEBUG: Show OCR quality stats
    empty_ocr_count = 0
    small_ocr_count = 0
    total_ocr_chars = 0
    sample_ocr = None
    for m in selected_messages:
        ocr_texts = m.get('ocr_texts', [])
        if not ocr_texts or all(not t or len(t.strip()) < 5 for t in ocr_texts):
            empty_ocr_count += 1
        else:
            for t in ocr_texts:
                total_ocr_chars += len(t) if t else 0
                if len(t.strip()) < 50:
                    small_ocr_count += 1
                if sample_ocr is None and t and len(t.strip()) > 20:
                    sample_ocr = t[:200]
    
    logging.info(f"[OCR Quality] Empty OCR results: {empty_ocr_count}/{len(selected_messages)}")
    logging.info(f"[OCR Quality] Small OCR results (<50 chars): {small_ocr_count}")
    logging.info(f"[OCR Quality] Total OCR chars: {total_ocr_chars}")
    if sample_ocr:
        logging.info(f"[OCR Quality] Sample OCR text: {sample_ocr[:150]}...")
    
    set_progress(100, "Complete")
    
    return jsonify({
        'master_prompt': master_prompt,
        'updated_messages': selected_messages 
    })

import difflib

def smart_merge_odds(picks):
    """
    Fuzzy matches picks to propagate odds from those that have them to those that don't.
    OPTIMIZED: Buckets by League/Type to avoid N^2 complexity.
    """
    from collections import defaultdict
    import difflib
    
    # 1. Separate sources (have odds) and targets (missing odds)
    # Bucket by (league, type) tuple
    sources_map = defaultdict(list)
    targets = []
    
    for p in picks:
        # Check if odds exist and are not empty/None
        has_odds = p.get('odds') is not None and str(p.get('odds')).strip() != ""
        
        # Normalize keys
        league = str(p.get('league', '')).lower().strip()
        p_type = str(p.get('type', '')).lower().strip()
        key = (league, p_type)
        
        if has_odds:
            sources_map[key].append(p)
        else:
            targets.append(p)
    
    if not targets or not sources_map:
        return picks
        
    for target in targets:
        league = str(target.get('league', '')).lower().strip()
        p_type = str(target.get('type', '')).lower().strip()
        key = (league, p_type)
        
        # Only compare against relevant sources
        relevant_sources = sources_map.get(key, [])
        if not relevant_sources:
            continue
            
        target_norm = target.get('pick', '').lower().strip()
        if not target_norm: continue
        
        best_match = None
        best_ratio = 0.0
        
        for source in relevant_sources:
            source_norm = source.get('pick', '').lower().strip()
            
            # Fast Substring Check (O(1) relative to string length)
            if target_norm in source_norm or source_norm in target_norm:
                ratio = 1.0
            else:
                # Expensive Fuzzy Match (only if substring fails)
                ratio = difflib.SequenceMatcher(None, target_norm, source_norm).ratio()
            
            # Update best match if this is better and passes threshold
            if ratio > 0.85 and ratio > best_ratio:
                best_ratio = ratio
                best_match = source
                if ratio == 1.0: break # Perfect match, stop searching
        
        # Apply the odds if we found a good match
        if best_match:
            target['odds'] = best_match['odds']
            
    return picks

@app.route('/api/ai_fill', methods=['POST'])
def api_ai_fill():
    data = request.json
    prompt = data.get('prompt')
    model = data.get('model', 'mistralai/devstral-2512:free') # Default to a free one
    use_parallel = data.get('use_parallel', True) # Default to True for speed
    
    if not prompt: 
        return jsonify({'error': 'No prompt provided'}), 400
        
    try:
        if use_parallel:
            logging.info(f"Calling OpenRouter PARALLEL execution")
            result_json_str = openrouter_parallel_completion(prompt)
        else:
            logging.info(f"Calling OpenRouter with model: {model}")
            result_json_str = openrouter_completion(prompt, model)
            
        # Parse it here to ensure it's valid JSON before sending to frontend? 
        # Or just send string. Frontend expects Object or Array.
        # openrouter_completion returns a string (the content).
        # Let's try to parse it to ensure it's JSON, but return the parsed obj.
        try:
            result_obj = json.loads(result_json_str)
            logging.info(f"[AI Fill] Raw AI Response Keys: {result_obj.keys() if isinstance(result_obj, dict) else 'Array'}")
            logging.info(f"[AI Fill] Raw Response Length: {len(result_json_str)} chars")
            logging.info(f"[AI Fill] Raw Response Preview: {result_json_str[:1000]}")
            # Unwrap if it's the new container format
            if isinstance(result_obj, dict) and 'picks' in result_obj:
                raw_picks = result_obj['picks']
                logging.info(f"[AI Fill] Number of raw picks from AI: {len(raw_picks)}")
                # Remap Short Keys to Long Keys
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
                
                # Apply Fuzzy Odds Matching
                result_obj = smart_merge_odds(remapped)
            
            # DEBUG: Track pick flow
            logging.info(f"[AI Fill] Final picks after processing: {len(result_obj)}")
            unique_ids = set(p.get('message_id', 0) for p in result_obj)
            logging.info(f"[AI Fill] Unique message IDs with picks: {len(unique_ids)}")
            
            return jsonify({'result': result_obj})
        except json.JSONDecodeError as e:
            logging.error(f"[AI Fill] JSON Decode Error: {e}")
            logging.error(f"[AI Fill] Raw Response: {result_json_str[:500]}")
            return jsonify({'error': 'AI returned invalid JSON', 'raw': result_json_str[:500]}), 500
            
    except Exception as e:
        logging.error(f"[AI Fill] Exception: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate_picks', methods=['POST'])
def api_validate_picks():
    data = request.json
    picks = data.get('picks', [])
    original_messages = data.get('original_messages', [])
    
    # AUTO-FIX: Try to deduce odds from siblings BEFORE validation
    picks = smart_merge_odds(picks)
    
    msg_map = {m['id']: f"[CAPTION]: {m.get('text','')}\n[OCR]: {m.get('ocr_text','')}" for m in original_messages}
    
    failed_items = []
    
    # Noise patterns that indicate a bad pick extraction
    noise_patterns = [
        # Sportsbook names
        'hard rock', 'draftkings', 'fanduel', 'betmgm', 'caesars', 'bet365', 'pointsbet',
        # Record labels / promo text
        'main play', 'potd', 'lock of the day', 'fire pick', 'max bet', 'bomb',
        '5-', '4-', '3-', '2-', '1-', '0-',  # Record patterns like "5-2 Run"
        # Generic descriptions (missing specifics)
        'player passing yards', 'player rushing yards', 'player receiving yards',
        'team totals', 'moneyline pick', 'spread pick'
    ]
    
    import re
    # Pattern: Valid pick should have a number (spread/total) or "ML"
    has_number_or_ml = re.compile(r'(-?\d+\.?\d*|ML|ml|Over|Under|over|under)', re.IGNORECASE)
    
    initial_count = len(picks)
    logging.info(f"[Validate] Starting validation with {initial_count} picks")
    
    for pick in picks:
        capper = pick.get('capper_name', 'Unknown')
        league = pick.get('league', 'Unknown')
        pick_value = pick.get('pick', '')
        pick_lower = pick_value.lower() if pick_value else ''
        
        # Check for any failure condition
        # 1. Critical Missing Info
        is_unknown_capper = capper in ["Unknown", "N/A", None, ""]
        is_unknown_league = league in ["Unknown", "Other", None, ""]
        is_invalid_pick = not pick_value or pick_value == "Unknown"
        
        # 2. Strict Parlay Logic: If '/' is present, Type MUST be 'Parlay'
        # If not, it's a "Failed" extraction that needs AI review
        has_slash = '/' in pick_value
        is_parlay = pick.get('type') == 'Parlay'
        
        # If it looks like a parlay but isn't marked as one -> FAIL
        potential_parlay_fail = has_slash and not is_parlay
        
        is_failed = (
            is_unknown_capper or 
            is_unknown_league or 
            is_invalid_pick or
            potential_parlay_fail
        )
        
            # Check for noise patterns in pick
        if not is_failed and pick_value:
            for noise in noise_patterns:
                if noise in pick_lower:
                    is_failed = True
                    break
            
            # Check if pick lacks proper formatting (no number or ML)
            if not is_failed and not has_number_or_ml.search(pick_value):
                is_failed = True

        # DON'T force revision for missing chem/tags - these are optional enhancements
        # Only fail if critical data is missing
        
        if is_failed:
            msg_id = pick.get('message_id')
            failed_items.append({
                "message_id": msg_id,
                "capper_name": capper,
                "league": league,
                "pick": pick_value,
                "original_text": msg_map.get(msg_id, "")[:1500] 
            })
    
    logging.info(f"[Validate] Passed: {initial_count - len(failed_items)}, Failed: {len(failed_items)}")

    if not failed_items:
        return jsonify({'status': 'clean'})
    
    # Collect Reference Picks (Good picks with odds)
    reference_picks = [p for p in picks if p not in failed_items and p.get('odds')]
    
    generate_revision_prompt = get_prompt_funcs()[1]
    revision_prompt = generate_revision_prompt(failed_items, reference_picks=reference_picks)
    return jsonify({
        'status': 'needs_revision', 
        'failed_count': len(failed_items), 
        'failed_items': failed_items,  # Return list for frontend
        'revision_prompt': revision_prompt
    })

@app.route('/api/merge_revisions', methods=['POST'])
def api_merge_revisions():
    data = request.json
    original_picks = data.get('original_picks', [])
    revised_picks = data.get('revised_picks', [])
    
    revised_map = {}
    for r in revised_picks:
        # Support both 'message_id' and 'id' keys (AI uses 'id')
        mid = r.get('message_id') or r.get('id')
        if mid:
            if mid not in revised_map: revised_map[mid] = []
            revised_map[mid].append(r)
            
    merged = []
    for orig in original_picks:
        mid = orig.get('message_id')
        # Always merge if a revision exists (trusting the revision process)
        if mid in revised_map:
            if len(revised_map[mid]) > 0:
                replacement = revised_map[mid].pop(0)
                
                # Update fields if they exist in replacement (even if null/empty, to allow correction)
                # Update fields with support for minified keys
                if 'capper_name' in replacement: orig['capper_name'] = replacement['capper_name']
                elif 'cn' in replacement: orig['capper_name'] = replacement['cn']
                
                if 'league' in replacement: orig['league'] = replacement['league']
                elif 'lg' in replacement: orig['league'] = replacement['lg']
                
                if 'type' in replacement: orig['type'] = replacement['type']
                elif 'ty' in replacement: orig['type'] = replacement['ty']
                
                if 'pick' in replacement: orig['pick'] = replacement['pick']
                elif 'p' in replacement: orig['pick'] = replacement['p']
                
                # Phase 2: Units, Tags, Warnings
                if 'u' in replacement: orig['units'] = replacement['u']
                if 'tags' in replacement: orig['tags'] = replacement['tags']
                if 'warning' in replacement: orig['warning'] = replacement['warning']
                if 'is_update' in replacement: orig['is_update'] = replacement['is_update']
                
                # Phase 3: Granular Props ("chem" object)
                chem = replacement.get('chem')
                if chem:
                    orig['subject'] = chem.get('sub')
                    orig['market'] = chem.get('mkt')
                    orig['line'] = chem.get('ln')
                    orig['prop_side'] = chem.get('sd')
                    orig['deduction_source'] = chem.get('src', 'Explicit')
                
                # STORE ULTIMATE REASONING METADATA
                reason = replacement.get('reason', '')
                conf = replacement.get('conf')
                
                if reason or conf is not None:
                     # Format: "Conf: 95% | Reason: Detected slash..."
                     meta_str = f"Conf: {conf}% | {reason}" if conf is not None else reason
                     orig['ai_reasoning'] = meta_str
                     
        merged.append(orig)
    
    # AUTO-FIX: Re-run deductions on the full merged set
    merged = smart_merge_odds(merged)
        
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
        
    generate_smart_fill_prompt = get_prompt_funcs()[2]
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
    
    # 1. Fetch Scores (Smart Lazy Loading)
    if target_date in _score_cache:
        current_scores = _score_cache[target_date]
    else:
        current_scores = []
        
    # Analyze requested leagues to avoid over-fetching
    requested_leagues = set()
    for p in picks:
        if p.get('league'):
            requested_leagues.add(str(p.get('league')).lower())
            
    # Always include 'nba', 'nfl' as defaults if list is small? No, strict lazy load.
    # If list is empty (parsing failed), we might fetch nothing.
    # Safe default: if empty, fetch major US sports.
    if not requested_leagues:
        requested_leagues = {'nba', 'nfl', 'ncaab', 'ncaaf', 'mlb', 'nhl'}
        
    try:
        # Pass existing cache so we only fetch missing leagues
        scores = get_score_fetcher()(target_date, requested_leagues=list(requested_leagues), current_scores=current_scores)
        
        # Update cache lock
        with score_cache_lock:
            _score_cache[target_date] = scores
            
    except Exception as e:
        print(f"Score fetch failed: {e}")
        return jsonify({'error': 'Score fetch failed'}), 500
            
    # 2. Traditional Grading (Regex/Fuzzy)
    graded_data = get_grader()(picks, scores)

    # 3. AI Fallback (Smart & Efficient)
    # Filter for items that failed grading (Pending/Unknown) BUT have potential game data or are just tricky
    pending_items = [p for p in graded_data if p.get('result') in ["Pending/Unknown", "Error"]]
    
    if pending_items:
        # We only send specific data to save tokens
        # We need the pick description and the available scores for that sport
        logging.info(f"AI Grading Fallback triggered for {len(pending_items)} items")
        
        # Structure the prompt efficiently
        # We'll group by Sport to provide relevant context
        
        ai_payload = []
        for p in pending_items:
            # Try to narrow down scores to relevant sport/league to reduce context
            sport = str(p.get('league', '')).lower()
            relevant_scores = [s for s in scores if s.get('league', '').lower() in sport or sport in s.get('league', '').lower()]
            
            # If no relevant scores found, maybe send all? Or skip?
            # Let's send a simplified list of scores if possible, or just the whole batch if small.
            # For efficiency, let's just send the pick text and ask AI to match against PROVIDED simplified score list.
            
            ai_payload.append({
                "id": p.get('message_id'),
                "desc": p.get('pick'),
                "sport": p.get('league'),
                "candidates": [f"{s['team1']} {s['score1']} - {s['score2']} {s['team2']}" for s in relevant_scores[:20]] # Limit candidates
            })

        if ai_payload:
            try:
                # Construct Minimal Prompt
                prompt = f"""
### GRADING TASK
Determine WIN/LOSS/PUSH for these picks based on the scores.
Return JSON Object: {{ "grades": [ {{ "id": 123, "result": "Win/Loss/Push", "score": "Lakers 110-100 Celtics" }} ] }}
If score not found, result="Unknown".

### SCORES AVAILABLE
{json.dumps([s['team1'] + ' ' + str(s['score1']) + '-' + str(s['score2']) + ' ' + s['team2'] for s in scores[:50]])}

### PICKS TO GRADE
{json.dumps([{ 'id': x['id'], 'pick': x['desc'], 'sport': x['sport'] } for x in ai_payload])}
"""
                # Call AI with SHORT timeout (30s) and only 1 cycle to prevent hanging
                # Grading is non-critical, so we fail fast instead of retrying forever
                logging.info(f"[AI Grading] Calling AI for {len(ai_payload)} pending items...")
                ai_resp_str = openrouter_completion(prompt, "google/gemini-2.0-flash-exp:free", timeout=30, max_cycles=1)
                ai_resp = json.loads(ai_resp_str)
                
                # Merge AI Grades
                if 'grades' in ai_resp:
                    grade_map = {g['id']: g for g in ai_resp['grades']}
                    for p in graded_data:
                        if p.get('message_id') in grade_map:
                            ai_g = grade_map[p.get('message_id')]
                            if ai_g.get('result') and ai_g.get('result') != "Unknown":
                                p['result'] = ai_g['result']
                                p['score_summary'] = ai_g.get('score', 'AI Graded')
                    logging.info(f"[AI Grading] Successfully graded {len(grade_map)} picks")
                                
            except Exception as e:
                logging.error(f"AI Grading Failed (non-critical): {e}")

    return jsonify(graded_data)

@app.route('/api/get_cappers', methods=['GET'])
def api_get_cappers():
    try:
        fetch_all_cappers = get_supabase_funcs()[0]
        cappers = fetch_all_cappers() 
        return jsonify(cappers)
    except Exception as e: return jsonify([])

@app.route('/api/export_csv', methods=['POST'])
def api_export_csv():
    """Server-side CSV export - saves directly to Downloads folder for pywebview compatibility"""
    import csv
    from pathlib import Path
    
    data = request.json
    picks = data.get('picks', [])
    
    if not picks:
        return jsonify({'success': False, 'error': 'No picks to export'})
    
    try:
        # Save to Downloads folder
        downloads = Path.home() / "Downloads"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"picks_export_{timestamp}.csv"
        filepath = downloads / filename
        
        logging.info(f"[Export] Writing {len(picks)} picks to {filename}")
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(['ID', 'Capper', 'Sport', 'Type', 'Pick', 'Odds', 'Units', 'Date', 'Result'])
            
            # Data rows
            blacklist = ['80k main play', 'vip whale', 'lock of the', 'max bet', 'hard rock', 'draftkings', 'fanduel']
            
            filtered_count = 0
            for pick in picks:
                # Final Safety Check: If pick matches noise exactly or contains noise, scrub it
                p_val = pick.get('pick', '') or ''
                p_lower = p_val.lower()
                
                is_noise = False
                for b in blacklist:
                    if b in p_lower:
                        is_noise = True
                        break
                
                final_pick = "Unknown (Manual Review)" if is_noise else p_val
                if is_noise:
                    filtered_count += 1

                writer.writerow([
                    pick.get('message_id', ''),
                    pick.get('capper_name', ''),
                    pick.get('league', ''),
                    pick.get('type', 'BET'),
                    final_pick,
                    pick.get('odds', ''),
                    pick.get('units', ''),
                    pick.get('date', ''),
                    pick.get('result', '')
                ])
        
        logging.info(f"[Export] Wrote {len(picks) - filtered_count} picks (filtered {filtered_count} as noise)")
        
        return jsonify({'success': True, 'path': str(filepath), 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    data = request.json
    picks = data.get('picks', [])
    target_date = data.get('date')
    if not picks: return jsonify({'success': False, 'error': 'No picks'})
    upload_picks = get_supabase_funcs()[1]
    result = upload_picks(picks, target_date)
    return jsonify(result)


@app.route('/api/prepare_manual_export', methods=['POST'])
def api_prepare_manual_export():
    from pathlib import Path
    from PIL import Image, ImageDraw, ImageFont
    
    data = request.json
    selected_messages = data.get('messages', [])
    
    if not selected_messages:
        return jsonify({'success': False, 'error': 'No messages selected'})
        
    try:
        # 1. Create PDF path in Downloads
        downloads = Path.home() / "Downloads"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"CapperSuite_Export_{timestamp}.pdf"
        pdf_path = downloads / pdf_filename
        
        # Helper: Add text overlay to image
        def add_caption_overlay(img, caption_text, msg_id):
            """Overlays caption text at top of image for AI context matching."""
            try:
                # Ensure RGB mode
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create header for caption
                header_height = 80 if len(caption_text) < 100 else 120
                new_height = img.height + header_height
                
                # New image with header space
                new_img = Image.new('RGB', (img.width, new_height), color=(30, 30, 30))
                new_img.paste(img, (0, header_height))
                
                # Draw caption text
                draw = ImageDraw.Draw(new_img)
                
                # Try to use a readable font, fallback to default
                try:
                    font = ImageFont.truetype("arial.ttf", 14)
                except:
                    font = ImageFont.load_default()
                
                # Truncate caption if too long
                max_chars = 200
                display_text = caption_text[:max_chars] + "..." if len(caption_text) > max_chars else caption_text
                display_text = f"[MSG {msg_id}] {display_text}"
                
                # Wrap text
                chars_per_line = max(50, img.width // 7)
                lines = []
                for i in range(0, len(display_text), chars_per_line):
                    lines.append(display_text[i:i+chars_per_line])
                
                # Draw each line
                y_offset = 10
                for line in lines[:5]:  # Max 5 lines
                    draw.text((10, y_offset), line, fill=(255, 255, 255), font=font)
                    y_offset += 18
                
                return new_img
            except Exception as e:
                logging.error(f"Caption overlay failed: {e}")
                return img  # Return original if overlay fails
        
        # 2. Collect and process all images
        pdf_pages = []
        
        for msg in selected_messages:
            mid = msg.get('id')
            caption = msg.get('text', '') or ''
            
            # Get image paths (web paths like /static/temp_images/...)
            images = []
            if msg.get('images') and isinstance(msg['images'], list):
                images = msg['images']
            elif msg.get('image'):
                images = [msg['image']]
            
            for web_path in images:
                # Convert web path to absolute path
                if web_path.startswith('/static/temp_images/'):
                    filename = web_path.split('/')[-1]
                    src_path = Path(TEMP_IMG_DIR) / filename
                else:
                    src_path = Path(web_path)
                    if not src_path.is_absolute():
                        src_path = Path(BASE_DIR) / web_path.lstrip('/')
                
                if src_path.exists():
                    try:
                        img = Image.open(src_path)
                        
                        # Ensure RGB for PDF
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Resize if too large (max 1200px width for PDF)
                        max_width = 1200
                        if img.width > max_width:
                            ratio = max_width / img.width
                            new_size = (int(img.width * ratio), int(img.height * ratio))
                            img = img.resize(new_size, Image.Resampling.LANCZOS)
                        
                        # Add caption overlay
                        img_with_caption = add_caption_overlay(img, caption, mid)
                        pdf_pages.append(img_with_caption)
                        
                    except Exception as e:
                        logging.error(f"Error processing image {src_path}: {e}")
                else:
                    logging.warning(f"Image not found: {src_path}")
        
        if not pdf_pages:
            return jsonify({'success': False, 'error': 'No valid images found'})
        
        # 3. Save as single PDF
        pdf_pages[0].save(
            str(pdf_path),
            "PDF",
            save_all=True,
            append_images=pdf_pages[1:] if len(pdf_pages) > 1 else [],
            resolution=100.0
        )
        
        pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        image_count = len(pdf_pages)

        # 4. Generate Prompt with Formatting Guide
        prompt = f"""You are an expert sports betting data parser. I have uploaded a PDF containing betting pick images.

**IMPORTANT**: Each page has a HEADER showing the Message ID and Caption/Context text at the top (dark bar with white text).
Use this embedded context along with the image content to extract picks.

---
## FORMATTING RULES

### Leagues
Use: `NFL`, `NCAAF`, `NBA`, `NCAAB`, `WNBA`, `MLB`, `NHL`, `EPL`, `MLS`, `UCL`, `UFC`, `PFL`, `TENNIS`, `PGA`, `F1`, `Other`

### Types
Use: `Moneyline`, `Spread`, `Total`, `Player Prop`, `Team Prop`, `Game Prop`, `Period`, `Parlay`, `Teaser`, `Future`, `Unknown`

### Pick Value Formats (by Type)
- **Moneyline**: `Team Name ML` → `Los Angeles Lakers ML`
- **Spread**: `Team Name Spread` → `Green Bay Packers -7.5`
- **Total**: `Team A vs Team B Over/Under Number` → `Lakers vs Celtics Over 215.5`
- **Player Prop**: `Player Name: Stat Over/Under Value` → `LeBron James: Pts Over 25.5`
  - Stats: `Pts`, `Reb`, `Ast`, `PRA`, `PassYds`, `RushYds`, `RecYds`, `PassTD`, `Rec`, `K`, `H`, `HR`, `RBI`, `SOG`, `G`, `A`
- **Team Prop**: `Team Name: Stat Over/Under Value` → `Cowboys: Total Points Over 27.5`
- **Period**: `Identifier Format` → `1H NYK vs BOS Total Over 110.5`, `1Q Thunder -2`
  - Identifiers: `1H`, `2H`, `1Q`, `2Q`, `3Q`, `4Q`, `P1`, `P2`, `P3`, `F5`, `60 min`
- **Parlay**: `(League) Leg / (League) Leg` → `(NFL) Cowboys -10.5 / (NBA) Lakers ML`
- **Teaser**: `(Teaser Xpt League) Leg / ...` → `(Teaser 6pt NFL) Chiefs -2.5 / (Teaser 6pt NFL) Eagles +8.5`
- **Future**: `Event: Selection` → `Super Bowl LIX Winner: Kansas City Chiefs`

### Key Rules
- Odds (-110, +150) go ONLY in the `od` field, NOT in pick value
- Omit trailing `.0` (use `48` not `48.0`, but keep `48.5`)
- Capper name is the person/brand, NOT watermarks like "@cappersfree"

---
## OUTPUT FORMAT
Return a JSON object:
{{
  "picks": [
    {{ "id": <message_id>, "cn": "<capper_name>", "lg": "<league>", "ty": "<type>", "p": "<pick_value>", "od": <odds_or_null>, "u": 1.0 }}
  ]
}}

Extract ALL picks from ALL pages. Return ONLY valid JSON."""
            
        return jsonify({
            'success': True, 
            'path': str(pdf_path), 
            'prompt': prompt,
            'image_count': image_count,
            'pdf_size_mb': round(pdf_size_mb, 1)
        })
        
    except Exception as e:
        logging.error(f"Manual Export Failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auto_review', methods=['POST'])
def api_auto_review():
    data = request.json
    picks = data.get('picks', [])
    
    if not picks:
        return jsonify({'changes': []})

    # 1. Identify items needing review
    # Criteria: Unknown/N/A in critical fields, or generic types
    to_review = []
    
    # Get all known cappers for context
    fetch_all_cappers = get_supabase_funcs()[0]
    known_cappers = [c['name'] for c in fetch_all_cappers()]
    
    for p in picks:
        reasons = []
        if p.get('capper_name') in ['Unknown', 'N/A', '', None]: reasons.append('Missing Capper')
        if p.get('league') in ['Unknown', 'Other', '', None]: reasons.append('Missing Sport')
        if p.get('type') in ['Unknown', 'Other', '', None]: reasons.append('Missing Type')
        
        # Also check for likely mistakes or noise in pick name if we want, but let's stick to metadata first
        
        if reasons:
            to_review.append({
                'item': p,
                'reasons': reasons
            })
            
    if not to_review:
        return jsonify({'changes': []})
        
    # 2. Build Prompt
    # We'll batch them to save time, but not too many at once. Let's do all in one go if < 50, else batch?
    # For now, simplistic approach: one big prompt.
    
    review_context = []
    for entry in to_review[:50]: # Limit to 50 for safety/speed
        p = entry['item']
        # We need original text context. Ideally the frontend passes it, or we have it in the pick object?
        # The pick object usually comes from the frontend state which might NOT have the full text if it's the final table.
        # But wait, looking at swiss_app.js: state.processedData has the full object usually. 
        # API expects frontend to send enough data.
        # Let's assume frontend sends { ...pick, original_text: "..." } or we just rely on what's there.
        # If 'original_text' is missing, AI will struggle.
        # CHECK: Does frontend export have original text?
        # Answer: The `processedData` in swiss_app.js usually has it. We will ensure frontend sends it.
        
        review_context.append({
            "id": p.get('message_id'),
            "current": {
                "capper": p.get('capper_name'),
                "sport": p.get('league'),
                "type": p.get('type'),
                "pick": p.get('pick')
            },
            "context": p.get('original_text', '')[:500] # Truncate for token limits
        })
        
    prompt = f"""
### ANALYTICAL REVIEW TASK
You are a Sports Betting Data Analyst.
Review the following extracted picks. Some have missing or incorrect metadata (Capper, Sport, Type).
Use the Context (original message) to determine the correct values.

### KNOWN CAPPERS (Use these if applicable, otherwise infer new name):
{json.dumps(known_cappers[:100])} ... (and others)

### INSTRUCTIONS
1. Fix "Unknown" or "N/A" values using the Context.
2. "Sport" should be standard (NBA, NFL, NHL, MLB, NCAA, SOCCER, TENNIS, UFC, etc).
3. "Type" should be one of: SPREAD, TOTAL, MONEYLINE, PROP, PARLAY, TEASER.
4. "Capper" is the person/group giving the pick. 
5. Return ONLY changes. If a value is currently correct, do not return it.
6. **IMPORTANT**: If a pick is GARBAGE, NOISE, an AD, or NOT A REAL BET (e.g., promotional text, website ads, crypto talk, non-sports content), recommend DELETION by setting field="DELETE" and new="true".

### INPUT DATA
{json.dumps(review_context)}

### OUTPUT FORMAT (JSON)
{{
  "changes": [
    {{ "id": "msg_1", "field": "capper_name", "old": "Unknown", "new": "CorrectName", "reason": "Found in signature" }},
    {{ "id": "msg_1", "field": "league", "old": "Unknown", "new": "NBA", "reason": "Lakers vs Celtics mentioned" }},
    {{ "id": "msg_2", "field": "DELETE", "old": "-", "new": "true", "reason": "This is an advertisement, not a pick" }}
  ]
}}
"""
    
    try:
        # Call AI
        # Using the primary reasoning model (same as parser)
        model = "google/gemini-2.0-flash-exp:free"
        response_str = openrouter_completion(prompt, model)
        
        # Parse
        # Build context map for enriching response
        # Handle duplicate IDs (multiple picks per msg) by aggregating selections
        context_map = {}
        selection_map = {}
        
        for item in review_context:
            mid = item["id"]
            ctxt = item.get("context", "")
            pick_val = item["current"].get("pick", "") or "No Pick"
            
            # Context is same for the ID
            context_map[mid] = ctxt
            
            # Selection: Append if exists
            if mid in selection_map:
                if pick_val not in selection_map[mid]:
                    selection_map[mid] += f"; {pick_val}"
            else:
                selection_map[mid] = pick_val
        
        def enrich_changes(changes):
            """Add original context and selection to each change for display."""
            for c in changes:
                mid = c.get('id')
                c['context'] = context_map.get(mid, '')[:300]
                c['selection'] = selection_map.get(mid, 'Unknown')
            return changes
        
        try:
            resp_json = json.loads(response_str)
            changes = enrich_changes(resp_json.get('changes', []))
            return jsonify({'changes': changes})
        except json.JSONDecodeError:
            # Try to find JSON block
            import re
            match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if match:
                try:
                    resp_json = json.loads(match.group(0))
                    changes = enrich_changes(resp_json.get('changes', []))
                    return jsonify({'changes': changes})
                except:
                    pass
            return jsonify({'changes': [], 'error': 'AI Parse Fail', 'raw': response_str})
            
    except Exception as e:
        return jsonify({'changes': [], 'error': str(e)})

# --- CAPPER RECONCILIATION ---
@app.route('/api/match_cappers', methods=['POST'])
def api_match_cappers():
    try:
        data = request.json
        capper_names = data.get('names', [])
        # Bulk match
        matches = get_capper_matcher().match_names_bulk(capper_names)
        return jsonify({'matches': matches})
    except Exception as e:
        logging.error(f"Error matching cappers: {e}")
        return jsonify({'matches': {}})

@app.route('/api/create_capper', methods=['POST'])
def api_create_capper():
    try:
        data = request.json
        name = data.get('name')
        if not name: return jsonify({'success': False})
        
        # This function creates if not exists and returns ID
        get_or_create_capper_id = get_supabase_funcs()[2]
        new_id = get_or_create_capper_id(name)
        
        if new_id:
            # Force cache refresh so next match finds it immediately?
            # Or just trust the return.
            # Ideally we return the structured object expected by frontend
            return jsonify({
                'success': True,
                'capper': {
                    'name': name.title(), # Title case for display
                    'id': new_id,
                    'is_new': False 
                }
            })
        else:
            return jsonify({'success': False})
    except Exception as e:
        logging.error(f"Error creating capper: {e}")
        return jsonify({'success': False, 'error': str(e)})

# --- AUTO-UPDATE API ---
from src.auto_updater import check_for_updates, download_update, apply_update, get_all_releases
from config import APP_VERSION

@app.route('/api/version', methods=['GET'])
def api_get_version():
    """Return current app version."""
    return jsonify({'version': APP_VERSION})

@app.route('/api/check_update', methods=['GET'])
def api_check_update():
    """Check if an update is available."""
    try:
        result = check_for_updates()
        return jsonify(result)
    except Exception as e:
        logging.error(f"Update check failed: {e}")
        return jsonify({'update_available': False, 'error': str(e)})

@app.route('/api/download_update', methods=['POST'])
def api_download_update():
    """Download and apply the update."""
    try:
        # First check for update to get download URL
        check_result = check_for_updates()
        logging.info(f"[Update] Check result: {check_result}")
        
        if not check_result.get('update_available'):
            return jsonify({'success': False, 'error': 'No update available'})
        
        download_url = check_result.get('download_url')
        if not download_url:
            return jsonify({'success': False, 'error': 'No download URL for this platform'})
        
        logging.info(f"[Update] Download URL: {download_url}")
        
        # Download the update
        set_progress(10, "Downloading update...")
        update_file = download_update(download_url, progress_callback=lambda p, s: set_progress(10 + int(p * 0.7), s))
        
        if not update_file:
            logging.error("[Update] Download returned None - check auto_updater logs")
            return jsonify({'success': False, 'error': 'Download failed - check logs for details'})
        
        logging.info(f"[Update] Downloaded to: {update_file}")
        set_progress(90, "Applying update...")
        
        # Apply the update (this will restart the app)
        success = apply_update(update_file, restart=True)
        
        if success:
            return jsonify({'success': True, 'message': 'Update applied, restarting...'})
        else:
            logging.error("[Update] apply_update returned False")
            return jsonify({'success': False, 'error': 'Failed to apply update'})
            
    except Exception as e:
        logging.error(f"Update download/apply failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/releases', methods=['GET'])
def api_get_releases():
    """Get changelog/release history."""
    try:
        releases = get_all_releases()
        return jsonify({'releases': releases})
    except Exception as e:
        return jsonify({'releases': [], 'error': str(e)})

# --- APP LAUNCHER ---
def start_server():
    """
    Uses Waitress for production-grade stability instead of Flask's dev server.
    This handles multiple requests better and prevents random crashes.
    """
    try:
        from waitress import serve
        logger = logging.getLogger('waitress')
        logger.setLevel(logging.INFO)
        # 4 threads is a sweet spot for this specific workload
        serve(app, host='127.0.0.1', port=5000, threads=4, _quiet=True) 
    except ImportError:
        # Fallback if waitress isn't installed
        app.run(port=5000, debug=False, use_reloader=False, threaded=True)

if __name__ == '__main__':
    # cleanup_temp_images(TEMP_IMG_DIR) 
    
    # 1. Start Server in background
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    
    # 2. Start Native Window
    # Performance Polish: Enable GPU acceleration hints if supported by webview
    webview.create_window(
        "CapperSuite", 
        "http://127.0.0.1:5000", 
        width=1280, # Increased default width for modern displays
        height=850,
        min_size=(1024, 768),
        background_color='#FFFFFF'
    )
    
    # Set icon path (Prefer .icns on Mac, .ico on Windows if available)
    icon_path = os.path.join(BASE_DIR, 'static', 'logo.icns')
    if not os.path.exists(icon_path):
         icon_path = os.path.join(BASE_DIR, 'static', 'logo.ico')

    webview.start(icon=icon_path, debug=False) # Debug False for production
    sys.exit(0)
