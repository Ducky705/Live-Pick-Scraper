"""
Rule-Based Extractor
====================
Reduces reliance on AI by attempting to extract betting picks using strict regex rules first.
If confident picks are found, the message is skipped from the expensive AI pipeline.
"""

import logging
import re
from typing import Any

from src.grading.parser import PickParser
from src.grading.schema import BetType, Pick
from src.prompts.decoder import infer_league_from_entity, normalize_pick_format

logger = logging.getLogger(__name__)


class RuleBasedExtractor:
    """
    Extracts picks using deterministic rules and the existing PickParser.
    """

    @staticmethod
    def extract(
        messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
            # If we see "Parlay" or "Teaser", it's likely a complex multi-line parlay.
            # Rule-Based extraction is poor at grouping these (it splits them).
            # STRATEGY: Defer ALL Parlays/Teasers to AI to ensure correct grouping.
            # ALSO: Check for "Team A + Team B" style headers (common in Telegram)
            has_plus_parlay = " + " in full_text and ("ML" in full_text or "Moneyline" in full_text)

            has_parlay_keyword = "parlay" in full_text.lower() or "teaser" in full_text.lower() or has_plus_parlay
            # EXPERIMENTAL: Don't skip on 'parlay' to allow extracting straight bets from mixed messages.
            # The AI fallback logic (if extraction is partial) should handle the complex parts if needed.
            # if has_parlay_keyword:
            #     remaining_messages.append(msg)
            #     logger.debug(
            #         f"[RuleBased] Msg {msg_id} has Parlay/Teaser keyword. Deferring to AI."
            #     )
            #     continue

            # 3. Line-by-line extraction
            lines = full_text.split("\n")
            msg_picks = []

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                i += 1

                if not line:
                    continue

                # CLEANUP: Remove common noise prefixes and bad characters
                # Remove "Pick:", "Selection:", "My Pick:"
                line = re.sub(
                    r"^(?:Pick|Selection|My Pick|My Play):\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                )
                # Remove numbering (e.g. "1. ", "1) ")
                line = re.sub(r"^\d+[\.\)]\s*", "", line)

                # Remove quotes and unicode garbage
                line = (
                    line.strip("\"'")
                    .replace("\u00a0", " ")
                    .replace("\u201c", '"')
                    .replace("\u201d", '"')  # Smart quotes
                    .replace("\u2018", "'")
                    .replace("\u2019", "'")  # Smart single quotes
                    .replace("\ufffd", "")
                    .replace("½", ".5")
                    .replace("¼", ".25")
                    .replace("¾", ".75")
                    # Replace unicode dashes with standard hyphen
                    .replace("\u2013", "-")  # En dash
                    .replace("\u2014", "-")  # Em dash
                    .replace("\u2212", "-")  # Minus sign
                )

                # NORMALIZE: Fix common OCR/Typo issues
                # 1. "MI" -> "ML" (common OCR error for Moneyline)
                line = re.sub(r"\bMI\b", "ML", line)
                # 2. Fix spaced odds/lines: "- 110" -> "-110", "+ 7" -> "+7"
                line = re.sub(r"(?<!\w)([+-])\s+(\d)", r"\1\2", line)
                # 3. Fix "U162" -> "Under 162", "o145" -> "Over 145"
                line = re.sub(r"\b([Uu])(\d+(\.\d+)?)", r"Under \2", line)
                line = re.sub(r"\b([Oo])(\d+(\.\d+)?)", r"Over \2", line)

                # 4. Fix "Money Line" -> "Moneyline" -> "ML"
                line = re.sub(r"Money\s*Line", "Moneyline", line, flags=re.IGNORECASE)

                # 5. Fix "Anytime Goal Scorer" -> "Name: Anytime Goal Scorer" (for Prop Parser)
                # If we see AGS pattern but no colon, inject one before the keyword
                if ":" not in line and re.search(r"\b(Anytime Goal Scorer|AGS|Score|Scorer)\b", line, re.IGNORECASE):
                    line = re.sub(
                        r"\s+(Anytime Goal Scorer|AGS|Anytime Goal|To Score)\b",
                        r": Anytime Goal Scorer",
                        line,
                        flags=re.IGNORECASE,
                    )

                # Remove emojis (simplistic regex) - Keep ASCII + standard punctuation
                line = re.sub(r"[^\x00-\x7F]+", "", line)

                # Clean specific noise patterns
                # 1. Remove everything after pipe |
                line = line.split("|")[0]

                # 2. Remove parenthetical commentary (e.g. "(risking 2u)")
                # Be careful not to remove (2u) or (-110)
                # Strategy: Remove (...) if it contains "risk", "win", "to win", "profit"
                if "(" in line:
                    line = re.sub(
                        r"\((?=[^)]*(?:risk|win|profit|analysis|writeup)).*?\)", "", line, flags=re.IGNORECASE
                    )

                line = line.strip()

                # Skip likely noise
                if line.lower().startswith(("http", "www", "t.me", "@")):
                    continue
                if len(line) < 5:
                    continue

                # --- MULTILINE MERGE LOGIC ---
                # Check if this line is likely a team/player name but lacks bet info,
                # and the NEXT line is just odds/line.
                if i < len(lines) and not RuleBasedExtractor._has_pick_indicators(line):
                    next_line = lines[i].strip()
                    # Clean next line slightly to check it
                    next_line_clean = re.sub(r"[^\x00-\x7F]+", "", next_line).strip()

                    # If next line looks like odds/line (e.g. "-110", "+145", "Over 220")
                    # Strict check: Start with +/-, or "Over/Under", or "ML"
                    is_continuation = False
                    if re.match(r"^[+-]\d+", next_line_clean):
                        is_continuation = True
                    elif re.match(r"^(Over|Under|O|U)\s*\d", next_line_clean, re.IGNORECASE):
                        is_continuation = True
                    elif re.match(r"^ML|Moneyline", next_line_clean, re.IGNORECASE):
                        is_continuation = True

                    if is_continuation:
                        # MERGE
                        line = f"{line} {next_line_clean}"
                        i += 1  # Consume next line

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

                    # Extract units before parsing (since parser cleans them)
                    units = RuleBasedExtractor._extract_units(line)

                    # AGGRESSIVE CLEANUP: Remove all parenthetical content before parsing
                    # We already extracted units, and 'PickParser' doesn't need the noise.
                    # This fixes "Texas ML (good to -2)" crashing the parser.
                    line_clean = re.sub(r"\(.*?\)", "", line).strip()

                    # Also remove trailing text after odds if separated by space?
                    # e.g. "Texas -3 -110 for the win" -> "Texas -3 -110"
                    # Hard to do reliably.

                    parsed: Pick = PickParser.parse(line_clean, league_hint)

                    if RuleBasedExtractor._is_valid_extraction(parsed):
                        # Normalize the pick string (e.g. "Jazz/Celtics O" -> "Jazz vs Celtics Over")
                        # This improves matching with Golden Set and consistency
                        normalized_selection = normalize_pick_format(
                            parsed.selection, parsed.bet_type.value, line, league_hint
                        )
                        parsed.selection = normalized_selection

                        # Convert to standard dict format
                        capper = msg.get("author") or "Unknown"

                        pick_dict = RuleBasedExtractor._to_pick_dict(
                            parsed, str(msg_id) if msg_id else "unknown", line, units
                        )
                        pick_dict["capper_name"] = capper

                        # Add metadata
                        pick_dict["extraction_method"] = "rule_based"
                        pick_dict["confidence"] = 8.5  # High confidence on 0-10 scale

                        msg_picks.append(pick_dict)

                except Exception:
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
                    logger.warning(f"[RuleBased] Msg {msg_id} has 'Parlay' but found straight bets. Deferring to AI.")
                else:
                    # Success
                    extracted_picks.extend(msg_picks)
                    handled_msgs += 1
                    logger.debug(f"[RuleBased] Extracted {len(msg_picks)} picks from msg {msg_id}")
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

        # 1. Explicit bet type keywords (Strongest signal)
        # If these are present, we might not need digits (e.g. "Lakers ML", "Parlay")
        # Added "ml" (must be whole word)
        if any(k in text_lower for k in ["moneyline", "spread", "parlay"]):
            return True
        if re.search(r"\bml\b", text_lower):
            return True

        # Must have at least one numeric digit (lines, odds)
        if not any(c.isdigit() for c in text):
            return False

        # Check for specific patterns
        # 2. Odds/Spread pattern: -110, +3.5, -7, - 110 (with space)
        # Needs to be careful not to match dates like 12-10
        if re.search(r"(?<!\d)[+-]\s*\d{1,4}(?:\.\d+)?", text):
            return True

        # 3. Total pattern: Over 220
        if re.search(r"\b(o|u|over|under)\s*\d", text_lower):
            return True

        # 4. Prop pattern: Name: Stat
        # Added goal/score/scorer patterns
        if ":" in text or "goal" in text_lower or "score" in text_lower:
            if any(
                k in text_lower
                for k in [
                    "pts",
                    "reb",
                    "ast",
                    "threes",
                    "yards",
                    "td",
                    "goal",
                    "score",
                    "scorer",
                ]
            ):
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
    def _extract_units(text: str) -> float:
        """Extract units from prefix like '3* ...' or suffix like '... 4u'"""
        # Prefix match: '3* ', '5% ', '10U '
        match = re.match(r"^(\d+(?:\.\d+)?)(?:\*|u|%|unit)\s*", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if val <= 20:
                    return val
            except ValueError:
                pass

        # Suffix match: '... 4u', '... (3U)'
        # Look for unit marker at end of string
        suffix_match = re.search(
            r"[\s\(](\d+(?:\.\d+)?)\s*(?:u|unit|%)[\)]?\s*[\u2b50\ufe0f]*$",
            text,
            re.IGNORECASE,
        )
        if suffix_match:
            try:
                val = float(suffix_match.group(1))
                if val <= 20:
                    return val
            except ValueError:
                pass

        return 1.0

    @staticmethod
    def _to_pick_dict(pick: Pick, message_id: str, original_text: str, units: float = 1.0) -> dict[str, Any]:
        """Convert Pick object to the dictionary format used by the pipeline."""
        return {
            "message_id": message_id,
            "capper_name": "Unknown",  # Heuristic extractor doesn't know capper context easily
            "league": pick.league if pick.league != "Unknown" else "Other",
            "type": pick.bet_type.value,
            "pick": pick.selection,  # Use the cleaned selection from parser
            "odds": pick.odds,
            "units": units,
            "line": pick.line,
            "is_over": pick.is_over,
            "stat": pick.stat,
            "reasoning": "Extracted via Rule-Based Regex",
            "_source_text": original_text,
            "confidence": 9.5,
        }
