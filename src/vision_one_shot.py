"""
Vision One-Shot - Direct image parsing with vision models.

This module has been optimized for maximum token efficiency:
- 1-char JSON keys (i, c, l, t, p, o, u)
- Type abbreviations (ML, SP, PP, etc.)
- Compressed instructions

The decoder module expands compact responses back to full field names.
"""

import os
import json
import base64
import logging
from typing import List, Dict, Any, Optional

from src.openrouter_client import openrouter_completion
from src.prompts.decoder import expand_picks_list

# Vision model for direct image parsing
VISION_MODEL = "google/gemini-2.0-flash-exp:free"


def parse_image_direct(image_path: str) -> List[Dict[str, Any]]:
    """
    One-Shot Vision Parsing: Sends image directly to LLM and asks for JSON.
    Bypasses OCR text generation.
    
    Returns picks with FULL field names (expanded from compact format).
    
    Args:
        image_path: Path to the image file
        
    Returns:
        List of pick dicts with full field names
    """
    if not os.path.exists(image_path):
        logging.error(f"[OneShot] Image not found: {image_path}")
        return []

    # Ultra-compact prompt (~60% token reduction)
    prompt = """Extract betting picks from this image. Return JSON only, no markdown.

KEYS:i=id,c=capper,l=league,t=type,p=pick,o=odds,u=units
TYPES:ML=Moneyline,SP=Spread,TL=Total,PP=Player Prop,TP=Team Prop,GP=Game Prop,PD=Period,PL=Parlay,TS=Teaser,FT=Future
LEAGUES:NFL,NCAAF,NBA,NCAAB,WNBA,MLB,NHL,EPL,MLS,UCL,UFC,TENNIS,SOCCER,Other

PICK FORMATS:
ML=Team ML|SP=Team -7.5|TL=Team A vs B O/U X
PP=Name: Stat O/U X|PD=1H/1Q/F5 + bet|PL=(LG) Leg1 / (LG) Leg2

RULES:
1.l=infer league from team/player names
2.Ignore watermarks(@cappersfree),ads
3.c=capper name if visible,else "Unknown"
4.o=American odds int or null
5.u=units float,default 1

OUTPUT:{"picks":[{"i":0,"c":"Name","l":"NBA","t":"SP","p":"Lakers -5","o":-110,"u":1}]}"""
    
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
            # Clean markdown if present
            clean_resp = response_str.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
            elif clean_resp.startswith("```"):
                clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
            
            data = json.loads(clean_resp)
            
            # Handle list vs dict response
            if isinstance(data, list):
                compact_picks = data
            elif isinstance(data, dict):
                compact_picks = data.get("picks", [])
            else:
                compact_picks = []
            
            # Expand compact format to full field names
            expanded_picks = expand_picks_list(compact_picks)
            
            # Set message_id to 0 (placeholder) if not present
            for p in expanded_picks:
                p.setdefault("message_id", 0)
                
            return expanded_picks
            
        except json.JSONDecodeError:
            logging.error(f"[OneShot] Invalid JSON returned: {response_str[:100]}...")
            return []
            
    except Exception as e:
        logging.error(f"[OneShot] Error: {e}")
        return []
