
import requests
import datetime
import time
import logging
import concurrent.futures
import urllib3

# Suppress insecure request warnings if we disable SSL verify
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ESPN API endpoints and their corresponding league names
LEAGUES_TO_SCRAPE = {
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
    },
    "mma": {
        "ufc": "ufc"
    },
    "golf": {
        "pga": "pga",
        "lpga": "lpga",
    },
    "racing": {
        "f1": "f1",
        "nascar-premier": "nascar",
        "irl": "indycar",
    },
    "tennis": {
        "atp": "atp",
        "wta": "wta"
    },
    "lacrosse": {
        "pll": "pll"
    }
}

# ESPN's internal group IDs for every D1 Men's Basketball conference.
NCAAB_CONFERENCE_GROUPS = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "13", "15", "16", "17",
    "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
    "31", "32", "59", "100",
]

def fetch_url(url, league_name, retries=2):
    """Helper function for threaded fetching"""
    for i in range(retries):
        try:
            # FIX: verify=False added to prevent SSL crashes in EXE
            response = requests.get(url, timeout=5, verify=False)
            response.raise_for_status()
            data = response.json()
            return data.get("events", [])
        except Exception:
            if i == retries - 1:
                return []
            time.sleep(0.2)
    return []

def fetch_scores_for_date(date_str):
    """
    Scrapes scores for all configured leagues for a given date string.
    Uses ThreadPoolExecutor for parallel fetching.
    """
    
    # Standardize date format for API
    try:
        if "-" in date_str:
             d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        else:
             d = datetime.datetime.strptime(date_str, "%m/%d/%Y")
        api_date = d.strftime("%Y%m%d")
    except ValueError:
        logger.error(f"Invalid date format: {date_str}")
        return []

    all_scores = []
    processed_game_ids = set()
    
    urls_to_fetch = []

    # Prepare URL list
    for sport_key, leagues in LEAGUES_TO_SCRAPE.items():
        for league_key_url, sheet_league_name in leagues.items():
            
            # --- SPECIAL HANDLING FOR NCAAB ---
            if league_key_url == "mens-college-basketball":
                for group_id in NCAAB_CONFERENCE_GROUPS:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_key}/{league_key_url}/scoreboard?dates={api_date}&groups={group_id}&limit=100"
                    urls_to_fetch.append((url, sheet_league_name, sport_key, league_key_url))
            
            # --- STANDARD HANDLING ---
            else:
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_key}/{league_key_url}/scoreboard?dates={api_date}&limit=300"
                urls_to_fetch.append((url, sheet_league_name, sport_key, league_key_url))

    logger.info(f"Fetching scores from {len(urls_to_fetch)} endpoints in parallel...")

    # Execute in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_league = {executor.submit(fetch_url, url, lname): (lname, skey, lkey) for url, lname, skey, lkey in urls_to_fetch}
        
        for future in concurrent.futures.as_completed(future_to_league):
            league_name, sport_key, league_key = future_to_league[future]
            try:
                events = future.result()
                for game in events:
                    if game['id'] not in processed_game_ids:
                        game_objs = _parse_espn_event(game, league_name)
                        if game_objs:
                            if isinstance(game_objs, list):
                                all_scores.extend(game_objs)
                            else:
                                all_scores.append(game_objs)
                            processed_game_ids.add(game['id'])
            except Exception as e:
                logger.error(f"Error processing {league_name}: {e}")

    return all_scores

def _parse_espn_event(game_data, league_name):
    """
    Parses a raw ESPN event JSON object into a list of standardized dictionaries.
    Handles Team vs Team (NFL, NBA, Soccer, Tennis, UFC) and Multi-Competitor (F1, Golf).
    Returns a LIST of game objects (one event might have multiple competitions/fights).
    """
    try:
        # Determine format based on league or structure
        is_multi_competitor = league_name.lower() in ['f1', 'pga', 'racing', 'golf']
        
        # Check if event is started/finished
        
        # Check if event is started/finished
        status_state = game_data.get('status', {}).get('type', {}).get('state', '')
        if status_state == 'pre':
            # print(f"Skipping {league_name} {game_data.get('id')} due to pre state")
            return []

        parsed_games = []
        
        # Iterate ALL competitions (fights/matches) in the event
        competitions = game_data.get("competitions", [])
        
        # Handle Tennis Groupings (e.g. Singles/Doubles) if competitions is empty
        if not competitions and "groupings" in game_data:
            for group in game_data["groupings"]:
                competitions.extend(group.get("competitions", []))
        
        for comp in competitions:
            # --- Multi-Competitor Logic (F1, Golf) ---
            if is_multi_competitor:
                competitors = comp.get("competitors", [])
                parsed_competitors = []
                
                for c in competitors:
                    ath = c.get("athlete", {})
                    name = ath.get("displayName") or ath.get("fullName") or c.get("name", "")
                    rank = c.get("order")
                    score = c.get("score")
                    winner = c.get("winner", False)
                    
                    parsed_competitors.append({
                        "name": name,
                        "rank": rank,
                        "score": score,
                        "winner": winner
                    })
                
                parsed_games.append({
                    "league": league_name,
                    "id": game_data.get("id", ""),
                    "name": game_data.get("name", ""),
                    "shortName": game_data.get("shortName", ""),
                    "type": "multi_competitor",
                    "competitors": parsed_competitors
                })

            # --- Team/Head-to-Head Logic (NFL, NBA, Soccer, Tennis, UFC) ---
            else:
                teams = comp.get("competitors", [])
                if len(teams) < 2: continue
                
                # Normalize Home/Away
                home_team_data = next((t for t in teams if t.get('homeAway') == 'home'), teams[0])
                away_team_data = next((t for t in teams if t.get('homeAway') == 'away'), teams[1])
                
                def get_name(c_data):
                    if 'athlete' in c_data:
                        return c_data['athlete'].get('displayName', '')
                    if 'team' in c_data:
                        return c_data['team'].get('displayName', '')
                    if 'roster' in c_data:
                        return c_data['roster'].get('displayName', '')
                    return "Unknown"

                try:
                    team1_name = get_name(home_team_data)
                    team2_name = get_name(away_team_data)
                except:
                    continue
                
                home_score = home_team_data.get("score")
                away_score = away_team_data.get("score")
                
                team1_winner = home_team_data.get("winner", False)
                team2_winner = away_team_data.get("winner", False)

                # Relaxed check: Allow missing score if winner is present (Tennis/UFC)
                if home_score is None and not (team1_winner or team2_winner):
                     # print(f"Skipping {league_name} {game_data.get('id')} due to no score/winner")
                     continue

                parsed_games.append({
                    "league": league_name,
                    "id": game_data.get("id", ""), 
                    "type": "matchup",
                    "team1": team1_name, 
                    "score1": home_score,
                    "winner1": team1_winner,
                    "team2": team2_name,
                    "score2": away_score,
                    "winner2": team2_winner,
                    "team1_data": {
                        "linescores": home_team_data.get("linescores", []),
                        "statistics": home_team_data.get("statistics", []),
                        "leaders": home_team_data.get("leaders", [])
                    },
                    "team2_data": {
                        "linescores": away_team_data.get("linescores", []),
                        "statistics": away_team_data.get("statistics", []),
                        "leaders": away_team_data.get("leaders", [])
                    }
                })
        
        return parsed_games

    except (KeyError, IndexError, StopIteration):
        return []

def fetch_boxscore(game_id, sport, league):
    """
    Fetches the detailed boxscore for a game.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={game_id}"
    try:
        resp = requests.get(url, timeout=5, verify=False)
        if resp.status_code == 200:
            return resp.json().get('boxscore', {})
    except:
        pass
    return {}
