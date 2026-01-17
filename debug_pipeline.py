#!/usr/bin/env python3
"""
Debug Pipeline Tool
====================
Isolated, cacheable debugging for the Telegram Scraper pipeline.

Usage:
    python debug_pipeline.py [stage] [options]

Stages:
    fetch   - Download messages from Telegram (caches to cache/messages.json)
    ocr     - Run OCR on images (caches to cache/ocr_results.json)
    parse   - Run AI parsing on OCR text (caches to cache/ai_response.json)
    grade   - Grade picks against scores (caches to cache/graded_picks.json)
    report  - Show diagnostics from cached data (no API calls)
    full    - Run all stages sequentially

Options:
    --fresh         Ignore cache for this stage, re-run from scratch
    --sample N      Process only first N messages (default: 10)
    --sample quick  Process 10 messages
    --sample medium Process 30 messages  
    --sample full   Process all messages
    --verbose       Show detailed output for each item
    --date YYYY-MM-DD  Target date (default: yesterday)

Examples:
    python debug_pipeline.py fetch              # Fetch and cache messages
    python debug_pipeline.py ocr --sample 5     # OCR first 5 images
    python debug_pipeline.py ocr --fresh        # Re-run OCR ignoring cache
    python debug_pipeline.py parse              # Parse using cached OCR
    python debug_pipeline.py report             # Show full diagnostics
    python debug_pipeline.py full --sample 10   # Run everything on 10 msgs
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# --- CONFIGURATION ---
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Hard-coded channel from last run (from logs: -1001900292133)
DEBUG_CHANNEL_ID = -1001900292133
DEBUG_CHANNEL_NAME = "CappersFree"

# Cache file paths
CACHE_FILES = {
    "messages": CACHE_DIR / "messages.json",
    "ocr": CACHE_DIR / "ocr_results.json", 
    "parse": CACHE_DIR / "ai_response.json",
    "grade": CACHE_DIR / "graded_picks.json",
    "diagnostics": CACHE_DIR / "diagnostics.json",
}

# Sample sizes
SAMPLE_SIZES = {
    "quick": 10,
    "medium": 30,
    "full": None,  # All
}


class Colors:
    """ANSI color codes for terminal output"""
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def log(msg: str, color: str = Colors.WHITE):
    """Print colored log message"""
    print(f"{color}{msg}{Colors.RESET}")


def log_header(title: str):
    """Print section header"""
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")


def log_subheader(title: str):
    """Print subsection header"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}--- {title} ---{Colors.RESET}")


def log_success(msg: str):
    log(f"[OK] {msg}", Colors.GREEN)


def log_error(msg: str):
    log(f"[ERROR] {msg}", Colors.RED)


def log_warning(msg: str):
    log(f"[WARN] {msg}", Colors.YELLOW)


def log_info(msg: str):
    log(f"[INFO] {msg}", Colors.BLUE)


# =============================================================================
# FORMAT VALIDATION (per pick_format.md)
# =============================================================================
VALID_LEAGUES = {"NFL", "NCAAF", "NBA", "NCAAB", "WNBA", "MLB", "NHL", "EPL", "MLS", "UCL", "UFC", "PFL", "TENNIS", "PGA", "F1", "Other"}
VALID_TYPES = {"Moneyline", "Spread", "Total", "Player Prop", "Team Prop", "Game Prop", "Period", "Parlay", "Teaser", "Future", "Unknown"}

import re as regex

def validate_pick_format(picks: list) -> dict:
    """
    Validate picks against pick_format.md specification.
    Returns detailed issue report.
    """
    issues = {
        "invalid_league": [],
        "invalid_type": [],
        "format_errors": [],
        "period_misclassified": [],
        "moneyline_missing_ml": [],
        "spread_bad_format": [],
        "total_bad_format": [],
        "summary": {}
    }
    
    for i, pick in enumerate(picks):
        pick_id = pick.get("id", i)
        lg = pick.get("lg", "")
        ty = pick.get("ty", "")
        p = pick.get("p", "")
        od = pick.get("od")
        
        # 1. Validate league
        if lg not in VALID_LEAGUES:
            issues["invalid_league"].append({
                "id": pick_id, "got": lg, "pick": p
            })
        
        # 2. Validate type
        if ty not in VALID_TYPES:
            issues["invalid_type"].append({
                "id": pick_id, "got": ty, "pick": p
            })
        
        # 3. Check for Period picks misclassified as Spread
        period_indicators = ["1H", "2H", "1Q", "2Q", "3Q", "4Q", "First Half", "Second Half", "P1", "P2", "P3", "F5", "F3"]
        if ty == "Spread" and any(ind.lower() in p.lower() for ind in period_indicators):
            issues["period_misclassified"].append({
                "id": pick_id, "pick": p, "should_be": "Period"
            })
        
        # 4. Moneyline format: Should end with "ML"
        if ty == "Moneyline" and not p.strip().upper().endswith("ML"):
            issues["moneyline_missing_ml"].append({
                "id": pick_id, "pick": p, "expected": f"{p} ML"
            })
        
        # 5. Spread format: "Team Name +/-X.X" (but tennis uses "sets" or "games" or just number)
        if ty == "Spread":
            lg = pick.get("lg", "")
            spread_pattern = r'^.+\s+[+-]?\d+\.?\d*$'
            tennis_pattern = r'.+\s+[+-]?\d+\.?\d*(\s+(sets?|games?))?$'
            
            # Tennis has different format - allow with or without sets/games suffix
            if lg == "TENNIS":
                if not regex.match(tennis_pattern, p.strip(), regex.IGNORECASE):
                    issues["spread_bad_format"].append({
                        "id": pick_id, "pick": p, "expected": "Player +/-X.X [sets/games]"
                    })
            elif not regex.match(spread_pattern, p.strip()):
                # Allow period-style spreads like "1H Team -X"
                if not any(ind.lower() in p.lower() for ind in period_indicators):
                    issues["spread_bad_format"].append({
                        "id": pick_id, "pick": p, "expected": "Team Name +/-X.X"
                    })
        
        # 6. Total format: "Team A vs Team B Over/Under X"
        if ty == "Total":
            if " vs " not in p.lower() and " over " not in p.lower() and " under " not in p.lower():
                issues["total_bad_format"].append({
                    "id": pick_id, "pick": p, "expected": "Team A vs Team B Over/Under X"
                })
    
    # Summary
    total = len(picks)
    issues["summary"] = {
        "total_picks": total,
        "invalid_league_count": len(issues["invalid_league"]),
        "invalid_type_count": len(issues["invalid_type"]),
        "period_misclassified_count": len(issues["period_misclassified"]),
        "moneyline_missing_ml_count": len(issues["moneyline_missing_ml"]),
        "spread_bad_format_count": len(issues["spread_bad_format"]),
        "total_bad_format_count": len(issues["total_bad_format"]),
    }
    
    # Print report
    log_subheader("FORMAT VALIDATION (pick_format.md)")
    
    s = issues["summary"]
    log_info(f"Total picks: {s['total_picks']}")
    
    if s["invalid_league_count"] == 0:
        log_success(f"League values: All valid")
    else:
        log_error(f"Invalid leagues: {s['invalid_league_count']}")
        for item in issues["invalid_league"][:3]:
            print(f"    ID {item['id']}: got '{item['got']}' for '{item['pick']}'")
    
    if s["invalid_type_count"] == 0:
        log_success(f"Type values: All valid")
    else:
        log_error(f"Invalid types: {s['invalid_type_count']}")
        for item in issues["invalid_type"][:3]:
            print(f"    ID {item['id']}: got '{item['got']}' for '{item['pick']}'")
    
    if s["period_misclassified_count"] > 0:
        log_warning(f"Period picks misclassified as Spread: {s['period_misclassified_count']}")
        for item in issues["period_misclassified"][:3]:
            print(f"    ID {item['id']}: '{item['pick']}' should be type=Period")
    
    if s["moneyline_missing_ml_count"] > 0:
        log_warning(f"Moneyline picks missing 'ML' suffix: {s['moneyline_missing_ml_count']}")
        for item in issues["moneyline_missing_ml"][:3]:
            print(f"    ID {item['id']}: '{item['pick']}' -> '{item['expected']}'")
    
    if s["spread_bad_format_count"] > 0:
        log_warning(f"Spread format issues: {s['spread_bad_format_count']}")
        for item in issues["spread_bad_format"][:3]:
            print(f"    ID {item['id']}: '{item['pick']}'")
    
    if s["total_bad_format_count"] > 0:
        log_warning(f"Total format issues: {s['total_bad_format_count']}")
        for item in issues["total_bad_format"][:3]:
            print(f"    ID {item['id']}: '{item['pick']}'")
    
    # Overall score
    total_issues = sum([
        s["invalid_league_count"],
        s["invalid_type_count"],
        s["period_misclassified_count"],
        s["moneyline_missing_ml_count"],
        s["spread_bad_format_count"],
        s["total_bad_format_count"],
    ])
    
    if total_issues == 0:
        log_success("FORMAT QUALITY: PERFECT")
    elif total_issues < s["total_picks"] * 0.1:
        log_success(f"FORMAT QUALITY: GOOD ({total_issues} minor issues)")
    elif total_issues < s["total_picks"] * 0.3:
        log_warning(f"FORMAT QUALITY: FAIR ({total_issues} issues)")
    else:
        log_error(f"FORMAT QUALITY: POOR ({total_issues} issues)")
    
    return issues


def load_cache(stage: str) -> Optional[dict]:
    """Load cached data for a stage"""
    cache_file = CACHE_FILES.get(stage)
    if cache_file and cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_warning(f"Failed to load cache {cache_file}: {e}")
    return None


def save_cache(stage: str, data: dict):
    """Save data to cache"""
    cache_file = CACHE_FILES.get(stage)
    if cache_file:
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            log_info(f"Cached to {cache_file}")
        except Exception as e:
            log_error(f"Failed to save cache: {e}")


def get_sample_size(args) -> Optional[int]:
    """Get sample size from args"""
    if args.sample is None:
        return SAMPLE_SIZES["quick"]  # Default to quick
    if args.sample in SAMPLE_SIZES:
        return SAMPLE_SIZES[args.sample]
    try:
        return int(args.sample)
    except ValueError:
        return SAMPLE_SIZES["quick"]


# =============================================================================
# STAGE: FETCH
# =============================================================================
async def stage_fetch(args) -> dict:
    """Fetch messages from Telegram"""
    log_header("STAGE: FETCH MESSAGES")
    
    # Check cache
    if not args.fresh:
        cached = load_cache("messages")
        if cached:
            log_success(f"Using cached messages ({len(cached.get('messages', []))} messages)")
            return cached
    
    log_info(f"Fetching from channel: {DEBUG_CHANNEL_ID} ({DEBUG_CHANNEL_NAME})")
    log_info(f"Target date: {args.date}")
    
    start_time = time.time()
    
    try:
        from src.telegram_client import tg_manager
        from config import TEMP_IMG_DIR
        
        # Connect
        authorized = await tg_manager.connect_client()
        if not authorized:
            log_error("Not authorized! Run the main app first to log in.")
            return {"error": "Not authorized", "messages": []}
        
        log_success("Telegram client connected")
        
        # Fetch messages
        messages = await tg_manager.fetch_messages([DEBUG_CHANNEL_ID], args.date)
        
        elapsed = time.time() - start_time
        
        result = {
            "channel_id": DEBUG_CHANNEL_ID,
            "channel_name": DEBUG_CHANNEL_NAME,
            "date": args.date,
            "fetch_time": elapsed,
            "message_count": len(messages),
            "messages": messages,
        }
        
        # Analyze
        log_subheader("FETCH RESULTS")
        log_success(f"Fetched {len(messages)} messages in {elapsed:.1f}s")
        
        # Count images
        total_images = sum(len(m.get("images", [])) for m in messages)
        msgs_with_images = sum(1 for m in messages if m.get("images"))
        msgs_with_text = sum(1 for m in messages if m.get("text", "").strip())
        
        log_info(f"Messages with images: {msgs_with_images}")
        log_info(f"Total images: {total_images}")
        log_info(f"Messages with text: {msgs_with_text}")
        
        # Check image files exist
        log_subheader("IMAGE FILE CHECK")
        missing_images = []
        existing_images = []
        
        for msg in messages:
            for img_path in msg.get("images", []):
                # Resolve path
                if img_path.startswith("/static/temp_images/"):
                    filename = img_path.split("/static/temp_images/")[-1]
                    full_path = Path(TEMP_IMG_DIR) / filename
                else:
                    full_path = Path(img_path)
                
                if full_path.exists():
                    existing_images.append(str(full_path))
                else:
                    missing_images.append(str(full_path))
        
        log_success(f"Images found on disk: {len(existing_images)}")
        if missing_images:
            log_error(f"Images MISSING: {len(missing_images)}")
            for p in missing_images[:5]:
                log_error(f"  - {p}")
            if len(missing_images) > 5:
                log_error(f"  ... and {len(missing_images) - 5} more")
        
        result["images_found"] = len(existing_images)
        result["images_missing"] = len(missing_images)
        result["missing_paths"] = missing_images[:10]
        
        # Sample messages
        log_subheader("SAMPLE MESSAGES (first 3)")
        for i, msg in enumerate(messages[:3]):
            print(f"\n{Colors.MAGENTA}Message {i+1} (ID: {msg.get('id')}){Colors.RESET}")
            print(f"  Text: {msg.get('text', '')[:100]}...")
            print(f"  Images: {msg.get('images', [])}")
            print(f"  Date: {msg.get('date')}")
        
        save_cache("messages", result)
        return result
        
    except Exception as e:
        log_error(f"Fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "messages": []}


# =============================================================================
# STAGE: OCR
# =============================================================================
def stage_ocr(args) -> dict:
    """Run OCR on images"""
    log_header("STAGE: OCR")
    
    # Check cache
    if not args.fresh:
        cached = load_cache("ocr")
        if cached:
            log_success(f"Using cached OCR results ({len(cached.get('results', {}))} images)")
            return cached
    
    # Load messages
    msg_cache = load_cache("messages")
    if not msg_cache or not msg_cache.get("messages"):
        log_error("No cached messages! Run 'fetch' stage first.")
        return {"error": "No messages cached", "results": {}}
    
    messages = msg_cache["messages"]
    sample_size = get_sample_size(args)
    
    if sample_size:
        messages = messages[:sample_size]
        log_info(f"Processing {len(messages)} messages (sample)")
    else:
        log_info(f"Processing all {len(messages)} messages")
    
    # Collect all image paths
    all_images = []
    for msg in messages:
        for img_path in msg.get("images", []):
            all_images.append({
                "msg_id": msg.get("id"),
                "path": img_path,
            })
    
    log_info(f"Total images to OCR: {len(all_images)}")
    
    if not all_images:
        log_warning("No images to process!")
        return {"results": {}, "errors": []}
    
    start_time = time.time()
    
    try:
        from src.ocr_handler import extract_text_batch
        from config import TEMP_IMG_DIR
        
        # Resolve paths and batch
        image_paths = [img["path"] for img in all_images]
        
        log_info("Running batch OCR...")
        ocr_results = extract_text_batch(image_paths)
        
        elapsed = time.time() - start_time
        
        # Build results dict
        results = {}
        errors = []
        empty_count = 0
        short_count = 0
        
        for i, (img_info, ocr_text) in enumerate(zip(all_images, ocr_results)):
            path = img_info["path"]
            msg_id = img_info["msg_id"]
            
            results[path] = {
                "msg_id": msg_id,
                "text": ocr_text,
                "length": len(ocr_text) if ocr_text else 0,
            }
            
            if not ocr_text or ocr_text.strip() == "":
                empty_count += 1
                errors.append({"path": path, "msg_id": msg_id, "error": "Empty OCR result"})
            elif len(ocr_text) < 20:
                short_count += 1
                errors.append({"path": path, "msg_id": msg_id, "error": f"Short result: '{ocr_text}'"})
        
        result = {
            "ocr_time": elapsed,
            "total_images": len(all_images),
            "results": results,
            "errors": errors,
            "stats": {
                "empty": empty_count,
                "short": short_count,
                "success": len(all_images) - empty_count,
            }
        }
        
        # Report
        log_subheader("OCR RESULTS")
        log_success(f"Completed in {elapsed:.1f}s")
        log_info(f"Success: {result['stats']['success']}/{len(all_images)}")
        
        if empty_count:
            log_error(f"Empty results: {empty_count}")
        if short_count:
            log_warning(f"Short results (<20 chars): {short_count}")
        
        # Sample OCR outputs
        log_subheader("SAMPLE OCR OUTPUTS (first 3 non-empty)")
        shown = 0
        for path, data in results.items():
            if data["text"] and len(data["text"]) > 20 and shown < 3:
                print(f"\n{Colors.MAGENTA}Image: {path}{Colors.RESET}")
                print(f"  Msg ID: {data['msg_id']}")
                print(f"  Text ({data['length']} chars):")
                preview = data["text"][:300].replace("\n", " ")
                print(f"    {preview}...")
                shown += 1
        
        if shown == 0:
            log_error("NO VALID OCR OUTPUTS!")
            log_subheader("ALL OCR RESULTS (showing failures)")
            for path, data in list(results.items())[:5]:
                print(f"\n{Colors.RED}Image: {path}{Colors.RESET}")
                print(f"  Text: '{data['text']}'")
        
        save_cache("ocr", result)
        return result
        
    except Exception as e:
        log_error(f"OCR failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "results": {}}


# =============================================================================
# STAGE: PARSE
# =============================================================================
def stage_parse(args) -> dict:
    """Run AI parsing on OCR text"""
    log_header("STAGE: PARSE (AI Fill)")
    
    # Check cache
    if not args.fresh:
        cached = load_cache("parse")
        if cached:
            log_success(f"Using cached parse results ({len(cached.get('picks', []))} picks)")
            return cached
    
    # Load dependencies
    msg_cache = load_cache("messages")
    ocr_cache = load_cache("ocr")
    
    if not msg_cache or not msg_cache.get("messages"):
        log_error("No cached messages! Run 'fetch' stage first.")
        return {"error": "No messages cached", "picks": []}
    
    if not ocr_cache or not ocr_cache.get("results"):
        log_error("No cached OCR! Run 'ocr' stage first.")
        return {"error": "No OCR cached", "picks": []}
    
    messages = msg_cache["messages"]
    ocr_results = ocr_cache["results"]
    
    sample_size = get_sample_size(args)
    if sample_size:
        messages = messages[:sample_size]
    
    log_info(f"Processing {len(messages)} messages")
    log_info(f"OCR results available: {len(ocr_results)}")
    
    start_time = time.time()
    
    try:
        from src.prompt_builder import generate_ai_prompt
        from src.openrouter_client import openrouter_completion
        
        # Build selected_data format expected by generate_ai_prompt
        selected_data = []
        for msg in messages:
            ocr_texts = []
            for img_path in msg.get("images", []):
                ocr_data = ocr_results.get(img_path, {})
                if ocr_data.get("text"):
                    ocr_texts.append(ocr_data["text"])
            
            selected_data.append({
                "id": msg.get("id"),
                "text": msg.get("text", ""),
                "ocr_texts": ocr_texts,
            })
        
        # Check OCR coverage
        msgs_with_ocr = sum(1 for m in selected_data if m.get("ocr_texts"))
        log_info(f"Messages with OCR text: {msgs_with_ocr}/{len(messages)}")
        
        if msgs_with_ocr == 0:
            log_error("NO MESSAGES HAVE OCR TEXT! Parse will fail.")
            return {"error": "No OCR text available", "picks": []}
        
        # Build prompt
        log_info("Building AI prompt...")
        prompt = generate_ai_prompt(selected_data)
        
        log_subheader("PROMPT PREVIEW")
        print(f"Prompt length: {len(prompt)} chars")
        print(f"First 500 chars:\n{prompt[:500]}...")
        
        # Call AI
        log_info("Calling OpenRouter AI...")
        
        model = "mistralai/devstral-2512:free"
        response = openrouter_completion(prompt, model=model)
        
        elapsed = time.time() - start_time
        
        log_subheader("RAW AI RESPONSE")
        print(f"Response length: {len(response)} chars")
        print(f"First 1000 chars:\n{response[:1000]}")
        
        # Parse response
        picks = []
        try:
            # Try to extract JSON
            clean = response.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0]
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0]
            
            data = json.loads(clean)
            if isinstance(data, dict) and "picks" in data:
                picks = data["picks"]
            elif isinstance(data, list):
                picks = data
                
        except json.JSONDecodeError as e:
            log_error(f"JSON parse failed: {e}")
            log_error(f"Raw response: {response[:500]}")
        
        result = {
            "parse_time": elapsed,
            "model": model,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "raw_response": response,
            "picks": picks,
            "pick_count": len(picks),
        }
        
        log_subheader("PARSE RESULTS")
        log_success(f"Completed in {elapsed:.1f}s")
        log_info(f"Picks extracted: {len(picks)}")
        
        # Analyze picks quality against pick_format.md
        if picks:
            format_issues = validate_pick_format(picks)
            result["format_issues"] = format_issues
            
            log_subheader("SAMPLE PICKS DETAILED VIEW (first 5)")
            for i, pick in enumerate(picks[:5]):
                pick_id = pick.get("id")
                
                # Find source text/OCR
                source_item = next((item for item in selected_data if item["id"] == pick_id), None)
                
                print(f"\n{Colors.MAGENTA}--- PICK {i+1} (ID: {pick_id}) ---{Colors.RESET}")
                
                if source_item:
                    # Show Text Caption
                    caption = source_item.get("text", "").strip()
                    if caption:
                        print(f"{Colors.YELLOW}[CAPTION]{Colors.RESET}\n{caption[:200]}{'...' if len(caption)>200 else ''}")
                    
                    # Show OCR
                    ocr_texts = source_item.get("ocr_texts", [])
                    if ocr_texts:
                        print(f"{Colors.YELLOW}[OCR CONTENT]{Colors.RESET}")
                        for idx, text in enumerate(ocr_texts):
                            print(f"  Img {idx+1}: {text[:300].replace(chr(10), ' ')}{'...' if len(text)>300 else ''}")
                
                print(f"{Colors.GREEN}[PARSED PICK]{Colors.RESET}")
                print(json.dumps(pick, indent=2))
        
        save_cache("parse", result)
        return result
        
    except Exception as e:
        log_error(f"Parse failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "picks": []}


# =============================================================================
# STAGE: GRADE
# =============================================================================
def stage_grade(args) -> dict:
    """Grade picks against actual scores"""
    log_header("STAGE: GRADE")
    
    # Check cache
    if not args.fresh:
        cached = load_cache("grade")
        if cached:
            log_success(f"Using cached grades ({len(cached.get('graded', []))} picks)")
            return cached
    
    # Load parse results
    parse_cache = load_cache("parse")
    if not parse_cache or not parse_cache.get("picks"):
        log_error("No cached picks! Run 'parse' stage first.")
        return {"error": "No picks cached", "graded": []}
    
    picks = parse_cache["picks"]
    log_info(f"Grading {len(picks)} picks")
    
    start_time = time.time()
    
    try:
        from src.grader import grade_picks
        from src.score_fetcher import fetch_scores_for_date
        
        # Fetch scores
        # Extract relevant leagues from picks to optimize fetch
        relevant_leagues = set()
        for p in picks:
             lg = p.get('lg') or p.get('league') or ''
             if lg: relevant_leagues.add(str(lg))
             
        log_info(f"Fetching scores for {args.date} (Leagues: {', '.join(relevant_leagues)})...")
        scores = fetch_scores_for_date(args.date, requested_leagues=list(relevant_leagues))
        log_info(f"Fetched {len(scores)} game scores")
        
        # Grade
        log_info("Grading picks...")
        graded = grade_picks(picks, scores)
        
        elapsed = time.time() - start_time
        
        # Analyze
        wins = sum(1 for p in graded if p.get("result") == "WIN")
        losses = sum(1 for p in graded if p.get("result") == "LOSS")
        pushes = sum(1 for p in graded if p.get("result") == "PUSH")
        pending = sum(1 for p in graded if p.get("result") in [None, "PENDING", ""])
        
        result = {
            "grade_time": elapsed,
            "total_picks": len(picks),
            "graded": graded,
            "stats": {
                "wins": wins,
                "losses": losses,
                "pushes": pushes,
                "pending": pending,
            }
        }
        
        log_subheader("GRADE RESULTS")
        log_success(f"Completed in {elapsed:.1f}s")
        log_info(f"Wins: {wins}, Losses: {losses}, Pushes: {pushes}, Pending: {pending}")
        
        if pending > len(picks) * 0.8:
            log_warning("Most picks are PENDING - scores may not be available yet")
        
        save_cache("grade", result)
        return result
        
    except Exception as e:
        log_error(f"Grade failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "graded": []}


# =============================================================================
# STAGE: REPORT
# =============================================================================
def stage_report(args) -> dict:
    """Generate comprehensive diagnostic report from cached data"""
    log_header("DIAGNOSTIC REPORT")
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "stages": {},
    }
    
    # Messages
    log_subheader("MESSAGES CACHE")
    msg_cache = load_cache("messages")
    if msg_cache:
        msgs = msg_cache.get("messages", [])
        log_success(f"Cached: {len(msgs)} messages")
        log_info(f"Channel: {msg_cache.get('channel_name')} ({msg_cache.get('channel_id')})")
        log_info(f"Date: {msg_cache.get('date')}")
        log_info(f"Images found: {msg_cache.get('images_found', 'N/A')}")
        log_info(f"Images missing: {msg_cache.get('images_missing', 'N/A')}")
        
        if msg_cache.get("missing_paths"):
            log_error("Missing image paths:")
            for p in msg_cache["missing_paths"][:3]:
                print(f"  {Colors.RED}{p}{Colors.RESET}")
        
        report["stages"]["messages"] = {
            "count": len(msgs),
            "images_found": msg_cache.get("images_found"),
            "images_missing": msg_cache.get("images_missing"),
        }
    else:
        log_warning("No messages cache")
    
    # OCR
    log_subheader("OCR CACHE")
    ocr_cache = load_cache("ocr")
    if ocr_cache:
        results = ocr_cache.get("results", {})
        stats = ocr_cache.get("stats", {})
        log_success(f"Cached: {len(results)} OCR results")
        log_info(f"Success: {stats.get('success', 'N/A')}")
        log_info(f"Empty: {stats.get('empty', 'N/A')}")
        log_info(f"Short: {stats.get('short', 'N/A')}")
        
        # Check OCR quality
        total_chars = sum(r.get("length", 0) for r in results.values())
        log_info(f"Total OCR characters: {total_chars}")
        
        if stats.get("empty", 0) > len(results) * 0.5:
            log_error("CRITICAL: More than 50% of OCR results are EMPTY!")
        
        report["stages"]["ocr"] = {
            "count": len(results),
            "stats": stats,
            "total_chars": total_chars,
        }
    else:
        log_warning("No OCR cache")
    
    # Parse
    log_subheader("PARSE CACHE")
    parse_cache = load_cache("parse")
    if parse_cache:
        picks = parse_cache.get("picks", [])
        log_success(f"Cached: {len(picks)} picks")
        log_info(f"Model: {parse_cache.get('model', 'N/A')}")
        log_info(f"Prompt length: {parse_cache.get('prompt_length', 'N/A')}")
        
        # Run format validation
        if picks:
            format_issues = validate_pick_format(picks)
            report["stages"]["parse"] = {
                "pick_count": len(picks),
                "format_issues": format_issues["summary"],
            }
        else:
            report["stages"]["parse"] = {"pick_count": 0}
    else:
        log_warning("No parse cache")
    
    # Grade
    log_subheader("GRADE CACHE")
    grade_cache = load_cache("grade")
    if grade_cache:
        stats = grade_cache.get("stats", {})
        log_success(f"Cached: {grade_cache.get('total_picks', 0)} graded picks")
        log_info(f"Wins: {stats.get('wins')}, Losses: {stats.get('losses')}")
        log_info(f"Pushes: {stats.get('pushes')}, Pending: {stats.get('pending')}")
        
        report["stages"]["grade"] = stats
    else:
        log_warning("No grade cache")
    
    # Summary
    log_subheader("PIPELINE HEALTH SUMMARY")
    
    issues = []
    
    if msg_cache and msg_cache.get("images_missing", 0) > 0:
        issues.append(f"FETCH: {msg_cache['images_missing']} images not saved to disk")
    
    if ocr_cache:
        stats = ocr_cache.get("stats", {})
        if stats.get("empty", 0) > 0:
            issues.append(f"OCR: {stats['empty']} empty results (images not found or OCR failed)")
    
    if parse_cache:
        picks = parse_cache.get("picks", [])
        unknown = sum(1 for p in picks if "unknown" in str(p.get("lg", "")).lower())
        if unknown > len(picks) * 0.3:
            issues.append(f"PARSE: {unknown}/{len(picks)} picks have Unknown league")
    
    if issues:
        log_error("ISSUES DETECTED:")
        for issue in issues:
            print(f"  {Colors.RED}- {issue}{Colors.RESET}")
    else:
        log_success("No major issues detected")
    
    report["issues"] = issues
    save_cache("diagnostics", report)
    
    return report


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Debug Pipeline Tool for Telegram Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "stage",
        choices=["fetch", "ocr", "parse", "grade", "report", "full"],
        help="Pipeline stage to run"
    )
    
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore cache, re-run from scratch"
    )
    
    parser.add_argument(
        "--sample",
        default="quick",
        help="Sample size: quick (10), medium (30), full (all), or a number"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    parser.add_argument(
        "--date",
        default=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        help="Target date (YYYY-MM-DD), default: yesterday"
    )
    
    args = parser.parse_args()
    
    log_header(f"DEBUG PIPELINE - {args.stage.upper()}")
    log_info(f"Date: {args.date}")
    log_info(f"Sample: {args.sample}")
    log_info(f"Fresh: {args.fresh}")
    log_info(f"Cache dir: {CACHE_DIR}")
    
    if args.stage == "fetch":
        asyncio.run(stage_fetch(args))
    
    elif args.stage == "ocr":
        stage_ocr(args)
    
    elif args.stage == "parse":
        stage_parse(args)
    
    elif args.stage == "grade":
        stage_grade(args)
    
    elif args.stage == "report":
        stage_report(args)
    
    elif args.stage == "full":
        log_info("Running full pipeline...")
        asyncio.run(stage_fetch(args))
        stage_ocr(args)
        stage_parse(args)
        stage_grade(args)
        stage_report(args)
    
    log_header("DONE")


if __name__ == "__main__":
    main()
