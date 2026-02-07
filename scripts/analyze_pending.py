import json
from collections import Counter

def analyze_pending():
    path = "src/data/picks_cache_2026-02-05.json"
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        picks = data.get("picks", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"Error loading cache: {e}")
        return

    pending = [p for p in picks if p.get("grade") == "PENDING"]
    total = len(picks)
    print(f"Total Picks: {total}")
    print(f"Pending Picks: {len(pending)} ({len(pending)/total:.1%})")

    # 1. By League
    leagues = Counter(p.get("league", "Unknown") for p in pending)
    print("\n--- By League ---")
    for l, c in leagues.most_common(5):
        print(f"{l}: {c}")

    # 2. By Bet Type (if inferred from text)
    print("\n--- By Pattern (Heuristic) ---")
    patterns = Counter()
    for p in pending:
        text = p.get("pick", "").lower() + " " + p.get("selection", "").lower()
        if "over" in text or "under" in text:
            if "points" in text or "rebounds" in text or "assists" in text or "pra" in text:
                patterns["Player Prop"] += 1
            else:
                patterns["Total (Over/Under)"] += 1
        elif "1h" in text or "2h" in text or "1p" in text or "q1" in text:
            patterns["Period/Live"] += 1
        elif "+" in text or "-" in text:
            patterns["Spread/ML"] += 1
        else:
            patterns["Other"] += 1

    for pat, c in patterns.most_common():
        print(f"{pat}: {c}")
        
    # 3. Sample of 'Other'
    print("\n--- Sample 'Other' / Hard Failures ---")
    others = [p for p in pending if "Player Prop" not in p.get("type", "")]
    for p in others[:5]:
        print(f"[{p.get('league')}] {p.get('pick')}")

if __name__ == "__main__":
    analyze_pending()
