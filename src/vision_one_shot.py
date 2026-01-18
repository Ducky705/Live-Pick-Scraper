
import os
import json
import base64
import logging
from typing import List, Dict, Any, Optional

from src.openrouter_client import openrouter_completion
from src.utils import smart_merge_odds

# We use Gemini 2.0 Flash for this because it has excellent vision capabilities
# and is currently free/fast. DeepSeek R1 is text-only.
VISION_MODEL = "google/gemini-2.0-flash-exp:free"

def parse_image_direct(image_path: str) -> List[Dict[str, Any]]:
    """
    One-Shot Vision Parsing: Sends image directly to LLM and asks for JSON.
    Bypasses OCR text generation.
    """
    if not os.path.exists(image_path):
        logging.error(f"[OneShot] Image not found: {image_path}")
        return []

    prompt = """
    Analyze this sports betting slip image. Extract all betting picks into a JSON structure.
    
    Return a JSON object with a key "picks" containing a list of objects.
    Each object must have:
    - "sport": (String) "NBA", "NFL", "NHL", "MLB", "NCAAF", "NCAAB", "UFC", "Tennis", "Soccer" or "Other".
    - "league": (String) The specific league (e.g. "NBA", "Premier League").
    - "capper_name": (String) The name of the person/channel posting (often at top/bottom). If unknown, use "Unknown".
    - "matchup": (String) "Team A vs Team B".
    - "type": (String) "Moneyline", "Spread", "Total", "Prop", "Parlay".
    - "pick": (String) The specific bet (e.g. "Lakers -5", "Over 210.5").
    - "odds": (String or Number) The odds (e.g. -110, +200, 1.91). If American, use string (e.g. "-110").
    - "units": (Number) Bet size in units (e.g. 1.0, 2.5). Default to 1.0 if not found.
    
    Rules:
    1. If a parlay is shown, list each leg as a separate pick if possible, or the whole parlay as one if legs aren't detailed.
    2. infer the Sport/League from team names if not explicitly stated.
    3. Ignore advertisements, watermarks (@cappersfree), or generic text.
    4. Return ONLY valid JSON. No markdown formatting.
    """
    
    try:
        # Encode image
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")
            
        logging.info(f"[OneShot] Sending {os.path.basename(image_path)} to {VISION_MODEL}...")
        
        response_str = openrouter_completion(
            prompt, 
            model=VISION_MODEL, 
            images=[b64_img], 
            timeout=60
        )
        
        if not response_str:
            logging.warning("[OneShot] Empty response from API.")
            return []
            
        # Parse JSON
        try:
            data = json.loads(response_str)
            
            # Handle list vs dict response
            if isinstance(data, list):
                picks = data
            elif isinstance(data, dict):
                picks = data.get("picks", [])
            else:
                picks = []
            
            # Post-process/Normalize keys to match our internal standard
            normalized_picks = []
            for p in picks:
                norm = {
                    "capper_name": p.get("capper_name", "Unknown"),
                    "league": p.get("league", "Other"),
                    "sport": p.get("sport", "Other"),
                    "type": p.get("type", "Straight"),
                    "pick": p.get("pick", "Unknown"),
                    "odds": p.get("odds", None),
                    "units": p.get("units", 1.0),
                    "message_id": 0 # Placeholder
                }
                normalized_picks.append(norm)
                
            return normalized_picks
            
        except json.JSONDecodeError:
            logging.error(f"[OneShot] Invalid JSON returned: {response_str[:100]}...")
            return []
            
    except Exception as e:
        logging.error(f"[OneShot] Error: {e}")
        return []
