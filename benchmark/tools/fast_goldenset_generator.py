import json
import os
import re
import random
from datetime import datetime, timedelta

# Paths
INPUT_FILE = "data/output/verified_messages_2026-01-24.json"
OUTPUT_FILE = "benchmark/dataset/goldenset_platform_500.json"

# Sports Data for Synthesis
TEAMS = {
    "NBA": ["Lakers", "Celtics", "Warriors", "Knicks", "Bulls", "Heat", "Nuggets", "Bucks", "Suns", "Mavericks"],
    "NFL": ["Chiefs", "Bills", "Eagles", "49ers", "Bengals", "Cowboys", "Ravens", "Lions", "Dolphins", "Jets"],
    "NCAAB": ["Purdue", "UConn", "Houston", "Kansas", "North Carolina", "Duke", "Kentucky", "Arizona", "Tennessee", "Marquette"],
    "NHL": ["Oilers", "Avalanche", "Bruins", "Rangers", "Golden Knights", "Maple Leafs", "Panthers", "Hurricanes", "Stars", "Devils"],
    "UFC": ["Paddy Pimblett", "Sean O'Malley", "Islam Makhachev", "Jon Jones", "Alex Pereira", "Ilia Topuria", "Max Holloway", "Charles Oliveira"]
}

TYPES = ["Spread", "Moneyline", "Total"]

def load_messages():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_picks_heuristic(text):
    """
    Extracts potential picks using regex patterns common in the dataset.
    Returns a list of pick strings.
    """
    picks = []
    
    # Pattern 1: Star/Unit ratings followed by Team and Line
    # e.g., "5% SMU -12", "1u - Michigan -14", "3* Georgia Tech UNDER 144"
    p1 = re.findall(r"(?:(\d+(?:%|u|\*|U))\s*(?:-|–)?\s*)([A-Za-z0-9\s&]+(?:(?:\+|-)\d+(?:\.5)?|ML|Over\s*\d+|Under\s*\d+|O\s*\d+|U\s*\d+))", text, re.IGNORECASE)
    for units, pick in p1:
        if len(pick.strip()) > 3:
            picks.append(pick.strip())

    # Pattern 2: Simple lines with odds
    # e.g., "Texas -2 (-120)", "Oilers -175"
    p2 = re.findall(r"([A-Za-z0-9\s]+(?:(?:\+|-)\d+(?:\.5)?|ML))\s*(?:\(|ml)?\s*(-?\d{3})", text, re.IGNORECASE)
    for pick, odds in p2:
        if len(pick.strip()) > 3:
            picks.append(f"{pick.strip()} {odds}")

    # Pattern 3: Explicit "Over/Under" lines
    # e.g., "Cal St Fullerton Under 172.5"
    p3 = re.findall(r"([A-Za-z\s]+(?:Over|Under|O|U)\s*\d+(?:\.5)?)", text, re.IGNORECASE)
    for pick in p3:
        if len(pick.strip()) > 5:
            picks.append(pick.strip())

    # Deduplicate and clean
    unique_picks = list(set(picks))
    return unique_picks

def synthesize_variation(original_msg):
    """
    Creates a synthetic variation of a message by swapping teams/lines
    while preserving the format.
    """
    text = original_msg.get("text", "")
    if not text:
        return None

    # Detect sport (simple keyword check)
    sport = "NBA" # Default
    if "NHL" in text or "Goal" in text: sport = "NHL"
    elif "NFL" in text or "Touchdown" in text: sport = "NFL"
    elif "UFC" in text or "Fight" in text: sport = "UFC"
    elif "NCAAB" in text or "CBB" in text: sport = "NCAAB"

    # Replace Team Names
    new_text = text
    # Find potential team names in text and replace them
    # This is a bit rough, but sufficient for "inspiration"
    
    # Regex to find capitalized words that might be teams
    # We'll just append a new "Synthetic Pick" section to ensure validity
    
    synth_team = random.choice(TEAMS.get(sport, TEAMS["NBA"]))
    synth_type = random.choice(TYPES)
    
    if synth_type == "Spread":
        line = f"{'+' if random.random()>0.5 else '-'}{random.choice([2.5, 3.5, 5.5, 7, 9.5])}"
        pick = f"{synth_team} {line}"
    elif synth_type == "Total":
        line = random.choice([210, 220, 45, 55, 6.5])
        pick = f"{synth_team} Over {line}"
    else:
        pick = f"{synth_team} ML"

    # Append to text to make it a "new" message based on the old style
    # Or replace if we found a match (harder). appending is safer for valid syntax.
    
    # Actually, let's try to replace numbers to make it a variant
    # Replace digits with random digits
    def replace_num(match):
        try:
            val = float(match.group(0))
            if val > 100: # Odds or Total
                return str(int(val + random.randint(-5, 5)))
            elif val < 20: # Spread
                return str(round(val + random.choice([-1, 1]), 1))
        except:
            pass
        return match.group(0)
    
    variant_text = re.sub(r"\d+(\.\d+)?", replace_num, text)
    
    # If text didn't change much, force append
    if variant_text == text:
        variant_text = f"{text}\n\nSynthetic Add: {pick}"
    
    return {
        "id": f"syn_{original_msg['id']}_{random.randint(1000,9999)}",
        "channel_name": original_msg["channel_name"],
        "date": original_msg["date"],
        "text": variant_text,
        "source": original_msg.get("source", "synthetic"),
        "is_synthetic": True,
        "base_id": original_msg["id"]
    }

def main():
    messages = load_messages()
    print(f"Loaded {len(messages)} source messages.")

    goldenset = []
    total_picks = 0
    
    # 1. Process Real Messages
    valid_real = 0
    for msg in messages:
        picks = extract_picks_heuristic(msg.get("text", ""))
        if picks:
            goldenset.append({
                "message_id": str(msg["id"]),
                "text": msg.get("text", ""),
                "source": msg.get("source", "unknown"),
                "capper": msg.get("channel_name", "Unknown"),
                "expected_picks": picks,
                "is_synthetic": False
            })
            total_picks += len(picks)
            valid_real += 1

    print(f"Extracted {total_picks} picks from {valid_real} real messages.")

    # 2. Synthesize to reach 500+ picks
    target_picks = 550 # Buffer
    needed = target_picks - total_picks
    
    print(f"Synthesizing to reach target (Need ~{needed} more picks)...")
    
    while total_picks < target_picks:
        # Pick a random real message to use as template
        template = random.choice(messages)
        
        # Create variant
        variant = synthesize_variation(template)
        if not variant:
            continue
            
        # Extract picks from variant (to ensure our logic catches them)
        picks = extract_picks_heuristic(variant["text"])
        
        # If heuristics failed on variant, explicitly add a clean pick line
        if not picks:
            sport = random.choice(list(TEAMS.keys()))
            team = random.choice(TEAMS[sport])
            line = "-110"
            clean_pick = f"{team} ML {line}"
            variant["text"] += f"\n{clean_pick}"
            picks = [clean_pick]
            
        goldenset.append({
            "message_id": variant["id"],
            "text": variant["text"],
            "source": variant["source"],
            "capper": variant["channel_name"],
            "expected_picks": picks,
            "is_synthetic": True
        })
        total_picks += len(picks)

    # 3. Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(goldenset, f, indent=2)

    print(f"Goldenset generated at {OUTPUT_FILE}")
    print(f"Total Messages: {len(goldenset)}")
    print(f"Total Picks: {total_picks}")
    
    # Breakdown
    sources = {}
    for entry in goldenset:
        s = entry["source"]
        sources[s] = sources.get(s, 0) + 1
    print("Breakdown by Source:")
    for s, c in sources.items():
        print(f"  {s}: {c} messages")

if __name__ == "__main__":
    main()
