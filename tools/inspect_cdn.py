
import requests
import json

CDN_URL = "https://cdn.espn.com/core/nba/scoreboard?xhr=1"

print("Fetching CDN data...")
try:
    resp = requests.get(CDN_URL, timeout=10)
    data = resp.json()
    
    print("Top level keys:", list(data.keys()))
    
    if 'content' in data:
        print("'content' keys:", list(data['content'].keys()))
        if 'sbData' in data['content']:
             print("'sbData' keys:", list(data['content']['sbData'].keys()))
             events = data['content']['sbData'].get('events', [])
             print(f"Events found in content.sbData: {len(events)}")
    
    if 'sports' in data:
        print("'sports' structure found (like API)")
        
except Exception as e:
    print(f"Failed: {e}")
