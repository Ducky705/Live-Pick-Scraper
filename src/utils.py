# src/utils.py
"""
Utility functions for the TelegramScraper.

This module provides shared helpers for:
- Text normalization and cleaning
- File operations
- Content detection
"""

from collections import Counter
import re
import os
import glob
import unicodedata
from typing import Optional


def normalize_string(text: Optional[str], remove_spaces: bool = False) -> str:
    """
    Normalize a string for comparison purposes.
    
    This is the canonical normalization function - use this instead of
    creating new normalize_name/normalize_text functions elsewhere.
    
    Args:
        text: Input string to normalize
        remove_spaces: If True, removes all spaces (useful for name matching)
    
    Returns:
        Normalized lowercase string with special chars removed
    
    Examples:
        >>> normalize_string("Los Angeles Lakers")
        'los angeles lakers'
        >>> normalize_string("Los Angeles Lakers", remove_spaces=True)
        'losangeleslakers'
        >>> normalize_string("Café André")
        'cafe andre'
    """
    if not text:
        return ""
    
    # Normalize unicode (NFKC handles accents, ligatures, etc.)
    text = unicodedata.normalize("NFKC", str(text))
    
    # Replace special whitespace with regular space
    text = text.replace("\u00A0", " ").replace("\u202F", " ")
    
    # Lowercase
    text = text.lower()
    
    # Remove special characters but keep alphanumeric and spaces
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    if remove_spaces:
        text = text.replace(" ", "")
    
    return text

def cleanup_temp_images(directory):
    """Deletes only .jpg files in the specified directory to save space."""
    if not os.path.exists(directory):
        return
    
    files = glob.glob(os.path.join(directory, "*.jpg"))
    if files:
        print(f"[System] Cleaning up {len(files)} old temporary images...")
        for f in files:
            try:
                os.remove(f)
            except Exception as e:
                print(f"Error deleting {f}: {e}")

def detect_common_watermark(messages_ocr_text):
    if not messages_ocr_text: return ""
    all_lines = []
    for text in messages_ocr_text:
        lines = [l.strip().lower() for l in text.split('\n') if len(l.strip()) > 3]
        all_lines.extend(lines)
    if not all_lines: return ""
    counts = Counter(all_lines)
    detected = []
    for line, count in counts.most_common(10):
        if count > 1 and ('@' in line or 'dm' in line or 'join' in line):
            detected.append(line)
    return ", ".join(detected[:3])

def filter_text(original_text, watermark_input):
    if not original_text: return ""
    
    terms = [t.strip() for t in watermark_input.split(',') if t.strip()]
    cleaned = original_text
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        cleaned = pattern.sub('', cleaned)
        
    noise_patterns = [
        r'DM\**\W+\**@cappersfree.*', 
        r'@cappers(free|tree).*',      
        r'➖➖+',                       
        r'✅',
        r'Join The BEST Team.*',
        r'Let\'s crush it.*',
        r'EXCLUSIVE PACKAGE.*'
    ]
    
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
    return '\n'.join(lines)

def is_ad_content(text):
    if not text: return False
    text_upper = text.upper()
    ad_triggers = ["HUGE PROMO ALLERT", "DAYS FOR THE PRICE OF", "EXCLUSIVE PACKAGE", "CHEAPEST PRICES"]
    if any(trigger in text_upper for trigger in ad_triggers):
        if not re.search(r'\d', text):
            return True
    return False

def backfill_odds(picks):
    """
    1. Identifies duplicates by pick text.
    2. Finds if any copy of that pick has valid odds.
    3. Fills missing odds from the valid ones.
    4. Does NOT default to -110 if nothing found.
    """
    odds_map = {}
    def normalize(s): return str(s).lower().replace(" ", "").strip()

    # Pass 1: Harvest known odds
    for p in picks:
        p_text = normalize(p.get('pick', ''))
        p_odds = p.get('odds')
        
        # Validate that odds is actually a number/string worth saving
        isValidOdds = p_odds is not None and str(p_odds).strip() != "" and str(p_odds).lower() != "none"
        
        if isValidOdds and p_text:
            if p_text not in odds_map:
                odds_map[p_text] = p_odds
            
    # Pass 2: Backfill or Leave Blank
    for p in picks:
        # Clean Capper Name
        if p.get('capper_name'):
            name = str(p['capper_name']).strip()
            if len(name) > 3 and name.isupper(): p['capper_name'] = name.title()
            elif name.lower() == 'n/a': p['capper_name'] = 'Unknown'
        else:
            p['capper_name'] = 'Unknown'

        if not p.get('league'): p['league'] = 'Other'

        # Handle Odds
        current_odds = p.get('odds')
        is_missing = current_odds is None or str(current_odds).strip() == "" or str(current_odds).lower() == "none"
        
        if is_missing:
            p_text = normalize(p.get('pick', ''))
            if p_text in odds_map:
                p['odds'] = odds_map[p_text] # Crowdsourced match
            else:
                p['odds'] = None # Explicitly null, do not default to -110
        
        # Unit Cap Logic
        raw_unit = p.get('units')
        if raw_unit is None or str(raw_unit).strip() in ['', 'null', 'None']:
            p['units'] = 1.0
        else:
            try:
                clean_str = str(raw_unit).lower().replace('units', '').replace('unit', '').replace('u', '').strip()
                val = float(clean_str)
                p['units'] = 1.0 if val > 25 else val
            except ValueError:
                p['units'] = 1.0
                
    return picks

def clean_text_for_ai(text):
    """
    Retrieval-Augmented compression: Removes high-entropy noise to save tokens.
    """
    if not text: return ""
    
    # 1. Remove URLs
    text = re.sub(r'http\S+|www\.\S+', '', text)
    
    # 2. Remove standard legal disclaimers
    text = re.sub(r'(?i)(gambling\sproblem|1-800-\d{3}-\d{4}|call\s*1-800).*', '', text)
    
    # 3. Remove excess punctuation/separators
    text = re.sub(r'[-=_]{3,}', ' ', text)
    
    # 4. Remove generic Telegram noise
    text = re.sub(r'(?i)(join\s*us|subscribe|link\s*in\s*bio|click\s*here|t\.me\/).*', '', text)
    
    # 5. CRITICAL: Remove known channel watermarks that get misidentified as cappers
    # These are channel branding, NOT capper names
    watermarks = [
        r'@?cappersfree',
        r'@?capperstree', 
        r'@?cappers_free',
        r'@?freecappers',
        r'@?vippicks',
        r'@?freepicks',
        r'@?sportsbetting',
        r'DM\s*@\w+',  # "DM @username" patterns
    ]
    for wm in watermarks:
        text = re.sub(wm, '', text, flags=re.IGNORECASE)
    
    # 6. Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text[:2500] # Safe clamp