import json
import os
from collections import Counter

file_path = "d:/Programs/Sports Betting/TelegramScraper/v0.0.15/data/output/picks_2026-02-16.json"

if not os.path.exists(file_path):
    print("File not found.")
    exit()

with open(file_path, "r") as f:
    data = json.load(f)

total_picks = 0
results = Counter()
sports = Counter()
cappers = Counter()
bet_types = Counter()

# The file likely contains a list of Message objects, each with a 'picks' list
# OR a flat list of picks? 
# Looking at previous view_file output (Step 491), it looks like a list of Message objects, 
# where each item has a "picks" key (list) AND top-level fields like "result".
# Wait, Step 491 showed:
# [
#   {
#     "message_id": "...",
#     "picks": [ { "selection": "Iowa State ML", ... } ],
#     "result": "Error", ...
#   }
# ]
# So it's a list of MESSAGES. The "picks" inside are the actual picks.
# The top-level "result" seems to be an aggregate or error flag for the message processing.

messages_count = len(data)
msgs_with_error = 0

for msg in data:
    if msg.get("result") == "Error":
        msgs_with_error += 1
    
    msg_picks = msg.get("picks", [])
    if isinstance(msg_picks, list):
        for p in msg_picks:
            total_picks += 1
            sports[p.get("sport", "Unknown")] += 1
            cappers[p.get("capper_name", "Unknown")] += 1
            bet_types[p.get("bet_type", "Unknown")] += 1
            # Check if pick itself has a result?
            # The structure in Step 491 showed picks having "selection", "odds", etc.
            # Did picks have "result"? Use .get()
            results[p.get("result", "Pending")] += 1

print(f"Total Messages Processed: {messages_count}")
print(f"Messages with Error Status: {msgs_with_error}")
print("-" * 30)
print(f"Total Extracted Picks: {total_picks}")
print("-" * 30)
print("Sports Distribution:")
for k, v in sports.most_common():
    print(f"  {k}: {v}")
print("-" * 30)
print("Top 5 Cappers:")
for k, v in cappers.most_common(5):
    print(f"  {k}: {v}")
print("-" * 30)
print("Grading Status:")
for k, v in results.most_common():
    print(f"  {k}: {v}")
