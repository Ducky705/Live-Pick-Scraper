
import json
import os
import sys
from collections import Counter

def main():
    cache_path = "src/data/picks_cache_2026-02-05.json"
    if not os.path.exists(cache_path):
        print(f"File not found: {cache_path}")
        return

    with open(cache_path, 'r') as f:
        data = json.load(f)
    
    # Handle list vs dict structure
    if isinstance(data, dict):
        picks = data.get("picks", [])
    else:
        picks = data # Root list

    total = len(picks)
    print(f"Total Extracted Picks: {total}")
    
    # Count Grades
    grades = Counter(p.get("grade", "UNKNOWN") for p in picks)
    
    graded_count = grades["WIN"] + grades["LOSS"] + grades["PUSH"] + grades["VOID"]
    graded_pct = (graded_count / total * 100) if total else 0
    
    print(f"\n--- Grading Status ---")
    print(f"GRADED (W/L/P/V): {graded_count} ({graded_pct:.1f}%)")
    print(f"PENDING: {grades['PENDING']} ({grades['PENDING'] / total * 100:.1f}%)")
    print(f"ERROR: {grades['ERROR']} ({grades['ERROR'] / total * 100:.1f}%)")
    print("-" * 20)
    for k, v in grades.items():
        print(f"{k}: {v}")

    # Analyze Pending
    print(f"\n--- Top Pending Reasons ---")
    pending_reasons = []
    for p in picks:
        if p.get("grade") == "PENDING":
            reason = p.get("grading_details", "") or p.get("grading_error", "Unknown")
            pending_reasons.append(reason)
            
    # Group similar reasons (simple truncation)
    clean_reasons = [r.split(":")[0] if ":" in r else r for r in pending_reasons]
    # Further cleanup common starts
    clean_reasons = [
        "Stat not found" if "Stat" in r and "not found" in r else
        "Could not resolve team" if "Could not resolve" in r else
        r for r in clean_reasons
    ]
            
    for r, count in Counter(clean_reasons).most_common(10):
        print(f"{count}x : {r}")
        
    print(f"\n--- 'Game not found' League Breakdown ---")
    game_not_found = [p for p in picks if "Game not found" in str(p.get("grading_details", ""))]
    leagues = Counter(p.get("league", "Unknown") for p in game_not_found)
    for l, c in leagues.most_common():
        print(f"{l}: {c}")

if __name__ == "__main__":
    main()
