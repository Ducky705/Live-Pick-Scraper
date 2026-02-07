import json
import os
from collections import Counter

def main():
    cache_path = "src/data/picks_cache_2026-02-05.json"
    if not os.path.exists(cache_path):
        print(f"File not found: {cache_path}")
        return

    with open(cache_path, 'r') as f:
        data = json.load(f)
    picks = data.get("picks", []) if isinstance(data, dict) else data

    pending = [p for p in picks if p.get("grade") == "PENDING"]
    total_pending = len(pending)
    print(f"Total Pending Picks: {total_pending}")

    reasons = Counter()
    leagues = Counter()
    teams_not_found = []
    
    for p in pending:
        details = p.get("grading_details", "No details")
        reasons[details] += 1
        leagues[p.get("league", "UNKNOWN")] += 1
        
        if "resolve team" in details or "not found" in details:
            teams_not_found.append({
                "pick": p.get("pick"),
                "league": p.get("league"),
                "details": details,
                "msg_id": p.get("message_id")
            })

    print("\nFailure Reasons Breakdown:")
    for reason, count in reasons.most_common():
        print(f"  {count}: {reason}")

    print("\nLeagues Affecting Pending Picks:")
    for league, count in leagues.most_common():
        print(f"  {count}: {league}")

    print("\nSample 'Game Not Found' / 'Resolve Team' Issues (Top 20):")
    for item in teams_not_found[:20]:
        print(f"  [{item['league']}] {item['pick']} -> {item['details']}")

if __name__ == "__main__":
    main()
