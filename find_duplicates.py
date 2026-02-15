
import json
import os
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

with open(os.path.join("data", "output", "comprehensive_debug_set.json"), "r", encoding="utf-8") as f:
    msgs = json.load(f)

target = next((m for m in msgs if str(m.get("id")) == "10891"), None)
target_text = target.get("text", "") + "\n" + "\n".join(target.get("ocr_texts", []))

print(f"Target Text Len: {len(target_text)}")

candidates = []
for m in msgs:
    if str(m.get("id")) == "10891": continue
    
    text = m.get("text", "") + "\n" + "\n".join(m.get("ocr_texts", []))
    sim = similar(target_text, text)
    if sim > 0.8: # High similarity
        candidates.append((m.get("id"), sim))

print("Duplicates found:")
for mid, sim in candidates:
    print(f" - {mid} (Sim: {sim:.2f})")
