import requests
import json

def check_conferences():
    # IDs from score_fetcher.py
    group_ids = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "12", "13", "15", "16", "17", "18", "19", "20",
    "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
    "31", "32", "62", "59", "100", "151"
    ]
    
    print(f"Checking {len(group_ids)} conference IDs...")
    
    # We can check a sample scoreboard for a group to see the league name
    # But names are often just "NCAA Men's Basketball"
    # Better to check if Navy (Patriot) or FAU (AAC) are in these groups for a known date.
    
    # Navy is in Patriot League.
    # FAU is in AAC (American Athletic Conference).
    
    # Let's try to find their teams in the groups on a busy day like Sat Feb 3rd 2024?
    # Or just today? Let's use 20240217 (Sat)
    
    date = "20240217" 
    
    found_navy = False
    found_fau = False
    
    for gid in group_ids:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={date}&groups={gid}&limit=100"
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            events = data.get("events", [])
            for evt in events:
                name = evt.get("name", "")
                if "Navy" in name:
                    print(f"FOUND NAVY in Group {gid}: {name}")
                    found_navy = True
                if "Florida Atlantic" in name or "FAU" in name:
                    print(f"FOUND FAU in Group {gid}: {name}")
                    found_fau = True
        except Exception as e:
            print(f"Error checking group {gid}: {e}")
            
    if not found_navy:
        print("WARNING: Navy NOT found in configured groups.")
    if not found_fau:
        print("WARNING: FAU NOT found in configured groups.")

if __name__ == "__main__":
    check_conferences()
