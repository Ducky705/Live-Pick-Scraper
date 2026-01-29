# src/grading/matcher.py
"""
Team and player matching logic using aliases and fuzzy matching.
"""

import re
from typing import Any

from src.grading.constants import LEAGUE_ALIASES_MAP
from src.team_aliases import TEAM_ALIASES


class Matcher:
    """
    Matches pick text to games and players using aliases and heuristics.
    """

    @staticmethod
    def normalize(name: str) -> str:
        """Normalize a name for comparison."""
        if not name:
            return ""
        return name.lower().replace(".", "").replace("'", "").replace("-", " ").strip()

    @staticmethod
    def find_game(pick_text: str, league: str, games: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        Find the best matching game for a pick.

        Args:
            pick_text: The pick text
            league: League code
            games: List of game dictionaries

        Returns:
            Best matching game or None
        """
        target_league = LEAGUE_ALIASES_MAP.get(league.lower(), league.lower())

        # Filter games by league
        league_games = [
            g
            for g in games
            if LEAGUE_ALIASES_MAP.get(g.get("league", "").lower(), g.get("league", "").lower()) == target_league
        ]

        if not league_games:
            # Try cross-league fallback for common confusions
            if target_league == "ncaaf":
                league_games = [g for g in games if g.get("league", "").lower() == "ncaab"]
            elif target_league == "ncaab":
                league_games = [g for g in games if g.get("league", "").lower() == "ncaaf"]

        # Try to find in league-filtered games first
        result = Matcher._find_best_match(pick_text, league_games)
        if result:
            return result

        # Fallback: try all games if league filter failed
        if league_games != games:
            return Matcher._find_best_match(pick_text, games)

        return None

    @staticmethod
    def _find_best_match(pick_text: str, games: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find the best matching game from a list of games."""
        if not games:
            return None

        best_match = None
        best_score = 0
        pick_norm = Matcher.normalize(pick_text)

        for game in games:
            score = 0

            t1 = game.get("team1", "")
            t2 = game.get("team2", "")

            if Matcher._team_in_text(t1, pick_norm):
                score += 1
            if Matcher._team_in_text(t2, pick_norm):
                score += 1

            if score > best_score:
                best_score = score
                best_match = game

            # Perfect match optimization
            if best_score >= 2:
                return best_match

        # Return if at least one team matched
        return best_match if best_score >= 1 else None

    @staticmethod
    def _team_in_text(team_name: str, text: str) -> bool:
        """Check if team is mentioned in text using aliases."""
        if not team_name:
            return False

        team_norm = Matcher.normalize(team_name)

        # 1. Direct word boundary match
        if re.search(r"\b" + re.escape(team_norm) + r"\b", text):
            return True

        # 2. Check all aliases
        for canonical, aliases in TEAM_ALIASES.items():
            # Check if this team matches the canonical or any alias
            is_match = team_norm == Matcher.normalize(canonical)
            if not is_match:
                for alias in aliases:
                    if Matcher.normalize(alias) in team_norm or team_norm in Matcher.normalize(alias):
                        is_match = True
                        break

            if is_match:
                # Check if any alias is in the text
                for alias in aliases:
                    alias_norm = Matcher.normalize(alias)
                    if alias_norm and re.search(r"\b" + re.escape(alias_norm) + r"\b", text):
                        return True
                    # Also check if text contains significant part of alias
                    alias_words = alias_norm.split()
                    if len(alias_words) >= 2:
                        # Try matching first two words (e.g., "golden state")
                        partial = " ".join(alias_words[:2])
                        if len(partial) > 5 and re.search(r"\b" + re.escape(partial) + r"\b", text):
                            return True

        # 3. Last word fallback (e.g., "Lakers" from "Los Angeles Lakers")
        words = team_norm.split()
        if len(words) > 1:
            last = words[-1]
            if len(last) > 2 and re.search(r"\b" + re.escape(last) + r"\b", text):
                return True

        # 4. First significant words fallback (e.g., "Golden State" from "Golden State Warriors")
        if len(words) >= 2:
            first_two = " ".join(words[:2])
            if len(first_two) > 5 and re.search(r"\b" + re.escape(first_two) + r"\b", text):
                return True

        return False

    @staticmethod
    def resolve_picked_team(pick_text: str, game: dict[str, Any]) -> tuple[str | None, str | None, bool]:
        """
        Determine which team was picked in the bet.

        Returns:
            Tuple of (picked_team, opponent_team, is_team1)
        """
        t1 = game.get("team1", "")
        t2 = game.get("team2", "")
        pick_norm = Matcher.normalize(pick_text)

        t1_match = Matcher._team_in_text(t1, pick_norm)
        t2_match = Matcher._team_in_text(t2, pick_norm)

        if t1_match and not t2_match:
            return t1, t2, True
        elif t2_match and not t1_match:
            return t2, t1, False

        return None, None, False

    @staticmethod
    def find_player_in_boxscore(player_name: str, boxscore: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        Find a player in the boxscore data.

        Args:
            player_name: Player name to search for
            boxscore: List of player stat dictionaries

        Returns:
            Player stats dict or None
        """
        if not boxscore:
            return None

        target = Matcher.normalize(player_name)

        # Split into first/last name
        parts = target.split()
        last_name = parts[-1] if parts else target
        first_name = parts[0] if len(parts) > 1 else ""

        for player in boxscore:
            p_name = Matcher.normalize(player.get("name", ""))

            # Full name match
            if target in p_name or p_name in target:
                return player

            # Last name match (common for props)
            p_parts = p_name.split()
            p_last = p_parts[-1] if p_parts else p_name

            if last_name == p_last:
                # Verify first initial if available
                if first_name and p_parts:
                    p_first = p_parts[0]
                    if first_name[0] == p_first[0]:
                        return player
                else:
                    return player

        return None

    @staticmethod
    def find_player_in_leaders(
        player_name: str, game: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str | None]:
        """
        Find a player in the game's leaders data.

        Returns:
            Tuple of (leader_entry, stat_category) or (None, None)
        """
        target = Matcher.normalize(player_name)

        for team_key in ["team1_data", "team2_data"]:
            team_data = game.get(team_key, {})
            leaders = team_data.get("leaders", [])

            for category in leaders:
                cat_name = category.get("name", "")
                for leader in category.get("leaders", []):
                    athlete = leader.get("athlete", {})
                    p_name = athlete.get("displayName", "") or athlete.get("fullName", "")

                    if target in Matcher.normalize(p_name):
                        return leader, cat_name

        return None, None
