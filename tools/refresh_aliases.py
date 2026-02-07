
import requests
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.score_fetcher import LEAGUES_TO_SCRAPE

OUTPUT_FILE = "src/team_aliases.py"

# Manual overrides or additions to ensure we don't lose custom knowledge
MANUAL_ALIASES = {
    "golden state warriors": ["dub nation", "dubs"],
    "los angeles lakers": ["purple and gold"],
    # Add other know custom aliases that API won't provide
}

def normalize_key(name):
    return name.lower().strip()

def fetch_teams(sport, league):
    """Fetch teams from ESPN API for a given sport/league."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams?limit=1000"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        teams_data = []
        if "sports" in data:
            for s in data["sports"]:
                for l in s.get("leagues", []):
                    for t in l.get("teams", []):
                        teams_data.append(t.get("team", {}))
        return teams_data
    except Exception as e:
        print(f"Error fetching {sport}/{league}: {e}")
        return []

def generate_aliases():
    print("Fetching team data from ESPN...")
    
    all_aliases = {}
    
    # Iterate over all leagues defined in our system
    for sport, leagues in LEAGUES_TO_SCRAPE.items():
        for league_key, league_name in leagues.items():
            print(f"  Processing {league_name} ({sport}/{league_key})...")
            teams = fetch_teams(sport, league_key)
            
            for team in teams:
                # Extract relevant fields
                display_name = team.get("displayName", "")
                short_name = team.get("shortDisplayName", "")
                name = team.get("name", "") # Often the "mascot" part ex: "Lakers"
                abbr = team.get("abbreviation", "")
                location = team.get("location", "")
                nickname = team.get("nickname", "")
                
                if not display_name:
                    continue
                    
                # The key for our alias map should be the full display name (lowercase)
                # or simpler if preferred. The current system seems to use specific keys.
                # Let's try to infer a canonical key. usually "nickname" or full name.
                # Looking at existing generic file, keys like "lakers" or "los angeles lakers".
                # We will use the full display name as canonical to be safe, OR match existing pattern.
                # Existing pattern seems to mix: "lakers" (mascot) and "los angeles lakers" (full)
                
                # We'll use the full displayName lowercased as valid key, 
                # AND the nickname as a valid key if it's unique enough (we handle collisions later?)
                # Actually, let's stick to generating a list of aliases for a canonical full name.
                
                canonical = display_name.lower()
                
                # Build alias set
                aliases = set()
                aliases.add(display_name)
                if short_name: aliases.add(short_name)
                if name: aliases.add(name)
                if abbr: aliases.add(abbr)
                if nickname: aliases.add(nickname)
                if location and nickname: aliases.add(f"{location} {nickname}")
                
                # Add manual aliases if any
                if canonical in MANUAL_ALIASES:
                    aliases.update(MANUAL_ALIASES[canonical])
                
                # Clean up
                cleaned_aliases = sorted(list({a.lower() for a in aliases if a}))
                
                # Store
                all_aliases[canonical] = cleaned_aliases
                
                # Also ensure "mascot" key points to same list if it's not the canonical
                if nickname and nickname.lower() != canonical:
                    all_aliases[nickname.lower()] = cleaned_aliases

    # Format output code
    content = ['# src/team_aliases.py', '', 'TEAM_ALIASES = {']
    
    # Sort for stability
    for key in sorted(all_aliases.keys()):
        aliases_quoted = [f'"{a}"' for a in all_aliases[key]]
        content.append(f'    "{key}": [{", ".join(aliases_quoted)}],')
        
    content.append('}')
    content.append('')
    
    # Write to file
    print(f"Writing {len(all_aliases)} team entries to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(content))
    print("Done!")

if __name__ == "__main__":
    generate_aliases()
