
import time
import requests
import json
import statistics

API_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
CDN_URL = "https://cdn.espn.com/core/nba/scoreboard?xhr=1"

def test_endpoint(url, name, headers=None):
    times = []
    data_size = 0
    event_count = 0
    
    print(f"Testing {name}...")
    for i in range(5):
        start = time.time()
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            duration = (time.time() - start) * 1000
            times.append(duration)
            
            if i == 0:
                data = resp.json()
                if name == "CDN":
                     # CDN structure can be slightly different, it wraps content in 'content' sometimes or returns direct
                     # The structure for scoreboard?xhr=1 is usually:
                     # { sports: [ ... ] } matching the API
                     pass
                
                # Check event count
                events = data.get('events', [])
                if not events and 'content' in data:
                     # Handle possible CDN wrapper
                     pass
                
                event_count = len(events)
                data_size = len(resp.content)
                
        except Exception as e:
            print(f"  Request failed: {e}")

    avg_time = statistics.mean(times)
    print(f"  Avg Time: {avg_time:.2f}ms")
    print(f"  Data Size: {data_size} bytes")
    print(f"  Events Found: {event_count}")
    return avg_time, event_count

def main():
    print("--- Comparing API vs CDN ---")
    
    api_time, api_count = test_endpoint(API_URL, "Standard API")
    cdn_time, cdn_count = test_endpoint(CDN_URL, "CDN")
    
    print("\n--- Results ---")
    print(f"Speed Improvement: {(api_time - cdn_time):.2f}ms faster")
    print(f"Data Parity: {'MATCH' if api_count == cdn_count else 'MISMATCH'}")

if __name__ == "__main__":
    main()
