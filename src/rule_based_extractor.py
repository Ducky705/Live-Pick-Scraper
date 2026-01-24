"""
Rule-Based Extractor
====================
Reduces reliance on AI by attempting to extract betting picks using strict regex rules first.
If confident picks are found, the message is skipped from the expensive AI pipeline.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional

from src.grading.parser import PickParser
from src.grading.schema import Pick, BetType
from src.prompts.decoder import infer_league_from_entity, normalize_pick_format

logger = logging.getLogger(__name__)


class RuleBasedExtractor:
    """
    Extracts picks using deterministic rules and the existing PickParser.
    """

    @staticmethod
    def extract(
        messages: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process a list of messages and try to extract picks without AI.

        Args:
            messages: List of message objects

        Returns:
            Tuple of (extracted_picks, remaining_messages)
        """
        extracted_picks = []
        remaining_messages = []

        # Statistics
        total_msgs = len(messages)
        handled_msgs = 0

        for msg in messages:
            msg_id = msg.get("id")
            text = msg.get("text", "") or ""
            ocr_text = msg.get("ocr_text", "") or ""

            # Combine text sources
            full_text = text + "\n" + ocr_text

            # 1. Pre-filtering: If text is too short or clearly conversational, skip
            if len(full_text) < 10:
                remaining_messages.append(msg)
                continue

            # 2. Check for "Parlay" keyword - Multiline parlays are hard for regex
            # If we see "Parlay" but don't find a slash-separated parlay line,
            # it's likely a complex multi-line parlay. Defer to AI.
            has_parlay_keyword = "parlay" in full_text.lower()

            # 3. Line-by-line extraction
            lines = full_text.split("\n")
            msg_picks = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Skip likely noise
                if line.lower().startswith(("http", "www", "t.me", "@")):
                    continue
                if len(line) < 5:
                    continue

                # Attempt parse
                try:
                    # Check for keywords that strongly suggest a pick
                    if not RuleBasedExtractor._has_pick_indicators(line):
                        continue

                    # Infer league context from the line itself
                    league_hint = "Unknown"
                    inferred = infer_league_from_entity(line)
                    if inferred:
                        league_hint = inferred

                    parsed: Pick = PickParser.parse(line, league_hint)

                    if RuleBasedExtractor._is_valid_extraction(parsed):
                        # Normalize the pick string (e.g. "Jazz/Celtics O" -> "Jazz vs Celtics Over")
                        # This improves matching with Golden Set and consistency
                        normalized_selection = normalize_pick_format(
                            parsed.selection, parsed.bet_type.value, line, league_hint
                        )
                        parsed.selection = normalized_selection

                        # Convert to standard dict format
                        pick_dict = RuleBasedExtractor._to_pick_dict(
                            parsed, msg_id, line
                        )

                        # Add metadata
                        pick_dict["extraction_method"] = "rule_based"
                        pick_dict["confidence"] = 0.95

                        msg_picks.append(pick_dict)

                except Exception as e:
                    continue

            # 4. Decision Logic
            if msg_picks:
                # SPECIAL CASE: If we found individual picks but the text said "Parlay",
                # and we didn't find a "Parlay" type pick, we might have split a parlay.
                # In this case, it's safer to let AI handle it to group them.
                found_parlay_type = any(p["type"] == "Parlay" for p in msg_picks)

                if has_parlay_keyword and not found_parlay_type:
                    # Risk of splitting a parlay into straight bets.
                    # E.g. "2-Team Parlay:\nLakers ML\nHeat ML" -> Found 2 MLs.
                    # Fallback to AI for accuracy.
                    remaining_messages.append(msg)
                    logger.debug(
                        f"[RuleBased] Msg {msg_id} has 'Parlay' but found straight bets. Deferring to AI."
                    )
                else:
                    # Success
                    extracted_picks.extend(msg_picks)
                    handled_msgs += 1
                    logger.debug(
                        f"[RuleBased] Extracted {len(msg_picks)} picks from msg {msg_id}"
                    )
            else:
                remaining_messages.append(msg)

        logger.info(
            f"[RuleBased] Processed {handled_msgs}/{total_msgs} messages via Regex ({len(extracted_picks)} picks)"
        )
        return extracted_picks, remaining_messages

    @staticmethod
    def _has_pick_indicators(text: str) -> bool:
        """Check if line has strong betting indicators."""
        text_lower = text.lower()

        # Must have at least one numeric digit (lines, odds)
        if not any(c.isdigit() for c in text):
            return False

        # Check for specific patterns
        # 1. Odds/Spread pattern: -110, +3.5, -7
        # Needs to be careful not to match dates like 12-10
        if re.search(r"(?<!\d)[+-]\d{1,4}(?:\.\d+)?", text):
            return True

        # 2. Total pattern: Over 220
        if re.search(r"\b(o|u|over|under)\s*\d", text_lower):
            return True

        # 3. Prop pattern: Name: Stat
        if ":" in text and any(
            k in text_lower for k in ["pts", "reb", "ast", "threes", "yards", "td"]
        ):
            return True

        # 4. Explicit bet type keywords
        if any(k in text_lower for k in ["moneyline", "spread", "parlay"]):
            return True

        return False

    @staticmethod
    def _is_valid_extraction(pick: Pick) -> bool:
        """Verify if the parsed pick is high-quality."""
        if pick.bet_type == BetType.UNKNOWN:
            return False

        # If it's a spread/total, it MUST have a line
        if pick.bet_type in [BetType.SPREAD, BetType.TOTAL]:
            if pick.line is None:
                return False

        # If it's a prop, it MUST have a stat
        if pick.bet_type in [BetType.PLAYER_PROP, BetType.TEAM_PROP]:
            if not pick.stat:
                return False

        # If it's Moneyline, it usually doesn't have a line, but that's fine.

        # Reject if selection is too long (likely parsed a whole sentence as a team name)
        if len(pick.selection) > 60:
            return False

        # Reject if selection is too short
        if len(pick.selection) < 3:
            return False

        return True

    @staticmethod
    def _to_pick_dict(
        pick: Pick, message_id: str, original_text: str
    ) -> Dict[str, Any]:
        """Convert Pick object to the dictionary format used by the pipeline."""
        return {
            "message_id": message_id,
            "capper_name": "Unknown",  # Heuristic extractor doesn't know capper context easily
            "league": pick.league if pick.league != "Unknown" else "Other",
            "type": pick.bet_type.value,
            "pick": pick.selection,  # Use the cleaned selection from parser
            "odds": pick.odds,
            "units": 1.0,  # Default
            "reasoning": "Extracted via Rule-Based Regex",
            "_source_text": original_text,
            "confidence": 0.95,
        }
