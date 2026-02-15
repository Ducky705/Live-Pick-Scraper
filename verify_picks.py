
import json
import os
import re
from collections import defaultdict

# Configuration
OUTPUT_DIR = r"d:\Programs\Sports Betting\TelegramScraper\v0.0.15\src\data\output"
DATE = "2026-02-14"
RAW_FILE = os.path.join(OUTPUT_DIR, "debug_msgs.json")
PICKS_FILE = os.path.join(OUTPUT_DIR, f"picks_{DATE}_manual.json") # Using manual file
REPORT_FILE = os.path.join(OUTPUT_DIR, f"recall_analysis_{DATE}.md")

# Keywords that suggest a pick
PICK_KEYWORDS = [
    r"\b(over|under)\b",
    r"\b(moneyline|ml)\b",
    r"\b(spread)\b",
    r"\b(-|\+)\d{3}\b", # American odds
    r"\b(u|o)\s?(\d+\.?\d*)\b", # Over/Under short
    r"\batts?\b", # Anytime TD
    r"\b(prop)\b",
    r"\b(parlay)\b"
]

def load_json(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def has_pick_keywords(text):
    if not text:
        return False
    text = text.lower()
    for pattern in PICK_KEYWORDS:
        if re.search(pattern, text):
            return True
    return False

def main():
    print(f"Loading data from {OUTPUT_DIR}...")
    raw_msgs = load_json(RAW_FILE)
    picks = load_json(PICKS_FILE)
    
    print(f"Loaded {len(raw_msgs)} raw messages.")
    print(f"Loaded {len(picks)} extracted picks.")

    # Map extracted picks to source message IDs
    extracted_msg_ids = set()
    for p in picks:
        # Check all possible ID fields and normalize to string
        mid = p.get("message_id") or p.get("source_msg_id")
        if mid is not None:
            extracted_msg_ids.add(str(mid))
    
    print(f"Messages with extracted picks: {len(extracted_msg_ids)}")

    # Analyze missed messages
    missed_msgs = []
    
    for msg in raw_msgs:
        msg_id = msg.get("id")
        if msg_id is None:
            continue
            
        # Normalize to string
        msg_id_str = str(msg_id)
        
        text = msg.get("text", "") or ""
        ocr = msg.get("ocr_text", "") or ""
        full_text = text + "\n" + ocr
        
        if msg_id_str not in extracted_msg_ids:
            # Check if it looks like a pick
            if has_pick_keywords(full_text):
                missed_msgs.append({
                    "id": msg_id,
                    "text": full_text.strip()[:500], # Truncate for report
                    "source": msg.get("source", "unknown")
                })

    print(f"Found {len(missed_msgs)} missed messages with potential picks.")

    # Generate Report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Recall Analysis for {DATE}\n\n")
        f.write(f"- **Total Raw Messages**: {len(raw_msgs)}\n")
        f.write(f"- **Total Extracted Picks**: {len(picks)}\n")
        f.write(f"- **Messages with Picks**: {len(extracted_msg_ids)}\n")
        f.write(f"- **Potential Missed Messages**: {len(missed_msgs)}\n\n")
        
        f.write("## Missed Messages (Potential False Negatives)\n\n")
        for m in missed_msgs:
            f.write(f"### Msg {m['id']} ({m['source']})\n")
            f.write(f"```\n{m['text']}\n```\n\n")
    
    print(f"Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    main()
