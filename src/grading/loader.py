# src/grading/loader.py
"""
Data loading layer - wraps ESPN score fetching.
"""

import logging
from typing import Any

import requests

from src.grading.constants import ESPN_LEAGUE_MAP

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Handles fetching scores and boxscores from ESPN APIs.
    """

    # Reuse the existing score_fetcher if available
    @staticmethod
    def fetch_scores(dates: list[str], leagues: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Fetches scores for multiple dates and specific leagues.

        Args:
            dates: List of date strings (YYYY-MM-DD)
            leagues: Optional list of league codes to filter

        Returns:
            List of game dictionaries
        """
        try:
            import concurrent.futures

            from src.score_fetcher import fetch_scores_for_date

            all_games = []
            unique_dates = list(set(dates))

            # Fetch dates in parallel to speed up multi-day grading
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(unique_dates), 10)) as executor:
                future_to_date = {
                    executor.submit(fetch_scores_for_date, date_str, leagues): date_str
                    for date_str in unique_dates
                }

                for future in concurrent.futures.as_completed(future_to_date):
                    date_str = future_to_date[future]
                    try:
                        games = future.result()
                        logger.info(f"Fetched {len(games)} games for {date_str}")
                        all_games.extend(games)
                    except Exception as e:
                        logger.error(f"Error fetching scores for {date_str}: {e}")

            return all_games

        except ImportError:
            logger.warning("score_fetcher not available, using direct ESPN fetch")
            return DataLoader._fetch_scores_direct(dates, leagues)

    @staticmethod
    def _fetch_scores_direct(dates: list[str], leagues: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Direct ESPN API fetch fallback.
        """
        import datetime

        all_games = []
        leagues_to_fetch = leagues if leagues else list(ESPN_LEAGUE_MAP.keys())

        for date_str in dates:
            # Normalize date
            try:
                if "-" in date_str:
                    d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    d = datetime.datetime.strptime(date_str, "%m/%d/%Y")
                api_date = d.strftime("%Y%m%d")
            except ValueError:
                logger.error(f"Invalid date format: {date_str}")
                continue

            for league_code in leagues_to_fetch:
                if league_code not in ESPN_LEAGUE_MAP:
                    continue

                sport, league_key = ESPN_LEAGUE_MAP[league_code]
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league_key}/scoreboard?dates={api_date}&limit=300"

                try:
                    resp = requests.get(url, timeout=10, verify=False)
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    events = data.get("events", [])

                    for event in events:
                        games = DataLoader._parse_event(event, league_code)
                        all_games.extend(games)

                except Exception as e:
                    logger.debug(f"Error fetching {league_code}: {e}")
                    continue

        return all_games

    @staticmethod
    def _parse_event(event: dict, league: str) -> list[dict[str, Any]]:
        """Parse ESPN event into game objects."""
        games = []

        status = event.get("status", {}).get("type", {}).get("state", "")
        if status == "pre":
            return games

        for comp in event.get("competitions", []):
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            # Find home/away
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

            def get_name(c):
                if "athlete" in c:
                    return c["athlete"].get("displayName", "")
                if "team" in c:
                    return c["team"].get("displayName", "")
                return "Unknown"

            games.append(
                {
                    "id": event.get("id"),
                    "league": league,
                    "team1": get_name(home),
                    "team2": get_name(away),
                    "score1": home.get("score"),
                    "score2": away.get("score"),
                    "winner1": home.get("winner", False),
                    "winner2": away.get("winner", False),
                    "status": status,
                    "team1_data": {
                        "linescores": home.get("linescores", []),
                        "statistics": home.get("statistics", []),
                        "leaders": home.get("leaders", []),
                    },
                    "team2_data": {
                        "linescores": away.get("linescores", []),
                        "statistics": away.get("statistics", []),
                        "leaders": away.get("leaders", []),
                    },
                }
            )

        return games

    @staticmethod
    def fetch_boxscore(game: dict[str, Any]) -> list[dict[str, Any]] | None:
        """
        Fetches the full boxscore for a game.

        Args:
            game: Game dictionary with 'id' and 'league' keys

        Returns:
            List of player stat dictionaries or None
        """
        if "full_boxscore" in game:
            return game["full_boxscore"]

        game_id = game.get("id")
        league = game.get("league", "").lower()

        if not game_id or league not in ESPN_LEAGUE_MAP:
            return None

        sport, league_key = ESPN_LEAGUE_MAP[league]
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league_key}/summary?event={game_id}"

        try:
            resp = requests.get(url, timeout=10, verify=False)
            if resp.status_code != 200:
                return None

            data = resp.json()
            boxscore = data.get("boxscore", {})

            all_players = []

            for team in boxscore.get("players", []):
                for stat_group in team.get("statistics", []):
                    keys = stat_group.get("keys", [])

                    for ath in stat_group.get("athletes", []):
                        athlete = ath.get("athlete", {})
                        name = athlete.get("displayName", "") or athlete.get("fullName", "")
                        stats = ath.get("stats", [])

                        player_stats = {"name": name, "id": athlete.get("id")}
                        for i, val in enumerate(stats):
                            if i < len(keys):
                                player_stats[keys[i].lower()] = val

                        all_players.append(player_stats)

            return all_players

        except Exception as e:
            logger.debug(f"Error fetching boxscore for {game_id}: {e}")
            return None

    @staticmethod
    def fetch_odds(date: str) -> dict[str, dict]:
        """
        Fetches odds for all games on a date.

        Returns:
            Dict mapping "league:event_id" to odds data
        """
        try:
            from src.score_fetcher import fetch_odds_for_date

            return fetch_odds_for_date(date)
        except ImportError:
            logger.warning("Odds fetching not available")
            return {}
