
import json
import os

results_path = os.path.join("data", "output", "debug_loop_results.json")

if not os.path.exists(results_path):
    print("Results file not found.")
    exit(1)

with open(results_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total Picks: {len(data)}")

# Count by Grade
grades = {}
for p in data:
    g = p.get("grade", "Pending")
    grades[g] = grades.get(g, 0) + 1

print("Grades Breakdown:")
for g, count in grades.items():
    print(f"  {g}: {count}")

# Check for specific "Pats" pick
pats_picks = [p for p in data if "Pats" in str(p)]
print(f"\nPicks mentioning 'Pats': {len(pats_picks)}")
for p in pats_picks:
    print(f"  - Msg {p.get('message_id')}: {p.get('pick')} (Grade: {p.get('grade')})")

# Check for Message 10891
msg_10891 = [p for p in data if str(p.get("message_id")) == "10891"]
print(f"\nPicks for Message 10891: {len(msg_10891)}")
