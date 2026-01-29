# src/grader.py
"""
Grading Module - Backward-compatible wrapper around V3 grading system.

This module provides the `grade_picks()` function as the public API.
All grading logic is delegated to the modular src.grading package.

De-Sloped: 2026-01-23
- Removed ~900 lines of legacy code (interpret_bet_result, _find_matching_game, etc.)
- All functionality now handled by src.grading.engine.GraderEngine
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def grade_picks(
    picks: list[dict[str, Any]], scores: list[dict[str, Any]], odds_data: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """
    Grades picks against scores using the V3 grading system.

    This is a backward-compatible wrapper that internally uses src.grading.

    Args:
        picks: List of pick dictionaries with keys:
            - pick (or p): The pick text (e.g., "Lakers -5.5")
            - league (or lg): League code (e.g., "NBA")
            - date: Optional date string
        scores: List of game score dictionaries from fetch_scores_for_date()
        odds_data: Optional dict from fetch_odds_for_date() (currently unused by V3)

    Returns:
        List of graded pick dictionaries with added fields:
            - result: "Win", "Loss", "Push", "Pending", or "Error"
            - score_summary: Human-readable score description
            - game_id: ESPN game ID (if matched)

    Example:
        >>> from src.grader import grade_picks
        >>> from src.score_fetcher import fetch_scores_for_date
        >>>
        >>> picks = [{"pick": "Lakers -5.5", "league": "NBA"}]
        >>> scores = fetch_scores_for_date("2026-01-20")
        >>> graded = grade_picks(picks, scores)
    """
    # Lazy imports to avoid circular dependencies and speed up module load
    from src.grading.engine import GraderEngine
    from src.grading.parser import PickParser

    graded_results: list[dict[str, Any]] = []
    engine = GraderEngine(scores)

    # Map V3 GradeResult enum values to legacy string format
    GRADE_MAP = {"WIN": "Win", "LOSS": "Loss", "PUSH": "Push", "PENDING": "Pending", "ERROR": "Error", "VOID": "Void"}

    for pick in picks:
        pick_obj = pick.copy()

        try:
            # Extract pick text and league (support both full and compact keys)
            bet_text = str(pick.get("pick") or pick.get("p") or "")
            league = str(pick.get("league") or pick.get("lg") or "other")
            pick_date = pick.get("date") or pick.get("pick_date")

            if not bet_text:
                pick_obj["result"] = "Error"
                pick_obj["score_summary"] = "Empty pick text"
                graded_results.append(pick_obj)
                continue

            # Parse and grade using V3 system
            parsed = PickParser.parse(bet_text, league, pick_date)
            graded = engine.grade(parsed)

            # Convert to legacy format
            pick_obj["result"] = GRADE_MAP.get(graded.grade.value, "Pending")
            pick_obj["score_summary"] = graded.score_summary or graded.details or ""

            # Keep game_id if available (useful for debugging/audit)
            if graded.game_id:
                pick_obj["game_id"] = graded.game_id

        except ValueError as e:
            # Parsing errors (invalid pick format)
            pick_obj["result"] = "Error"
            pick_obj["score_summary"] = f"Parse error: {e}"
            logger.warning(f"Parse error for pick '{pick.get('pick', '')}': {e}")

        except Exception as e:
            # Unexpected errors
            pick_obj["result"] = "Error"
            pick_obj["score_summary"] = str(e)
            logger.error(f"Grading error for pick '{pick.get('pick', '')}': {e}")

        graded_results.append(pick_obj)

    return graded_results
