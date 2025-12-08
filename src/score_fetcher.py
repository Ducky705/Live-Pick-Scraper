# src/score_fetcher.py
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
                    urls_to_fetch.append((url, sheet_league_name))
            
            # --- STANDARD HANDLING ---
            else:
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_key}/{league_key_url}/scoreboard?dates={api_date}&limit=300"
                urls_to_fetch.append((url, sheet_league_name))

    logger.info(f"Fetching scores from {len(urls_to_fetch)} endpoints in parallel...")

    # Execute in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_league = {executor.submit(fetch_url, url, lname): lname for url, lname in urls_to_fetch}
        
        for future in concurrent.futures.as_completed(future_to_league):
            league_name = future_to_league[future]
            try:
                events = future.result()
                for game in events:
                    if game['id'] not in processed_game_ids:
                        game_obj = _parse_espn_event(game, league_name)
                        if game_obj:
                            all_scores.append(game_obj)
                            processed_game_ids.add(game['id'])
            except Exception as e:
                logger.error(f"Error processing {league_name}: {e}")

    return all_scores

def _parse_espn_event(game_data, league_name):
    """Parses a raw ESPN event JSON object into a simplified dictionary."""
    try:
        comp = game_data["competitions"][0]
        teams = comp["competitors"]
        
        home_team_data = next((t for t in teams if t.get('homeAway') == 'home'), teams[0])
        away_team_data = next((t for t in teams if t.get('homeAway') == 'away'), teams[1])

        # Check if game is started/finished
        status_state = game_data.get('status', {}).get('type', {}).get('state', '')
        if status_state == 'pre':
            return None 

        home_score = home_team_data.get("score")
        away_score = away_team_data.get("score")
        
        if home_score is None or away_score is None:
            return None

        return {
            "league": league_name,
            "team1": home_team_data["team"]["displayName"], 
            "score1": home_score,
            "team2": away_team_data["team"]["displayName"],
            "score2": away_score
        }
    except (KeyError, IndexError, StopIteration):
        return None
