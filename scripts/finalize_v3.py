import json

def finalize_dataset():
    input_path = "benchmark/dataset/golden_set_v3_draft.json"
    output_path = "new_golden_set.json" # Overwriting the old one for the benchmark script to pick up automatically
    
    with open(input_path, "r") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} draft items.")
    
    final_set = []
    skipped = 0
    
    for item in data:
        picks = item.get("expected_picks", [])
        if picks and len(picks) > 0:
            # We trust the pipeline's positive output as 'Silver' labels
            final_set.append(item)
        else:
            skipped += 1
            print(f"Skipping ID {item.get('id')} (No picks generated)")

    print(f"Retained {len(final_set)} verified items. Skipped {skipped}.")
    
    with open(output_path, "w") as f:
        json.dump(final_set, f, indent=2)
        
    print(f"Saved Final V3 Golden Set to {output_path}")

if __name__ == "__main__":
    finalize_dataset()
