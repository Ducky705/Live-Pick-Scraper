import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.supabase_client import upload_picks

def main():
    json_path = os.path.join("data", "output", "picks_2026-01-24.json")
    if not os.path.exists(json_path):
        print("JSON file not found.")
        return 1

    with open(json_path, 'r', encoding='utf-8') as f:
        picks = json.load(f)

    print(f"Loaded {len(picks)} picks. Uploading to Supabase...")
    res = upload_picks(picks, target_date="2026-01-24")
    
    if res.get("success"):
        print(f"Successfully uploaded/updated {res.get('count')} picks.")
    else:
        print(f"Failed to upload. Error: {res.get('error') or res.get('details')}")

if __name__ == "__main__":
    main()
