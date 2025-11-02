# File: ./standardizer.py
import re
from thefuzz import process as fuzz_process
from config import LEAGUE_STANDARDS, BET_TYPE_STANDARDS

def get_standardized_value(input_string: str, standards_map: dict, fallback_key: str) -> str:
    """Uses fuzzy matching to map a potentially messy input string to a standardized code."""
    if not input_string:
        return standards_map.get(fallback_key.upper(), 'Unknown')

    normalized_input = input_string.upper().strip()
    
    if normalized_input in standards_map:
        return standards_map[normalized_input]

    if normalized_input in standards_map.values():
        return normalized_input

    keys_to_match = list(standards_map.keys())
    if not keys_to_match:
        return standards_map.get(fallback_key.upper(), 'Unknown')
        
    best_match_key, score = fuzz_process.extractOne(normalized_input, keys_to_match)
    
    if score >= 85:
        return standards_map[best_match_key]
    
    return standards_map.get(fallback_key.upper(), 'Unknown')

def clean_unit_value(unit_input: any) -> float:
    """Cleans the 'unit' value, extracting a float or returning a default."""
    default_unit = 1.0
    if isinstance(unit_input, (int, float)):
        return float(unit_input)
    if not isinstance(unit_input, str) or not unit_input:
        return default_unit
    
    # --- FIX: Update regex to accept comma OR dot as decimal separator ---
    match = re.search(r'(\d+[\.,]?\d*)', unit_input.strip())
    if match:
        try:
            # Always replace comma with dot before converting to float
            unit_str = match.group(1).replace(',', '.')
            return float(unit_str)
        except (ValueError, TypeError):
            return default_unit
    return default_unit