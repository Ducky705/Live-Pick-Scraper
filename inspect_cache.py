
import json
import os

cache_path = os.path.join("data", "output", "extraction_cache.json")

print(f"Loading cache from {cache_path}")
try:
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("Cache file not found.")
    exit(1)

# Look for key matching ['10891']
key = "['10891']"
if key in data:
    print(f"Found entry for {key}:")
    print(json.dumps(data[key], indent=2))
else:
    print(f"No entry found for {key}")

# Also try integer key just in case (though signature is stringified list of strings)
# But wait, signature is strictly sorted list of strings.
# So "['10891']" is correct.
