
import json
from collections import Counter
import re

def analyze_accuracy():
    input_file = "src/data/output/picks_2026-02-14_manual.json"
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            picks = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {input_file}")
        return

    print(f"Analyzing {len(picks)} picks from {input_file}...")

    results = Counter()
    void_reasons = Counter()
    unknown_leagues = Counter()
    
    suspicious_voids = []

    for p in picks:
        res = p.get("result", "Unknown")
        results[res] += 1
        
        if res == "Void":
            reason = p.get("score_summary", "No reason provided")
            # Simplify reason for grouping
            if "Invalid: No betting structure" in reason:
                reason_key = "Invalid Structure"
            elif "not a known team alias" in reason:
                reason_key = "Unknown Alias"
            elif "Ambiguous" in reason:
                reason_key = "Ambiguous Team"
            else:
                reason_key = reason[:50] + "..."
            
            void_reasons[reason_key] += 1
            
            # Check for suspicious voids (looks like a real pick)
            pick_text = p.get("pick", "")
            if len(pick_text) > 5 and any(c.isdigit() for c in pick_text):
                 suspicious_voids.append((pick_text, reason))

        if res == "Unknown":
             unknown_leagues[p.get("league", "N/A")] += 1

    print("\n--- Result Distribution ---")
    for r, c in results.most_common():
        print(f"{r}: {c}")

    print("\n--- Void Reasons ---")
    for r, c in void_reasons.most_common(10):
        print(f"{c}x {r}")

    print("\n--- Suspicious Voids (Sample) ---")
    for i, (pt, r) in enumerate(suspicious_voids[:10]):
        print(f"{i+1}. '{pt}' -> {r}")

    print("\n--- Unknown Results by League ---")
    for l, c in unknown_leagues.most_common():
        print(f"{l}: {c}")

if __name__ == "__main__":
    analyze_accuracy()
