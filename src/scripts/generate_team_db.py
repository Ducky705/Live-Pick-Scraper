
import sys
import os
import json
import requests
import datetime
import urllib3

# Add src to path just in case
sys.path.append(os.path.join(os.getcwd(), "src"))

# Suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants for ESPN API
# We duplicate some logic from score_fetcher to keep this script standalone if needed, 
# or we could import. For robustness, I'll copy the map.

LEAGUES_TO_FETCH = {
    "basketball": {
        "nba": "nba",
        "wnba": "wnba",
        "mens-college-basketball": "ncaab",
        "womens-college-basketball": "wncaab",
    },
    "hockey": {
        "nhl": "nhl",
    },
    "baseball": {
        "mlb": "mlb",
    },
    "football": {
        "nfl": "nfl",
        "college-football": "ncaaf",
    },
    "soccer": {
        "eng.1": "epl",
        "usa.1": "mls",
        "uefa.champions": "ucl",
        "eng.2": "championship",
        "esp.1": "laliga",
        "ger.1": "bundesliga",
        "ita.1": "seriea",
        "fra.1": "ligue1",
        "usa.nwsl": "nwsl",
        "mex.1": "liga_mx",
        "ned.1": "eredivisie",
    }
}

# For NCAAB, we need to fetch all conferences. 
# The common API endpoint only returns Top 25 unless we specify groups.
# We will iterate groups 1-32, 50, etc. based on score_fetcher.
NCAAB_CONFERENCE_GROUPS = [str(i) for i in range(1, 33)] + ["50", "100"]

OUTPUT_FILE = "src/grading/data/teams_db.json"

def fetch_teams_for_league(sport, league_key, league_alias):
    """
    Fetch all teams for a given league.
    Strategy: Use the 'teams' endpoint if available, or scoreboard for active games?
    Better: Use `http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams`
    """
    print(f"Fetching teams for {league_alias} ({sport}/{league_key})...")
    
    teams_found = []
    
    # Base URL for teams
    # Pagination might be needed for some, but typically this endpoint returns all for pro leagues.
    # For College, it limits. We might need `?limit=1000`.
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league_key}/teams?limit=1000"
    
    if league_alias == "ncaab" or league_alias == "ncaaf":
        # For college, even limit=1000 might filter by "groups" (conferences).
        # We need to iterate groups to get everyone.
        # See score_fetcher logic.
        groups = NCAAB_CONFERENCE_GROUPS if league_alias == "ncaab" else ["80", "81"] # NCAAF is simpler usually? 
        # Actually for NCAAF, limit=1000 usually gets FBS.
        if league_alias == "ncaab":
             # iterating groups
             all_college_teams = {}
             for g in groups:
                 g_url = f"{url}&groups={g}"
                 try:
                     resp = requests.get(g_url, timeout=5)
                     data = resp.json()
                     for t_entry in data.get("sports", [])[0].get("leagues", [])[0].get("teams", []):
                         team = t_entry.get("team", {})
                         all_college_teams[team.get("id")] = team
                 except Exception as e:
                     pass
             teams_found = list(all_college_teams.values())
             print(f"  Found {len(teams_found)} teams for {league_alias} via groups.")
             return teams_found
        else:
             # NCAAF - Try just limit=1000 first
             pass

    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        # Structure: sports -> leagues -> teams
        for sport_obj in data.get("sports", []):
            for league_obj in sport_obj.get("leagues", []):
                for team_entry in league_obj.get("teams", []):
                    teams_found.append(team_entry.get("team"))
        
        print(f"  Found {len(teams_found)} teams for {league_alias}.")
        
    except Exception as e:
        print(f"  Error fetching {league_alias}: {e}")
        
    return teams_found

def process_teams(teams_list, league_alias):
    """
    Extract useful names/aliases from team objects.
    Returns a list of dicts: {"name": str, "league": str, "aliases": [str]}
    """
    processed = []
    for team in teams_list:
        if not team: continue
        
        full_name = team.get("displayName", "").lower()
        short_name = team.get("shortDisplayName", "").lower()
        name = team.get("name", "").lower() # e.g. "Kings"
        abbr = team.get("abbreviation", "").lower()
        location = team.get("location", "").lower()
        nickname = team.get("nickname", "").lower() # e.g. "Kings"
        
        # Collect all viable search tokens
        aliases = set()
        if full_name: aliases.add(full_name)
        if short_name: aliases.add(short_name)
        if name: aliases.add(name)
        if nickname: aliases.add(nickname)
        # Location + Nickname (e.g. "Sacramento Kings") is covered by full_name usually.
        # But handle cases.
        
        # Skip abbrevs for universal search? "LAL" -> Lakers? Maybe.
        # Be careful with collisions. "ARI" (Arizona) vs "ARI" (ArianaGrande? No).
        # We will add abbrs but with lower priority in matcher, or maybe include them.
        if abbr and len(abbr) > 1: aliases.add(abbr)
        
        processed.append({
            "id": team.get("id"),
            "league": league_alias,
            "names": list(aliases)
        })
    return processed

def main():
    all_teams_data = []
    
    for sport, leagues in LEAGUES_TO_FETCH.items():
        for league_key, league_alias in leagues.items():
            raw_teams = fetch_teams_for_league(sport, league_key, league_alias)
            processed = process_teams(raw_teams, league_alias)
            all_teams_data.extend(processed)
            
    # Save to JSON
    # We want a format optimized for lookup?
    # Or just a flat list for the Matcher to load and build its index?
    # Flat list is fine.
    
    print(f"Saving {len(all_teams_data)} total teams to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_teams_data, f, indent=2)
    print("Done.")

if __name__ == "__main__":
    main()
