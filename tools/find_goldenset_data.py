
import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root
sys.path.append(os.getcwd())

from src.grading.loader import DataLoader

# Setup logging
logging.basicConfig(level=logging.INFO)

def find_data():
    # Wider Scan: Jan 15 to Feb 15, 2026
    start_date = datetime(2026, 1, 15)
    dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(32)]
    
    # Focus on missing leagues
    leagues = [
        "tennis", "ufc", "pfl",        
        "rugby", "cricket", "boxing"   
    ]
    
    print(f"Scanning dates {dates[0]} to {dates[-1]} for {len(leagues)} leagues...")
    
    hits = {lg: [] for lg in leagues}
    
    for date in dates:
        print(f"\nChecking {date}...")
        try:
            scores = DataLoader.fetch_scores([date], leagues)
            
            # Count per league
            counts = {lg: 0 for lg in leagues}
            for g in scores:
                lg = g.get("league")
                if lg in counts:
                    counts[lg] += 1
            
            for lg, count in counts.items():
                if count > 0:
                    hits[lg].append(date)
                    print(f"  ✅ {lg.upper()}: {count} games")
        except Exception as e:
            print(f"  Error fetching {date}: {e}")

    print("\n--- Summary of Available Dates ---")
    for lg, valid_dates in hits.items():
        if valid_dates:
            print(f"{lg.upper()}: {valid_dates}")
        else:
            print(f"{lg.upper()}: NO GAMES FOUND ❌ (Need to check other dates?)")

if __name__ == "__main__":
    find_data()
