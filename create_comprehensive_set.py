import json
import os
import shutil
from typing import Any

# CONFIG
OUTPUT_DIR = "data/output"
DEBUG_FILE = os.path.join(OUTPUT_DIR, "debug_msgs.json")
VERIFIED_FILE = os.path.join(OUTPUT_DIR, "verified_messages_2026-01-24.json")
TARGET_FILE = os.path.join(OUTPUT_DIR, "comprehensive_debug_set.json")

def load_json(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        print(f"Warning: File not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    print(f"Loading {DEBUG_FILE}...")
    debug_msgs = load_json(DEBUG_FILE)
    print(f"Loaded {len(debug_msgs)} debug messages.")

    print(f"Loading {VERIFIED_FILE}...")
    verified_msgs = load_json(VERIFIED_FILE)
    print(f"Loaded {len(verified_msgs)} verified messages.")

    # Merge and Dedup by ID
    merged_map = {}
    
    # Process Debug Msgs first
    for m in debug_msgs:
        mid = str(m.get("id"))
        merged_map[mid] = m

    # Process Verified Msgs (Overwrite if exists? Or keep debug? Let's keep debug as it might be fresher)
    # Actually, verified set is older. Let's trust debug set for overlap.
    for m in verified_msgs:
        mid = str(m.get("id"))
        if mid not in merged_map:
            merged_map[mid] = m
            # Ensure fields exist
            if "ocr_text" not in m:
                m["ocr_text"] = ""
            if "text" not in m:
                m["text"] = ""

    merged_list = list(merged_map.values())
    print(f"Total Unique Messages: {len(merged_list)}")

    print(f"Saving to {TARGET_FILE}...")
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_list, f, indent=2)
    
    print("Done!")

if __name__ == "__main__":
    main()
