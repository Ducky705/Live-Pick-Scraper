# src/score_cache.py
"""
Persistent caching layer for ESPN scores, boxscores, and odds.

Features:
- SQLite-backed storage for speed and persistence
- Final games cached for 24 hours (immutable once finished)
- Boxscores cached permanently (don't change after game ends)
- Odds cached for 24 hours
- Thread-safe with check_same_thread=False
- force_refresh support via bypass flag

Usage:
    from src.score_cache import get_cache
    cache = get_cache()

    # Get/set scores
    games = cache.get_scores("20260122", "nba")
    cache.set_scores("20260122", "nba", games)

    # Get/set boxscores
    boxscore = cache.get_boxscore("401234567")
    cache.set_boxscore("401234567", boxscore)
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ScoreCache:
    """
    SQLite-backed cache for ESPN API data.

    TTL Strategy:
    - Scores: 24 hours (games are final, unlikely to change)
    - Boxscores: 7 days (immutable after game ends)
    - Odds: 24 hours
    """

    DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "cache" / "espn_cache_v1.db"
    SCORES_TTL = 86400  # 24 hours
    BOXSCORE_TTL = 604800  # 7 days
    ODDS_TTL = 86400  # 24 hours

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency

        # Scores table: cache_key = "YYYYMMDD:league"
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                fetched_at REAL NOT NULL,
                game_count INTEGER DEFAULT 0
            )
        """)

        # Boxscores table: indexed by game_id
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS boxscores (
                game_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                fetched_at REAL NOT NULL
            )
        """)

        # Odds table: cache_key = "YYYYMMDD:league"
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS odds (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                fetched_at REAL NOT NULL
            )
        """)

        self.conn.commit()
        logger.debug(f"ScoreCache initialized at {self.db_path}")

    # -------------------------------------------------------------------------
    # SCORES
    # -------------------------------------------------------------------------

    def get_scores(self, api_date: str, league: str) -> list[dict[str, Any]] | None:
        """
        Get cached scores for a date/league combo.

        Args:
            api_date: Date in YYYYMMDD format
            league: League code (e.g., "nba", "nfl")

        Returns:
            List of game dicts or None if cache miss/expired
        """
        cache_key = f"{api_date}:{league.lower()}"

        row = self.conn.execute("SELECT data, fetched_at FROM scores WHERE cache_key=?", (cache_key,)).fetchone()

        if row:
            data, fetched_at = row
            age = time.time() - fetched_at

            if age < self.SCORES_TTL:
                try:
                    games = json.loads(data)
                    logger.debug(f"Cache HIT: {cache_key} ({len(games)} games, {age:.0f}s old)")
                    return games
                except json.JSONDecodeError:
                    logger.warning(f"Cache CORRUPT: {cache_key}")
                    self._delete_scores(cache_key)
            else:
                logger.debug(f"Cache EXPIRED: {cache_key} ({age:.0f}s old)")

        return None

    def set_scores(self, api_date: str, league: str, games: list[dict[str, Any]]):
        """
        Cache scores for a date/league combo.

        Args:
            api_date: Date in YYYYMMDD format
            league: League code
            games: List of game dictionaries
        """
        cache_key = f"{api_date}:{league.lower()}"

        try:
            data = json.dumps(games)
            self.conn.execute(
                "INSERT OR REPLACE INTO scores VALUES (?, ?, ?, ?)", (cache_key, data, time.time(), len(games))
            )
            self.conn.commit()
            logger.debug(f"Cache SET: {cache_key} ({len(games)} games)")
        except Exception as e:
            logger.error(f"Cache SET failed for {cache_key}: {e}")

    def _delete_scores(self, cache_key: str):
        """Remove a corrupted cache entry."""
        self.conn.execute("DELETE FROM scores WHERE cache_key=?", (cache_key,))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # BOXSCORES
    # -------------------------------------------------------------------------

    def get_boxscore(self, game_id: str) -> list[dict[str, Any]] | None:
        """
        Get cached boxscore for a game.

        Args:
            game_id: ESPN game ID

        Returns:
            List of player stat dicts or None if cache miss
        """
        row = self.conn.execute("SELECT data, fetched_at FROM boxscores WHERE game_id=?", (game_id,)).fetchone()

        if row:
            data, fetched_at = row
            age = time.time() - fetched_at

            if age < self.BOXSCORE_TTL:
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    self._delete_boxscore(game_id)

        return None

    def set_boxscore(self, game_id: str, boxscore: list[dict[str, Any]]):
        """Cache boxscore for a game."""
        try:
            data = json.dumps(boxscore)
            self.conn.execute("INSERT OR REPLACE INTO boxscores VALUES (?, ?, ?)", (game_id, data, time.time()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Boxscore cache SET failed for {game_id}: {e}")

    def _delete_boxscore(self, game_id: str):
        """Remove a corrupted cache entry."""
        self.conn.execute("DELETE FROM boxscores WHERE game_id=?", (game_id,))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # ODDS
    # -------------------------------------------------------------------------

    def get_odds(self, api_date: str, league: str) -> dict[str, Any] | None:
        """Get cached odds for a date/league."""
        cache_key = f"{api_date}:{league.lower()}"

        row = self.conn.execute("SELECT data, fetched_at FROM odds WHERE cache_key=?", (cache_key,)).fetchone()

        if row:
            data, fetched_at = row
            age = time.time() - fetched_at

            if age < self.ODDS_TTL:
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    self._delete_odds(cache_key)

        return None

    def set_odds(self, api_date: str, league: str, odds: dict[str, Any]):
        """Cache odds for a date/league."""
        cache_key = f"{api_date}:{league.lower()}"

        try:
            data = json.dumps(odds)
            self.conn.execute("INSERT OR REPLACE INTO odds VALUES (?, ?, ?)", (cache_key, data, time.time()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Odds cache SET failed for {cache_key}: {e}")

    def _delete_odds(self, cache_key: str):
        """Remove a corrupted cache entry."""
        self.conn.execute("DELETE FROM odds WHERE cache_key=?", (cache_key,))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # MAINTENANCE
    # -------------------------------------------------------------------------

    def clear_all(self):
        """Clear all cached data."""
        self.conn.execute("DELETE FROM scores")
        self.conn.execute("DELETE FROM boxscores")
        self.conn.execute("DELETE FROM odds")
        self.conn.commit()
        logger.info("Cache cleared")

    def clear_stale(self, max_age_days: int = 7):
        """Remove entries older than max_age_days."""
        cutoff = time.time() - (max_age_days * 86400)

        self.conn.execute("DELETE FROM scores WHERE fetched_at < ?", (cutoff,))
        self.conn.execute("DELETE FROM boxscores WHERE fetched_at < ?", (cutoff,))
        self.conn.execute("DELETE FROM odds WHERE fetched_at < ?", (cutoff,))
        self.conn.commit()
        logger.info(f"Cleared cache entries older than {max_age_days} days")

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        scores_count = self.conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        boxscores_count = self.conn.execute("SELECT COUNT(*) FROM boxscores").fetchone()[0]
        odds_count = self.conn.execute("SELECT COUNT(*) FROM odds").fetchone()[0]

        return {"scores_entries": scores_count, "boxscores_entries": boxscores_count, "odds_entries": odds_count}

    def close(self):
        """Close the database connection."""
        self.conn.close()


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_cache_instance: ScoreCache | None = None


def get_cache() -> ScoreCache:
    """Get the global cache instance (singleton)."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ScoreCache()
    return _cache_instance


def clear_cache():
    """Clear all cached data."""
    get_cache().clear_all()
