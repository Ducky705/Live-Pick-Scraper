import json
import random
import os

def create_v3_candidate():
    source_path = "benchmark/dataset/goldenset_platform_500.json"
    target_path = "benchmark/dataset/golden_set_v3_candidates.json"
    
    if not os.path.exists(source_path):
        print(f"Source not found: {source_path}")
        return

    with open(source_path, "r") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} items from source.")
    
    # Filter for diversity (Telegram vs Discord vs Twitter)
    telegram = [d for d in data if d.get("source", "").lower() == "telegram"]
    discord = [d for d in data if d.get("source", "").lower() == "discord"]
    twitter = [d for d in data if d.get("source", "").lower() == "twitter"]
    
    print(f"Stats: Telegram={len(telegram)}, Discord={len(discord)}, Twitter={len(twitter)}")
    
    # Sample 15 from each
    selected = []
    selected.extend(random.sample(telegram, min(20, len(telegram))))
    selected.extend(random.sample(discord, min(15, len(discord))))
    selected.extend(random.sample(twitter, min(15, len(twitter))))
    
    # Clean up fields mapping
    # The extraction pipeline expects "id" and "text"
    final_set = []
    for item in selected:
        new_item = {
            "id": item.get("message_id"),
            "source": item.get("source"),
            "text": item.get("text"),
            "expected_picks": [] # Reset expected picks for re-verification
        }
        final_set.append(new_item)
        
    with open(target_path, "w") as f:
        json.dump(final_set, f, indent=2)
        
    print(f"Created {target_path} with {len(final_set)} candidates.")

if __name__ == "__main__":
    create_v3_candidate()
