
"""
Schedule Manager
================
Provides rapid access to historical game schedules for context-aware parsing.
Acts as the "Source of Truth" for which teams played on a given date.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    from src.score_fetcher import fetch_scores_for_date
except ImportError:
    fetch_scores_for_date = None


logger = logging.getLogger(__name__)


class ScheduleManager:
    """
    Manages fetching, caching, and querying game schedules.
    """

    _MEMORY_CACHE = {}  # Lightweight in-memory cache for the current run

    @staticmethod
    def get_schedule_for_date(target_date: str) -> list[dict[str, Any]]:
        """
        Get the full game slate for a specific date.
        Uses in-memory cache first, then persistent cache (via score_fetcher).
        """
        # unexpected date formats handled by utils.get_date_object usually, 
        # but here we expect "YYYY-MM-DD" mostly.
        
        if target_date in ScheduleManager._MEMORY_CACHE:
            return ScheduleManager._MEMORY_CACHE[target_date]

        logger.info(f"[ScheduleManager] Fetching schedule for {target_date}...")
        
        # Fetch for all supported leagues
        # We assume fetch_scores_for_date handles the SQLite caching.
        if fetch_scores_for_date is None:
            logger.warning("[ScheduleManager] Score fetcher unavailable. Returning empty schedule.")
            return []
            
        games = fetch_scores_for_date(
            target_date, 
            requested_leagues=None, # Fetch all
            force_refresh=False, 
            final_only=False # We want ALL games scheduled, even if they haven't started or are live
        )
        
        # Cache in memory
        ScheduleManager._MEMORY_CACHE[target_date] = games
        return games

    @staticmethod
    def get_context_string(target_date: str) -> str:
        """
        Returns a formatted string of games for the AI prompt.
        Format:
        NBA: LAL vs BOS, GSW vs PHX
        NFL: KC vs BAL
        """
        games = ScheduleManager.get_schedule_for_date(target_date)
        if not games:
            return "No games scheduled/found for this date."

        # Group by League
        grouped = {}
        for g in games:
            league = g.get("league", "Other").upper()
            if league not in grouped:
                grouped[league] = []
            
            # Format: "TeamA vs TeamB"
            # Some games (Golf/F1) might be multi-competitor
            if g.get("type") == "matchup":
                t1 = g.get("team1") or "TBD"
                t2 = g.get("team2") or "TBD"
                grouped[league].append(f"{t1} vs {t2}")
            elif g.get("name"):
                grouped[league].append(g.get("name"))

        # Build String
        lines = []
        priorities = ["NBA", "NFL", "NHL", "MLB", "NCAAB", "UFC"]
        
        # Add priority leagues first
        for league in priorities:
            if league in grouped:
                matchups = grouped[league]
                # Limit NCAAB to top 50 games if too many?
                if league == "NCAAB" and len(matchups) > 50:
                     matchups = matchups[:50] + [f"... and {len(matchups)-50} more"]
                
                matchups_str = ", ".join(matchups)
                lines.append(f"{league}: {matchups_str}")
                del grouped[league]
        
        # Add remaining leagues
        for league, matchups in grouped.items():
             matchups_str = ", ".join(matchups)
             lines.append(f"{league}: {matchups_str}")

        full_text = "\n".join(lines)
        
        # Hard cap at 3000 chars to save context window
        if len(full_text) > 3000:
            full_text = full_text[:3000] + " ... [Truncated Schedule]"
            
        return full_text

    @staticmethod
    def is_team_playing(team_name: str, target_date: str) -> tuple[bool, Optional[str]]:
        """
        Checks if a team is playing on the target date.
        Returns (is_playing, canonical_name).
        
        Soft Match Strategy:
        - Exact match
        - Substring match (e.g. "Kings" in "Sacramento Kings")
        """
        # TODO: Implement fuzzy matching if needed using team_aliases
        games = ScheduleManager.get_schedule_for_date(target_date)
        
        team_name_lower = team_name.lower().strip()
        
        for g in games:
            # Check Matchups
            if g.get("type") == "matchup":
                t1 = g.get("team1", "").lower()
                t2 = g.get("team2", "").lower()
                
                # Check 1: Exact/Constituent
                # If input is "Kings", it matches "Sacramento Kings"
                if team_name_lower in t1 or t1 in team_name_lower:
                    return True, g.get("team1")
                if team_name_lower in t2 or t2 in team_name_lower:
                    return True, g.get("team2")
                    
        return False, None
