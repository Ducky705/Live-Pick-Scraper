
import json
import os

results_path = os.path.join("data", "output", "debug_loop_results.json")
with open(results_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Check for Message 12793
msg_12793 = [p for p in data if str(p.get("message_id")) == "12793"]
print(f"Picks for Message 12793: {len(msg_12793)}")

# Check for Capper "Big Al"
big_al = [p for p in data if "Big Al" in str(p.get("capper_name"))]
print(f"Picks for Capper 'Big Al': {len(big_al)}")
if big_al:
    print(f"Sample Big Al Pick Msg ID: {big_al[0].get('message_id')}")
