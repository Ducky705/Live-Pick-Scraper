
import requests
import json
import ssl
import sys
import os

# Disable SSL verification warnings
requests.packages.urllib3.disable_warnings()

def fetch_nba_boxscore():
    # Fetch scoreboard to get a game ID
    date_str = "20260205" # Date from the dry run
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}&limit=5"
    
    print(f"Fetching scoreboard from {url}")
    resp = requests.get(url, verify=False)
    data = resp.json()
    
    events = data.get("events", [])
    if not events:
        print("No events found.")
        return

    # Pick the first game (likely Magic vs Lakers or similar)
    game_id = events[0]['id']
    name = events[0]['name']
    print(f"Fetching boxscore for {name} (ID: {game_id})")
    
    box_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    box_resp = requests.get(box_url, verify=False)
    box_data = box_resp.json()
    
    boxscore = box_data.get("boxscore", {})
    
    # Print keys
    print("Boxscore Keys:", list(boxscore.keys()))
    
    if "players" in boxscore:
        players_group = boxscore["players"]
        print(f"Players Group Count: {len(players_group)}")
        if players_group:
            first_group = players_group[0]
            print("First Group Keys:", list(first_group.keys()))
            if "statistics" in first_group:
                stats_list = first_group["statistics"]
                print(f"Statistics Categories: {len(stats_list)}")
                if stats_list:
                    first_stat_cat = stats_list[0]
                    print("First Stat Category Keys:", list(first_stat_cat.keys()))
                    print("Labels:", first_stat_cat.get("names", [])[:5])
                    
                    if "athletes" in first_stat_cat:
                        athletes = first_stat_cat["athletes"]
                        print(f"Athletes count: {len(athletes)}")
                        if athletes:
                            first_athlete = athletes[0]
                            print("First Athlete Keys:", list(first_athlete.keys()))
                            print("First Athlete DisplayName:", first_athlete.get("athlete", {}).get("displayName"))
                            print("First Athlete Stats:", first_athlete.get("stats", [])[:5])

if __name__ == "__main__":
    fetch_nba_boxscore()
