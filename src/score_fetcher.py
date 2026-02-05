import concurrent.futures
import datetime
import logging
import time

import requests
import urllib3
from requests.adapters import HTTPAdapter

# Suppress insecure request warnings if we disable SSL verify
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONNECTION POOLING - Reuse TCP connections for faster requests
# =============================================================================
_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Get a reusable session with connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.verify = False
        # Increase pool size for parallel requests
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=2)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session


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
    "mma": {"ufc": "ufc"},
    "golf": {
        "pga": "pga",
        "lpga": "lpga",
    },
    "racing": {
        "f1": "f1",
        "nascar-premier": "nascar",
        "irl": "indycar",
    },
    "tennis": {"atp": "atp", "wta": "wta"},
    "lacrosse": {"pll": "pll"},
}

# ESPN's internal group IDs for every D1 Men's Basketball conference.
NCAAB_CONFERENCE_GROUPS = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "12",
    "13",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "59",
    "100",
]


def fetch_url(url, league_name, retries=2, session=None):
    """Helper function for threaded fetching with connection pooling."""
    sess = session or get_session()
    for i in range(retries):
        try:
            response = sess.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("events", [])
        except Exception:
            if i == retries - 1:
                return []
            time.sleep(0.2)
    return []


def fetch_scores_for_date(date_str, requested_leagues=None, current_scores=None, force_refresh=False, final_only=True):
    """
    Scrapes scores for all configured leagues for a given date string.
    Uses ThreadPoolExecutor for parallel fetching with caching.

    Args:
        date_str: "YYYY-MM-DD" or "MM/DD/YYYY"
        requested_leagues: Optional list/set of league names (e.g. ['nba', 'nfl']) to filter by.
                           If None, fetches all.
        current_scores: Optional list of existing game objects. If provided, we skip fetching
                        leagues that are already present in this list.
        force_refresh: If True, bypass cache and fetch fresh data.
        final_only: If True (default), only return games with status 'post' (final).
                    Live/in-progress games are excluded for grading accuracy.

    Returns:
        List of game dictionaries with scores.
    """
    from src.score_cache import get_cache

    cache = get_cache()

    # Normalize requested leagues
    if requested_leagues:
        requested_leagues = {l.lower() for l in requested_leagues}

    # Determine which leagues we already have
    existing_leagues = set()
    if current_scores:
        for game in current_scores:
            if "league" in game:
                existing_leagues.add(game["league"].lower())

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

    # Start with existing scores if provided, or empty list
    all_scores = list(current_scores) if current_scores else []
    processed_game_ids = {g["id"] for g in all_scores}

    urls_to_fetch = []
    leagues_from_cache = []

    # Get session for connection pooling
    session = get_session()

    # Prepare URL list, checking cache first
    for sport_key, leagues in LEAGUES_TO_SCRAPE.items():
        for league_key_url, sheet_league_name in leagues.items():
            norm_league = sheet_league_name.lower()

            # Optimization: Skip if we already have this league
            if norm_league in existing_leagues:
                continue

            # Filter by requested leagues if provided
            if requested_leagues and norm_league not in requested_leagues:
                continue

            # Check cache first (unless force_refresh)
            if not force_refresh:
                cached_games = cache.get_scores(api_date, norm_league)
                if cached_games is not None:
                    # Filter by final_only if needed (cached games are already final)
                    for game in cached_games:
                        if game.get("id") not in processed_game_ids:
                            all_scores.append(game)
                            processed_game_ids.add(game["id"])
                    leagues_from_cache.append(norm_league)
                    continue

            # --- SPECIAL HANDLING FOR NCAAB ---
            if league_key_url == "mens-college-basketball":
                for group_id in NCAAB_CONFERENCE_GROUPS:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_key}/{league_key_url}/scoreboard?dates={api_date}&groups={group_id}&limit=100"
                    urls_to_fetch.append((url, sheet_league_name, sport_key, league_key_url))

            # --- STANDARD HANDLING ---
            else:
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_key}/{league_key_url}/scoreboard?dates={api_date}&limit=300"
                urls_to_fetch.append((url, sheet_league_name, sport_key, league_key_url))

    if leagues_from_cache:
        logger.info(
            f"Cache HIT for {len(leagues_from_cache)} leagues: {', '.join(leagues_from_cache[:5])}{'...' if len(leagues_from_cache) > 5 else ''}"
        )

    if not urls_to_fetch:
        logger.info(f"All leagues served from cache. Total: {len(all_scores)} games")
        return all_scores

    logger.info(f"Fetching scores from {len(urls_to_fetch)} endpoints in parallel...")

    # Track games by league for caching
    games_by_league: dict[str, list[dict]] = {}

    # Execute in parallel with connection pooling
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_league = {
            executor.submit(fetch_url, url, lname, 2, session): (lname, skey, lkey)
            for url, lname, skey, lkey in urls_to_fetch
        }

        for future in concurrent.futures.as_completed(future_to_league):
            league_name, sport_key, league_key = future_to_league[future]
            try:
                events = future.result()
                for game in events:
                    if game["id"] not in processed_game_ids:
                        game_objs = _parse_espn_event(game, league_name, final_only=final_only)
                        if game_objs:
                            if isinstance(game_objs, list):
                                all_scores.extend(game_objs)
                                # Track for caching
                                if league_name.lower() not in games_by_league:
                                    games_by_league[league_name.lower()] = []
                                games_by_league[league_name.lower()].extend(game_objs)
                            else:
                                all_scores.append(game_objs)
                                if league_name.lower() not in games_by_league:
                                    games_by_league[league_name.lower()] = []
                                games_by_league[league_name.lower()].append(game_objs)
                            processed_game_ids.add(game["id"])
            except Exception as e:
                logger.error(f"Error processing {league_name}: {e}")

    # Cache the fetched scores by league
    for league, games in games_by_league.items():
        if games:  # Only cache if we got games
            cache.set_scores(api_date, league, games)

    return all_scores


def _parse_espn_event(game_data, league_name, final_only=True):
    """
    Parses a raw ESPN event JSON object into a list of standardized dictionaries.
    Handles Team vs Team (NFL, NBA, Soccer, Tennis, UFC) and Multi-Competitor (F1, Golf).
    Returns a LIST of game objects (one event might have multiple competitions/fights).

    Args:
        game_data: Raw ESPN event JSON
        league_name: League identifier
        final_only: If True, only return games with status 'post' (final).
                    If False, return both 'in' (live) and 'post' games.
    """
    try:
        # Determine format based on league or structure
        is_multi_competitor = league_name.lower() in ["f1", "pga", "racing", "golf"]

        # Check game status
        status_state = game_data.get("status", {}).get("type", {}).get("state", "")

        # Skip pre-game (not started)
        if status_state == "pre":
            return []

        # Skip in-progress games if final_only is True
        if final_only and status_state == "in":
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

                    parsed_competitors.append({"name": name, "rank": rank, "score": score, "winner": winner})

                parsed_games.append(
                    {
                        "league": league_name,
                        "id": game_data.get("id", ""),
                        "name": game_data.get("name", ""),
                        "shortName": game_data.get("shortName", ""),
                        "type": "multi_competitor",
                        "competitors": parsed_competitors,
                    }
                )

            # --- Team/Head-to-Head Logic (NFL, NBA, Soccer, Tennis, UFC) ---
            else:
                teams = comp.get("competitors", [])
                if len(teams) < 2:
                    continue

                # Normalize Home/Away
                home_team_data = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                away_team_data = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

                def get_name(c_data):
                    if "athlete" in c_data:
                        return c_data["athlete"].get("displayName", "")
                    if "team" in c_data:
                        return c_data["team"].get("displayName", "")
                    if "roster" in c_data:
                        return c_data["roster"].get("displayName", "")
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

                parsed_games.append(
                    {
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
                            "leaders": home_team_data.get("leaders", []),
                        },
                        "team2_data": {
                            "linescores": away_team_data.get("linescores", []),
                            "statistics": away_team_data.get("statistics", []),
                            "leaders": away_team_data.get("leaders", []),
                        },
                    }
                )

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
            return resp.json().get("boxscore", {})
    except:
        pass
    return {}


# =============================================================================
# ESPN ODDS API INTEGRATION
# =============================================================================

# Mapping from our league names to ESPN API sport/league keys for odds endpoint
# Format: "our_league": ("sport", "league")
ODDS_LEAGUE_MAPPING = {
    # Basketball
    "nba": ("basketball", "nba"),
    "wnba": ("basketball", "wnba"),
    "ncaab": ("basketball", "mens-college-basketball"),
    "wncaab": ("basketball", "womens-college-basketball"),
    # Football
    "nfl": ("football", "nfl"),
    "ncaaf": ("football", "college-football"),
    # Hockey
    "nhl": ("hockey", "nhl"),
    # Baseball
    "mlb": ("baseball", "mlb"),
    # Soccer (has drawOdds for 3-way moneyline)
    "epl": ("soccer", "eng.1"),
    "mls": ("soccer", "usa.1"),
    "ucl": ("soccer", "uefa.champions"),
    "championship": ("soccer", "eng.2"),
    "laliga": ("soccer", "esp.1"),
    "bundesliga": ("soccer", "ger.1"),
    "seriea": ("soccer", "ita.1"),
    "ligue1": ("soccer", "fra.1"),
    "nwsl": ("soccer", "usa.nwsl"),
    # MMA (uses awayAthleteOdds/homeAthleteOdds)
    "ufc": ("mma", "ufc"),
    # These sports don't have odds available via ESPN API:
    # - pga, lpga (golf) - returns empty
    # - f1, nascar, indycar (racing) - returns 404
    # - atp, wta (tennis) - returns empty
}

# Sports that use athlete odds instead of team odds
ATHLETE_ODDS_SPORTS = {"mma", "ufc"}

# Sports that have 3-way moneyline (home/away/draw)
SOCCER_LEAGUES = {"epl", "mls", "ucl", "championship", "laliga", "bundesliga", "seriea", "ligue1", "nwsl"}


def fetch_odds_for_date(date_str: str) -> dict:
    """
    Fetches odds for all games on a given date.

    Args:
        date_str: Date in "YYYY-MM-DD" or "MM/DD/YYYY" format

    Returns:
        Dictionary mapping game keys to odds data:
        {
            "league:event_id:comp_id": {
                "home_team": str,
                "away_team": str,
                "moneyline_home": int or None,
                "moneyline_away": int or None,
                "moneyline_draw": int or None,  # Soccer only
                "spread_home": float or None,
                "spread_away": float or None,
                "spread_home_odds": int or None,
                "spread_away_odds": int or None,
                "total": float or None,
                "over_odds": int or None,
                "under_odds": int or None,
                "provider": str
            }
        }
    """
    # Standardize date format
    try:
        if "-" in date_str:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        else:
            d = datetime.datetime.strptime(date_str, "%m/%d/%Y")
        api_date = d.strftime("%Y%m%d")
    except ValueError:
        logger.error(f"Invalid date format for odds: {date_str}")
        return {}

    odds_by_game = {}

    # Fetch scoreboards first to get event/competition IDs
    for league_name, (sport, league_key) in ODDS_LEAGUE_MAPPING.items():
        try:
            # Fetch scoreboard for this league
            scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league_key}/scoreboard?dates={api_date}&limit=300"

            resp = requests.get(scoreboard_url, timeout=10, verify=False)
            if resp.status_code != 200:
                continue

            data = resp.json()
            events = data.get("events", [])

            # For each event, fetch odds for each competition
            for event in events:
                event_id = event.get("id")
                if not event_id:
                    continue

                competitions = event.get("competitions", [])

                # Handle Tennis groupings
                if not competitions and "groupings" in event:
                    for group in event.get("groupings", []):
                        competitions.extend(group.get("competitions", []))

                for comp in competitions:
                    comp_id = comp.get("id", event_id)

                    # Fetch odds for this competition
                    odds_data = _fetch_competition_odds(sport, league_key, event_id, comp_id, league_name)

                    if odds_data:
                        # Extract team/athlete names from competition
                        competitors = comp.get("competitors", [])
                        home_name, away_name = _extract_competitor_names(competitors, league_name)

                        game_key = f"{league_name}:{event_id}:{comp_id}"
                        odds_data["home_team"] = home_name
                        odds_data["away_team"] = away_name
                        odds_by_game[game_key] = odds_data

        except Exception as e:
            logger.debug(f"Error fetching odds for {league_name}: {e}")
            continue

    logger.info(f"Fetched odds for {len(odds_by_game)} games on {date_str}")
    return odds_by_game


def fetch_odds_for_leagues(date_str: str, leagues: list[str]) -> dict[str, dict]:
    """
    Fetches odds for specific leagues only (optimized for smart backfilling).
    Uses parallel fetching for speed.

    Args:
        date_str: Date in "YYYY-MM-DD" or "MM/DD/YYYY" format
        leagues: List of league codes to fetch (e.g., ['nba', 'nfl'])

    Returns:
        Dictionary mapping game keys to odds data
    """
    # Standardize date format
    try:
        if "-" in date_str:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        else:
            d = datetime.datetime.strptime(date_str, "%m/%d/%Y")
        api_date = d.strftime("%Y%m%d")
    except ValueError:
        logger.error(f"Invalid date format for odds: {date_str}")
        return {}

    leagues_set = {l.lower() for l in leagues}
    odds_by_game = {}
    session = get_session()

    # Build list of (league_name, sport, league_key) to fetch
    leagues_to_fetch = []
    for league_name, (sport, league_key) in ODDS_LEAGUE_MAPPING.items():
        if league_name.lower() in leagues_set:
            leagues_to_fetch.append((league_name, sport, league_key))

    if not leagues_to_fetch:
        return {}

    logger.info(f"Fetching odds for {len(leagues_to_fetch)} leagues in parallel...")

    def fetch_league_odds(args):
        """Fetch odds for a single league."""
        league_name, sport, league_key = args
        league_odds = {}

        try:
            # Fetch scoreboard for this league
            scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league_key}/scoreboard?dates={api_date}&limit=300"
            resp = session.get(scoreboard_url, timeout=10)
            if resp.status_code != 200:
                return league_odds

            data = resp.json()
            events = data.get("events", [])

            # For each event, fetch odds
            for event in events:
                event_id = event.get("id")
                if not event_id:
                    continue

                competitions = event.get("competitions", [])
                if not competitions and "groupings" in event:
                    for group in event.get("groupings", []):
                        competitions.extend(group.get("competitions", []))

                for comp in competitions:
                    comp_id = comp.get("id", event_id)
                    odds_data = _fetch_competition_odds(sport, league_key, event_id, comp_id, league_name)

                    if odds_data:
                        competitors = comp.get("competitors", [])
                        home_name, away_name = _extract_competitor_names(competitors, league_name)

                        game_key = f"{league_name}:{event_id}:{comp_id}"
                        odds_data["home_team"] = home_name
                        odds_data["away_team"] = away_name
                        league_odds[game_key] = odds_data

        except Exception as e:
            logger.debug(f"Error fetching odds for {league_name}: {e}")

        return league_odds

    # Fetch all leagues in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_league_odds, args) for args in leagues_to_fetch]

        for future in concurrent.futures.as_completed(futures):
            try:
                league_odds = future.result()
                odds_by_game.update(league_odds)
            except Exception as e:
                logger.debug(f"Error in parallel odds fetch: {e}")

    logger.info(f"Fetched odds for {len(odds_by_game)} games")
    return odds_by_game


def _fetch_competition_odds(sport: str, league: str, event_id: str, comp_id: str, league_name: str) -> dict | None:
    """
    Fetches odds for a specific competition from ESPN API.

    Args:
        sport: ESPN sport key (e.g., "basketball")
        league: ESPN league key (e.g., "nba")
        event_id: ESPN event ID
        comp_id: ESPN competition ID
        league_name: Our internal league name for determining odds type

    Returns:
        Parsed odds dict or None if unavailable
    """
    odds_url = f"https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{event_id}/competitions/{comp_id}/odds"

    try:
        resp = requests.get(odds_url, timeout=5, verify=False)
        if resp.status_code != 200:
            return None

        data = resp.json()
        items = data.get("items", [])

        if not items:
            return None

        # Prefer ESPN BET (id=58), fall back to first provider
        odds_item = None
        for item in items:
            provider_id = item.get("provider", {}).get("id")
            if provider_id == "58":
                odds_item = item
                break

        if odds_item is None:
            odds_item = items[0]

        return _parse_odds_item(odds_item, league_name)

    except Exception as e:
        logger.debug(f"Error fetching odds for {event_id}/{comp_id}: {e}")
        return None


def _parse_odds_item(odds_item: dict, league_name: str) -> dict:
    """
    Parses an ESPN odds item into our standardized format.

    Handles:
    - Team sports (awayTeamOdds/homeTeamOdds)
    - Combat sports (awayAthleteOdds/homeAthleteOdds)
    - Soccer (drawOdds for 3-way moneyline)
    """
    result = {
        "moneyline_home": None,
        "moneyline_away": None,
        "moneyline_draw": None,
        "spread_home": None,
        "spread_away": None,
        "spread_home_odds": None,
        "spread_away_odds": None,
        "total": None,
        "over_odds": None,
        "under_odds": None,
        "provider": odds_item.get("provider", {}).get("name", "Unknown"),
    }

    # Determine if this is athlete odds (UFC) or team odds
    is_athlete_sport = league_name.lower() in ATHLETE_ODDS_SPORTS
    is_soccer = league_name.lower() in SOCCER_LEAGUES

    # Get the correct odds keys
    if is_athlete_sport:
        home_odds = odds_item.get("homeAthleteOdds", {})
        away_odds = odds_item.get("awayAthleteOdds", {})
    else:
        home_odds = odds_item.get("homeTeamOdds", {})
        away_odds = odds_item.get("awayTeamOdds", {})

    # Parse moneylines
    result["moneyline_home"] = _safe_int(home_odds.get("moneyLine"))
    result["moneyline_away"] = _safe_int(away_odds.get("moneyLine"))

    # Parse draw odds for soccer
    if is_soccer:
        draw_odds = odds_item.get("drawOdds", {})
        result["moneyline_draw"] = _safe_int(draw_odds.get("moneyLine"))

    # Parse spread
    result["spread_home"] = _safe_float(odds_item.get("spread"))
    if result["spread_home"] is not None:
        result["spread_away"] = -result["spread_home"]

    # Parse spread odds (juice)
    result["spread_home_odds"] = _safe_int(home_odds.get("spreadOdds"))
    result["spread_away_odds"] = _safe_int(away_odds.get("spreadOdds"))

    # Parse totals
    result["total"] = _safe_float(odds_item.get("overUnder"))
    result["over_odds"] = _safe_int(odds_item.get("overOdds"))
    result["under_odds"] = _safe_int(odds_item.get("underOdds"))

    return result


def _extract_competitor_names(competitors: list, league_name: str) -> tuple[str, str]:
    """
    Extracts home and away team/athlete names from competition data.

    Returns:
        Tuple of (home_name, away_name)
    """
    home_name = ""
    away_name = ""

    for comp in competitors:
        home_away = comp.get("homeAway", "")

        # Try different name sources
        name = ""
        if "athlete" in comp:
            name = comp["athlete"].get("displayName", "")
        elif "team" in comp:
            team = comp["team"]
            # Use abbreviation for matching, full name as fallback
            name = team.get("abbreviation", "") or team.get("displayName", "") or team.get("name", "")
        elif "roster" in comp:
            name = comp["roster"].get("displayName", "")

        if home_away == "home":
            home_name = name
        elif home_away == "away":
            away_name = name

    return home_name, away_name


def _safe_int(value) -> int | None:
    """Safely convert value to int, returning None if invalid."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> float | None:
    """Safely convert value to float, returning None if invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def get_odds_for_pick(pick_text: str, league: str, odds_by_game: dict) -> dict | None:
    """
    Looks up odds for a specific pick from the pre-fetched odds data.

    Args:
        pick_text: The pick text (e.g., "Lakers -3.5", "Chiefs ML")
        league: The league name (e.g., "nba", "nfl")
        odds_by_game: Dictionary from fetch_odds_for_date()

    Returns:
        Odds dict for matching game, or None if not found
    """
    pick_lower = pick_text.lower().strip()
    league_lower = league.lower()

    # Filter to games in this league
    league_games = {k: v for k, v in odds_by_game.items() if k.startswith(f"{league_lower}:")}

    if not league_games:
        return None

    # Try to match pick to a game
    for game_key, odds in league_games.items():
        home = odds.get("home_team", "").lower()
        away = odds.get("away_team", "").lower()

        # Check if pick mentions either team
        if _pick_matches_team(pick_lower, home) or _pick_matches_team(pick_lower, away):
            return odds

    return None


def _pick_matches_team(pick_lower: str, team_lower: str) -> bool:
    """
    Checks if a pick text matches a team name.
    Handles abbreviations, nicknames, and city names.
    """
    if not team_lower:
        return False

    # Direct match
    if team_lower in pick_lower:
        return True

    # Check individual words (for abbreviations like "LAL", "KC")
    team_words = team_lower.split()
    for word in team_words:
        if len(word) >= 2 and word in pick_lower:
            return True

    return False


def fetch_odds_for_game(event_id: str, comp_id: str, league: str) -> dict | None:
    """
    Fetches odds for a single game by ID.

    Args:
        event_id: ESPN event ID
        comp_id: ESPN competition ID (often same as event_id for team sports)
        league: Our internal league name (e.g., "nba")

    Returns:
        Parsed odds dict or None if unavailable
    """
    league_lower = league.lower()

    if league_lower not in ODDS_LEAGUE_MAPPING:
        logger.debug(f"League {league} not supported for odds")
        return None

    sport, league_key = ODDS_LEAGUE_MAPPING[league_lower]

    return _fetch_competition_odds(sport, league_key, event_id, comp_id, league_lower)
