# src/grading/validity_filter.py
"""
Deterministic validity filter for picks.
Replaces the previous LLM-based filter with fast, reproducible heuristic rules.
"""

import logging
import re

from src.team_aliases import TEAM_ALIASES

logger = logging.getLogger(__name__)


class ValidityFilter:
    """
    Filters out 'nonsense' or invalid picks using deterministic rules.
    No LLM calls — fully reproducible and fast.
    """

    def __init__(self, model: str = "auto"):
        self.model = model
        # Flatten aliases for fast lookup
        self.known_aliases: set[str] = set()
        for aliases in TEAM_ALIASES.values():
            for alias in aliases:
                self.known_aliases.add(alias.lower())

    def is_valid(self, pick_text: str, league: str = "Unknown") -> tuple[bool, str]:
        """
        Determines if a pick text is valid enough to attempt grading.
        Returns (is_valid, reason).
        """
        if not pick_text or len(pick_text.strip()) < 3:
            return False, "Text too short"

        text = pick_text.strip()
        lower = text.lower()

        # -------------------------------------------------------------------
        # 1. Reject pure numbers / whitespace
        # -------------------------------------------------------------------
        if text.replace(".", "").replace("-", "").replace("+", "").replace(" ", "").isdigit():
            return False, "Numeric only"

        # -------------------------------------------------------------------
        # 2. Reject obvious marketing / garbage
        # -------------------------------------------------------------------
        garbage_phrases = [
            "vip", "subscribe", "link in bio", "dm for", "promo",
            "discount", "package", "guaranteed", "bankroll management",
            "sign up", "join now", "free access", "use code",
        ]
        if any(g in lower for g in garbage_phrases):
            return False, "Marketing/Garbage detected"

        # -------------------------------------------------------------------
        # 3. Reject URLs
        # -------------------------------------------------------------------
        if re.search(r"https?://", lower):
            return False, "URL detected"

        # -------------------------------------------------------------------
        # 4. Check for betting structure
        # -------------------------------------------------------------------
        # A valid pick should have AT LEAST ONE of:
        #   a) A number (spread, total, odds, line)
        #   b) A betting keyword (ML, Over, Under, etc.)
        #   c) A known team/player alias
        betting_keywords = [
            "over", "under", "ml", "moneyline", "spread",
            "pts", "reb", "ast", "o/u", "parlay", "teaser",
            "1h", "2h", "1q", "f5", "tt",
        ]
        has_digit = any(c.isdigit() for c in text)
        has_keyword = any(
            re.search(r'\b' + re.escape(k) + r'\b', lower)
            for k in betting_keywords
        )

        # Check known team aliases
        is_known_team = self._contains_known_team(lower)

        # -------------------------------------------------------------------
        # 5. Accept if any betting structure is present
        # -------------------------------------------------------------------
        if has_digit or has_keyword:
            return True, "Valid betting structure"

        if is_known_team:
            return True, "Known team alias detected"

        # -------------------------------------------------------------------
        # 6. Final: reject if no structure found
        # -------------------------------------------------------------------
        return False, "No betting structure (digits/keywords) found and not a known team alias"

    def _contains_known_team(self, lower_text: str) -> bool:
        """Check if the text contains any known team alias."""
        # Direct full-text match
        if lower_text in self.known_aliases:
            return True

        # Word-level match (3+ chars to avoid false positives)
        words = lower_text.split()
        for word in words:
            clean = word.strip("().,!?#*")
            if len(clean) >= 3 and clean in self.known_aliases:
                return True

        # Multi-word aliases (e.g., "iowa state", "nc state")
        for alias in self.known_aliases:
            if len(alias) > 3 and alias in lower_text:
                return True

        return False
