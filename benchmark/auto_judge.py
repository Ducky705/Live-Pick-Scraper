"""
Auto Judge - AI-Powered Golden Set Generator
=============================================
Uses the most powerful available model (DeepSeek R1T2 Chimera) as an "Oracle"
to establish ground truth from raw messages. NO MANUAL LABELING REQUIRED.

This creates a golden set that the scraper's output can be compared against,
enabling automated accuracy benchmarking without human intervention.

Usage:
    python -m benchmark.auto_judge [--limit N] [--output FILE]
"""

import os
import sys
import json
import logging
import time
import re
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup paths
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# The Oracle Model - Most powerful free model available
JUDGE_MODEL = "tngtech/deepseek-r1t2-chimera:free"

# Backup models in case primary fails
BACKUP_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

# Simple, focused prompt for the Judge
# Key principle: LESS IS MORE. The Judge should just FIND picks, not format them.
JUDGE_SYSTEM_PROMPT = """You are a sports betting pick detector. Your ONLY job is to identify betting picks from Telegram messages.

A VALID PICK contains:
1. A team name OR player name (e.g., "Lakers", "LeBron James", "Chiefs")
2. A bet type indicator (e.g., "-5", "ML", "Over 220", "+3.5", "to score anytime")

NOT PICKS (ignore these):
- "Join VIP", "DM for picks", promotional text
- Past results with checkmarks (recaps)
- Bankroll advice ("bet 2% of bankroll")
- Sportsbook names alone ("DraftKings", "FanDuel")

For each message, extract:
- capper: Who posted this pick (look for usernames, headers)
- picks: Array of pick strings exactly as written
- confidence: 1-10 how confident you are these are real picks

Output JSON only. No markdown."""


def call_judge_model(prompt: str, images: Optional[List[str]] = None, timeout: int = 180) -> Optional[str]:
    """
    Call the Judge model via OpenRouter.
    Uses aggressive retry logic since this is for offline benchmarking (time doesn't matter).
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logging.error("OPENROUTER_API_KEY not set!")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram-scraper.local",
        "X-Title": "CapperSuite-Judge"
    }
    
    # Build content
    content = [{"type": "text", "text": prompt}]
    
    if images:
        for img_path in images:
            try:
                if os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })
            except Exception as e:
                logging.warning(f"Failed to load image {img_path}: {e}")
    
    models_to_try = [JUDGE_MODEL] + BACKUP_MODELS
    
    for model in models_to_try:
        for attempt in range(5):  # 5 retries per model
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": content if images else prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 4096,
            }
            
            try:
                logging.info(f"[Judge] Calling {model} (attempt {attempt + 1})...")
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                
                if response.status_code == 429:
                    wait = min(30, 5 * (attempt + 1))
                    logging.warning(f"[Judge] Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        result = data['choices'][0]['message']['content']
                        # Clean thinking blocks from DeepSeek
                        result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)
                        return result.strip()
                
                logging.warning(f"[Judge] {model} returned {response.status_code}")
                
            except requests.exceptions.Timeout:
                logging.warning(f"[Judge] Timeout with {model}")
            except Exception as e:
                logging.error(f"[Judge] Error with {model}: {e}")
            
            time.sleep(2)
        
        logging.warning(f"[Judge] {model} exhausted. Trying next model...")
    
    return None


def extract_json_from_response(text: str) -> Optional[Dict]:
    """Extract JSON from potentially messy model output."""
    if not text:
        return None
    
    # Try direct parse first
    try:
        return json.loads(text)
    except:
        pass
    
    # Try to find JSON in markdown blocks
    if "```json" in text:
        try:
            json_str = text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        except:
            pass
    
    if "```" in text:
        try:
            json_str = text.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
        except:
            pass
    
    # Try to find first { or [ and parse from there
    for i, c in enumerate(text):
        if c in '{[':
            try:
                return json.loads(text[i:])
            except:
                pass
    
    return None


def load_ocr_results(cache_dir: str) -> Dict[int, str]:
    """Load OCR results and create a map of msg_id -> ocr_text."""
    ocr_path = os.path.join(cache_dir, "ocr_results.json")
    ocr_map = {}
    
    if os.path.exists(ocr_path):
        with open(ocr_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = data.get('results', {})
        for img_path, ocr_data in results.items():
            msg_id = ocr_data.get('msg_id')
            text = ocr_data.get('text', '')
            if msg_id and text:
                # Append if multiple images for same message
                if msg_id in ocr_map:
                    ocr_map[msg_id] += "\n---\n" + text
                else:
                    ocr_map[msg_id] = text
        
        logging.info(f"Loaded OCR for {len(ocr_map)} messages")
    
    return ocr_map


def load_messages(messages_path: str, limit: Optional[int] = None) -> List[Dict]:
    """Load messages from cache file and merge OCR data."""
    if not os.path.exists(messages_path):
        logging.error(f"Messages file not found: {messages_path}")
        return []
    
    with open(messages_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle wrapped format ({"messages": [...]}) vs direct array
    if isinstance(data, dict) and 'messages' in data:
        messages = data['messages']
    elif isinstance(data, list):
        messages = data
    else:
        logging.error("Unknown messages.json format")
        return []
    
    # Load OCR results
    cache_dir = os.path.dirname(messages_path)
    ocr_map = load_ocr_results(cache_dir)
    
    # Merge OCR into messages
    for msg in messages:
        msg_id = msg.get('id')
        if msg_id and msg_id in ocr_map:
            msg['ocr_texts'] = [ocr_map[msg_id]]
    
    # Filter to only messages with content
    valid = []
    for msg in messages:
        has_text = bool(msg.get('text', '').strip())
        has_images = bool(msg.get('images') or msg.get('image'))
        has_ocr = bool(msg.get('ocr_text') or msg.get('ocr_texts'))
        
        if has_text or has_images or has_ocr:
            valid.append(msg)
    
    if limit:
        valid = valid[:limit]
    
    logging.info(f"Loaded {len(valid)} messages with content")
    return valid


def judge_message(msg: Dict) -> Dict:
    """
    Have the Judge analyze a single message and determine ground truth.
    Returns a judgment record.
    """
    msg_id = msg.get('id')
    text = msg.get('text', '')
    ocr_texts = msg.get('ocr_texts', [])
    if not ocr_texts and msg.get('ocr_text'):
        ocr_texts = [msg.get('ocr_text')]
    
    # Build context for the Judge
    context_parts = []
    if text:
        context_parts.append(f"CAPTION:\n{text}")
    
    for i, ocr in enumerate(ocr_texts):
        if ocr and ocr.strip():
            context_parts.append(f"IMAGE {i+1} TEXT:\n{ocr}")
    
    if not context_parts:
        return {
            "message_id": msg_id,
            "has_picks": False,
            "picks": [],
            "capper": None,
            "confidence": 0,
            "reason": "No text content"
        }
    
    full_context = "\n\n".join(context_parts)
    
    prompt = f"""Analyze this Telegram message and extract any sports betting picks.

MESSAGE ID: {msg_id}

{full_context}

Respond with JSON:
{{
    "has_picks": true/false,
    "picks": ["pick 1 as written", "pick 2 as written"],
    "capper": "capper name if found",
    "confidence": 1-10
}}"""

    # Get images if available
    images = []
    img_paths = msg.get('images', [])
    if not img_paths and msg.get('image'):
        img_paths = [msg.get('image')]
    
    for img_path in img_paths:
        # Resolve path
        if img_path.startswith('/static/'):
            abs_path = os.path.join(BASE_DIR, img_path.lstrip('/').replace('/', os.sep))
        else:
            abs_path = img_path
        
        if os.path.exists(abs_path):
            images.append(abs_path)
    
    # Call the Judge (with images if available for vision analysis)
    response = call_judge_model(prompt, images[:3] if images else None)  # Limit to 3 images
    
    if not response:
        return {
            "message_id": msg_id,
            "has_picks": None,  # Unknown - Judge failed
            "picks": [],
            "capper": None,
            "confidence": 0,
            "reason": "Judge model failed to respond"
        }
    
    # Parse response
    parsed = extract_json_from_response(response)
    
    if parsed:
        return {
            "message_id": msg_id,
            "has_picks": parsed.get("has_picks", False),
            "picks": parsed.get("picks", []),
            "capper": parsed.get("capper"),
            "confidence": parsed.get("confidence", 5),
            "raw_response": response[:500]  # Keep snippet for debugging
        }
    else:
        return {
            "message_id": msg_id,
            "has_picks": None,
            "picks": [],
            "capper": None,
            "confidence": 0,
            "reason": f"Failed to parse: {response[:200]}"
        }


def generate_golden_set(messages: List[Dict], batch_size: int = 5) -> List[Dict]:
    """
    Process all messages through the Judge to create a golden set.
    Uses batching to manage rate limits.
    """
    golden_set = []
    total = len(messages)
    
    for i, msg in enumerate(messages):
        logging.info(f"[Judge] Processing message {i+1}/{total} (ID: {msg.get('id')})")
        
        judgment = judge_message(msg)
        golden_set.append(judgment)
        
        # Rate limit management
        if (i + 1) % batch_size == 0:
            logging.info(f"[Judge] Batch complete. Brief pause...")
            time.sleep(3)
    
    return golden_set


def save_golden_set(golden_set: List[Dict], output_path: str):
    """Save the golden set to file."""
    # Calculate stats
    total = len(golden_set)
    with_picks = sum(1 for g in golden_set if g.get('has_picks'))
    unknown = sum(1 for g in golden_set if g.get('has_picks') is None)
    
    output = {
        "metadata": {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "judge_model": JUDGE_MODEL,
            "total_messages": total,
            "messages_with_picks": with_picks,
            "unknown_failures": unknown,
        },
        "judgments": golden_set
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Golden set saved to {output_path}")
    logging.info(f"Stats: {with_picks}/{total} messages have picks ({unknown} unknown)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Judge - Generate golden set from messages")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of messages to process")
    parser.add_argument("--input", type=str, default=None, help="Input messages file")
    parser.add_argument("--output", type=str, default=None, help="Output golden set file")
    args = parser.parse_args()
    
    # Paths
    messages_path = args.input or os.path.join(BASE_DIR, "cache", "messages.json")
    output_path = args.output or os.path.join(BASE_DIR, "benchmark", "reports", "auto_golden_set.json")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Load messages
    messages = load_messages(messages_path, args.limit)
    
    if not messages:
        logging.error("No messages to process!")
        return
    
    # Generate golden set
    logging.info(f"Starting Judge analysis of {len(messages)} messages...")
    golden_set = generate_golden_set(messages)
    
    # Save
    save_golden_set(golden_set, output_path)
    
    print(f"\nGolden set generated: {output_path}")
    print(f"Run 'python -m benchmark.run_autotest' to compare against scraper output.")


if __name__ == "__main__":
    main()
