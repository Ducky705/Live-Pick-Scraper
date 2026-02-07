
import requests
import sys
import os
sys.path.append(os.getcwd())
try:
    from src.team_aliases import TEAM_ALIASES
except ImportError:
    # Fallback if running from tools/ directly
    sys.path.append(os.path.dirname(os.getcwd()))
    from src.team_aliases import TEAM_ALIASES

def normalize(name):
    return name.lower().replace(".", "").replace("'", "").replace("-", " ").strip()

def get_nba_aliases():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams?limit=100"
    resp = requests.get(url)
    data = resp.json()
    
    leagues = data.get('sports', [{}])[0].get('leagues', [{}])[0]
    teams = leagues.get('teams', [])
    
    found_aliases = {}
    
    for item in teams:
        team = item.get('team', {})
        name = team.get('displayName', '')
        short = team.get('shortDisplayName', '')
        abbr = team.get('abbreviation', '')
        nick = team.get('nickname', '')
        loc = team.get('location', '')
        
        # Canonical key usually nickname lowercased
        key = nick.lower()
        
        aliases = set()
        if name: aliases.add(name)
        if short: aliases.add(short)
        if abbr: aliases.add(abbr)
        if nick: aliases.add(nick)
        if loc and nick: aliases.add(f"{loc} {nick}")
        
        found_aliases[key] = list(aliases)
        
    return found_aliases

def main():
    print("--- Checking for Missing Aliases (NBA) ---")
    generated = get_nba_aliases()
    
    current_flat = set()
    for k, v in TEAM_ALIASES.items():
        for alias in v:
            current_flat.add(normalize(alias))
            
    missing_count = 0
    for key, aliases in generated.items():
        for alias in aliases:
            norm = normalize(alias)
            if norm not in current_flat:
                # Filter out very short ones that might be dangerous (like 'GS', 'NY') 
                # unless we are sure. But let's print them to see.
                if len(alias) > 2:
                    print(f"MISSING: {alias} (for {key})")
                    missing_count += 1
                    
    print(f"\nTotal potential new aliases found: {missing_count}")

if __name__ == "__main__":
    main()
