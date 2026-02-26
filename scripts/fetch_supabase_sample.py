import os
import json
import random
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(url, key)

print("Fetching a sample of 50 picks from the database...")

# Fetch up to 1000 recent picks to sample from (recent date range)
try:
    response = supabase.table("picks").select("*").order("created_at", desc=True).limit(500).execute()
    
    data = response.data
    if not data:
        print("No data found in Supabase!")
        exit(1)
        
    print(f"Successfully retrieved {len(data)} recent records from Supabase.")
    
    # Take a random sample of 50
    sample_size = min(50, len(data))
    sample = random.sample(data, sample_size)
    
    # Save the sample to a file for review
    output_path = os.path.join("data", "output", "supabase_sample.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2)
        
    print(f"Saved {sample_size} random records to {output_path} for review.")
    
    # Print a quick summary of a few items
    print("\n--- SAMPLE PREVIEW (First 3) ---")
    for pick in sample[:3]:
        print(f"Date: {pick.get('pick_date')} | Capper: {pick.get('capper_id')} | Pick: {pick.get('pick')} | Result: {pick.get('result')}")

except Exception as e:
    print(f"Error fetching from Supabase: {e}")
