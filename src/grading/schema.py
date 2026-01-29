# src/grading/schema.py
"""
Data structures for the grading system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BetType(Enum):
    """Enumeration of supported bet types."""

    MONEYLINE = "Moneyline"
    SPREAD = "Spread"
    TOTAL = "Total"
    PLAYER_PROP = "Player Prop"
    TEAM_PROP = "Team Prop"
    GAME_PROP = "Game Prop"
    PERIOD = "Period"
    PARLAY = "Parlay"
    TEASER = "Teaser"
    FUTURE = "Future"
    UNKNOWN = "Unknown"


class GradeResult(Enum):
    """Enumeration of grading outcomes."""

    WIN = "WIN"
    LOSS = "LOSS"
    PUSH = "PUSH"
    PENDING = "PENDING"
    ERROR = "ERROR"
    VOID = "VOID"


@dataclass
class Pick:
    """
    Represents a parsed betting pick.
    """

    raw_text: str
    league: str
    date: str | None = None
    bet_type: BetType = BetType.UNKNOWN

    # Parsed components
    selection: str = ""
    line: float | None = None
    subject: str | None = None  # Player or Team name for props
    stat: str | None = None  # Stat key (e.g., 'pts', 'reb')
    is_over: bool | None = None  # True=Over, False=Under, None=N/A
    period: str | None = None  # '1H', '1Q', 'F5', etc.

    # Parlay legs (recursive)
    legs: list["Pick"] = field(default_factory=list)

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Original odds if provided
    odds: int | None = None


@dataclass
class GradedPick:
    """
    Result of grading a pick.
    """

    pick: Pick
    grade: GradeResult
    score_summary: str = ""
    details: str = ""
    confidence: float = 1.0
    game_id: str | None = None
    odds_filled: int | None = None

    # For parlays, individual leg results
    leg_results: list["GradedPick"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pick": self.pick.raw_text,
            "league": self.pick.league,
            "bet_type": self.pick.bet_type.value,
            "grade": self.grade.value,
            "score_summary": self.score_summary,
            "details": self.details,
            "confidence": self.confidence,
            "game_id": self.game_id,
            "odds_filled": self.odds_filled,
            "legs": [lr.to_dict() for lr in self.leg_results] if self.leg_results else None,
        }
