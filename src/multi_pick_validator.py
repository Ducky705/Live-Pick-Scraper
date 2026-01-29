# src/multi_pick_validator.py
"""
Multi-Pick Validator: Ensures all plays are extracted from betting cards.

Problem:
- A single betting card often contains 3-5 picks
- Current system might only extract 1-2 due to OCR issues or AI limitations
- No validation to detect missing picks

Solution:
- Analyze OCR text to estimate expected pick count
- Compare with actual parsed picks
- Flag discrepancies for re-processing
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class PickCountEstimate:
    """Estimated pick count from text analysis."""

    estimated_count: int
    confidence: float  # 0-1
    signals: List[str]  # What indicated this count
    has_parlay: bool
    has_multiple_cappers: bool


@dataclass
class ValidationResult:
    """Result of multi-pick validation."""

    is_valid: bool
    expected_count: int
    actual_count: int
    missing_count: int
    confidence: float
    needs_reparse: bool
    reason: str


class MultiPickValidator:
    """
    Validates that all picks from an image/message were extracted.

    Detection signals:
    1. Multiple team names in OCR text
    2. Multiple odds values (-110, +150, etc.)
    3. Multiple line values (-5.5, Over 220, etc.)
    4. Parlay indicators (3-leg, 4-leg, etc.)
    5. Bullet points or numbered lists
    6. Multiple checkmarks/emojis
    """

    # Patterns for detecting picks
    # Expanded Team Pattern to catch College/International teams (Capitalized words followed by spread/odds)
    TEAM_PATTERN = re.compile(
        r"\b(?:Lakers|Celtics|Warriors|Heat|Nets|Bucks|76ers|Suns|Nuggets|Clippers|"
        r"Chiefs|Eagles|Cowboys|Bills|Ravens|49ers|Dolphins|Lions|"
        r"Yankees|Dodgers|Braves|Astros|Phillies|Padres|"
        r"Bruins|Maple Leafs|Rangers|Oilers|Panthers|Avalanche|"
        r"Inter|Real Madrid|Barcelona|Man City|Arsenal|Liverpool|Chelsea|"
        r"Alabama|Georgia|Michigan|Ohio State|Texas|Tennessee|Purdue|UConn|Houston|"
        r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}(?=\s*(?:[+-]\d|vs|@|over|under|o|u)))\b",
        re.IGNORECASE,
    )

    ODDS_PATTERN = re.compile(r"[+-]\s*\d{3,4}(?!\d)")  # -110, +150, +1200
    # Enhanced Line Pattern to catch -2.5, +7, etc.
    LINE_PATTERN = re.compile(
        r"(?<!\d)[-+]?\d+\.?\d*(?:\s*(?:pts?|points?|reb|ast|yds?|yards?|TDs?|games?))?",
        re.IGNORECASE,
    )
    OVER_UNDER_PATTERN = re.compile(r"\b(?:over|under|o|u)\s*\d+\.?\d*", re.IGNORECASE)
    PARLAY_LEG_PATTERN = re.compile(
        r"(\d+)\s*(?:leg|pick|team|way)\s*(?:parlay)?", re.IGNORECASE
    )
    BULLET_PATTERN = re.compile(r"^[\s]*[-•●◦▪︎★✓✔☑✅❌]\s*\S", re.MULTILINE)
    NUMBERED_PATTERN = re.compile(r"^\s*\d+[.):\-]\s*\S", re.MULTILINE)
    CHECKMARK_PATTERN = re.compile(r"[✓✔☑✅❌⭕🔴🟢]")

    @classmethod
    def estimate_pick_count(cls, ocr_text: str, caption: str = "") -> PickCountEstimate:
        """
        Estimate expected number of picks from OCR text and caption.

        Args:
            ocr_text: Raw OCR text from image
            caption: Optional message caption

        Returns:
            PickCountEstimate with expected count and confidence
        """
        combined_text = f"{ocr_text}\n{caption}"
        signals = []
        estimates = []

        # 1. Count odds occurrences
        odds_matches = cls.ODDS_PATTERN.findall(combined_text)
        if odds_matches:
            signals.append(f"{len(odds_matches)} odds values")
            estimates.append(len(odds_matches))

        # 2. Count over/under patterns
        ou_matches = cls.OVER_UNDER_PATTERN.findall(combined_text)
        if ou_matches:
            signals.append(f"{len(ou_matches)} over/under patterns")
            # Each O/U is usually 1 pick
            estimates.append(len(ou_matches))

        # 3. Count bullet points
        bullet_matches = cls.BULLET_PATTERN.findall(combined_text)
        if bullet_matches:
            signals.append(f"{len(bullet_matches)} bullet points")
            estimates.append(len(bullet_matches))

        # 4. Count numbered items
        numbered_matches = cls.NUMBERED_PATTERN.findall(combined_text)
        if numbered_matches:
            signals.append(f"{len(numbered_matches)} numbered items")
            estimates.append(len(numbered_matches))

        # 5. Count checkmarks (often indicate picks)
        checkmarks = cls.CHECKMARK_PATTERN.findall(combined_text)
        if checkmarks:
            signals.append(f"{len(checkmarks)} checkmarks/status icons")
            estimates.append(len(checkmarks))

        # 6. Check for parlay with explicit leg count
        parlay_match = cls.PARLAY_LEG_PATTERN.search(combined_text)
        has_parlay = False
        if parlay_match:
            leg_count = int(parlay_match.group(1))
            signals.append(f"Parlay with {leg_count} legs")
            estimates.append(leg_count)
            has_parlay = True

        # 7. Check for multiple capper indicators
        capper_patterns = [
            r"@\w+",  # @mentions
            r"(?:^|\n)\s*[A-Z][a-z]+(?:Bets?|Picks?|Plays?|Cap(?:per)?s?)",  # CapperName patterns
        ]
        capper_count = 0
        for pattern in capper_patterns:
            matches = re.findall(pattern, combined_text)
            capper_count += len(matches)

        has_multiple_cappers = capper_count > 1
        if has_multiple_cappers:
            signals.append(f"{capper_count} potential cappers detected")

        # 8. Count Team Names (Significant for leagues like NBA/NFL/NHL)
        team_matches = cls.TEAM_PATTERN.findall(combined_text)
        if team_matches:
            signals.append(f"{len(team_matches)} team names")
            estimates.append(len(team_matches))

        # Calculate best estimate
        if not estimates:
            return PickCountEstimate(
                estimated_count=1,
                confidence=0.3,
                signals=["No clear pick indicators found"],
                has_parlay=False,
                has_multiple_cappers=False,
            )

        # Use median of estimates (more robust than mean)
        sorted_estimates = sorted(estimates)
        median_idx = len(sorted_estimates) // 2
        estimated_count = sorted_estimates[median_idx]

        # Confidence based on signal agreement
        agreement_ratio = sum(
            1 for e in estimates if abs(e - estimated_count) <= 1
        ) / len(estimates)
        confidence = min(0.9, 0.5 + (agreement_ratio * 0.4))

        return PickCountEstimate(
            estimated_count=max(1, estimated_count),
            confidence=confidence,
            signals=signals,
            has_parlay=has_parlay,
            has_multiple_cappers=has_multiple_cappers,
        )

    @classmethod
    def validate_extraction(
        cls,
        ocr_text: str,
        parsed_picks: List[Dict[str, Any]],
        caption: str = "",
        message_id: Optional[int] = None,
    ) -> ValidationResult:
        """
        Validate that extracted picks match expected count.
        """
        estimate = cls.estimate_pick_count(ocr_text, caption)
        actual_count = len(parsed_picks)

        # Calculate missing
        missing_count = max(0, estimate.estimated_count - actual_count)

        # Check for Uncovered Teams
        combined_text = f"{ocr_text}\n{caption}"
        team_matches = cls.TEAM_PATTERN.findall(combined_text)
        uncovered_teams = []
        
        parsed_teams = set()
        for p in parsed_picks:
            # Handle potential None values safely
            val = p.get("pick")
            sel = str(val).lower() if val is not None else ""
            parsed_teams.add(sel)

        for tm in team_matches:
            tm_lower = tm.lower()
            parts = tm_lower.split()
            found = False
            for part in parts:
                 if len(part) < 3: continue 
                 for p_sel in parsed_teams:
                     if part in p_sel:
                         found = True
                         break
                 if found: break
            if not found:
                uncovered_teams.append(tm)

        # Determine if valid
        # Allow some tolerance based on confidence
        if actual_count == 0 and estimate.estimated_count > 0:
            tolerance = 0
        else:
            # RELAXED TOLERANCE (US-006): Be less aggressive.
            # Only enforce strict count if we are VERY confident (> 0.85)
            tolerance = 0 if estimate.confidence > 0.85 else 1
        
        is_valid = missing_count <= tolerance

        # Determine if we should retry
        needs_reparse = (
            missing_count > tolerance
            and estimate.confidence > 0.7  # US-006: Increased threshold (was 0.5) to reduce FPs
            and estimate.estimated_count >= 1
        )

        reason_parts = []
        if is_valid:
            reason_parts.append(f"Extraction complete: {actual_count} picks (expected ~{estimate.estimated_count})")
        else:
            reason_parts.append(f"Potential missing picks: got {actual_count}, expected ~{estimate.estimated_count}. Signals: {', '.join(estimate.signals[:3])}")

        # Override validity if uncovered teams found
        if uncovered_teams:
             # US-006: Less aggressive validation
             # Only flag if we found ZERO picks. 
             # If we found some picks and are within tolerance, ignore uncovered teams (likely opponents).
             if actual_count == 0:
                 needs_reparse = True
                 reason_parts.append(f"Uncovered Teams (No picks): {len(uncovered_teams)} ({', '.join(uncovered_teams[:2])}...)")
             elif needs_reparse:
                 # Just add context if we are already reparsing
                 reason_parts.append(f"Uncovered Teams: {len(uncovered_teams)}")

        reason = " | ".join(reason_parts)

        if needs_reparse:
            logging.warning(f"[MultiPickValidator] Message {message_id}: {reason}")

        return ValidationResult(
            is_valid=is_valid,
            expected_count=estimate.estimated_count,
            actual_count=actual_count,
            missing_count=missing_count,
            confidence=estimate.confidence,
            needs_reparse=needs_reparse,
            reason=reason,
        )

    @classmethod
    def get_reparse_hint(
        cls, ocr_text: str, parsed_picks: List[Dict[str, Any]], caption: str = ""
    ) -> str:
        """
        Generate a hint for AI to re-parse with more attention.
        Used when validation fails.
        """
        estimate = cls.estimate_pick_count(ocr_text, caption)
        actual_count = len(parsed_picks)

        hint_lines = [
            "### REPARSE INSTRUCTION",
            f"Previous extraction found {actual_count} picks, but analysis suggests ~{estimate.estimated_count}.",
            "",
            "**INDICATORS FOUND:**",
        ]

        for signal in estimate.signals:
            hint_lines.append(f"- {signal}")

        hint_lines.extend(
            [
                "",
                "**INSTRUCTIONS:**",
                "1. Re-read the OCR text carefully",
                "2. Look for additional picks that may have been missed",
                "3. Check for multi-line picks that may have been truncated",
                "4. If this is a parlay, ensure ALL legs are extracted separately",
            ]
        )

        if estimate.has_parlay:
            hint_lines.append(
                "5. This appears to be a PARLAY - extract each leg as a separate pick"
            )

        if estimate.has_multiple_cappers:
            hint_lines.append(
                "6. Multiple cappers detected - ensure each capper's picks are attributed correctly"
            )

        return "\n".join(hint_lines)


def validate_and_flag_missing(
    messages: List[Dict[str, Any]], parsed_picks: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    Validate all messages and flag those with potentially missing picks.

    Args:
        messages: List of message dicts with 'id', 'ocr_texts', 'text'
        parsed_picks: List of all parsed picks with 'message_id'

    Returns:
        (picks, message_ids_needing_reparse)
    """
    # Group picks by message_id
    picks_by_message = {}
    for pick in parsed_picks:
        mid = pick.get("message_id")
        # Normalize to string for reliable matching
        mid_str = str(mid) if mid is not None else "None"

        if mid_str not in picks_by_message:
            picks_by_message[mid_str] = []
        picks_by_message[mid_str].append(pick)

    needs_reparse = []

    for msg in messages:
        mid = msg.get("id")
        mid_str = str(mid) if mid is not None else "None"

        ocr_texts = msg.get("ocr_texts", [])
        caption = msg.get("text", "")

        # Combine all OCR texts for this message
        combined_ocr = "\n---\n".join(ocr_texts) if ocr_texts else ""

        # Get picks for this message
        msg_picks = picks_by_message.get(mid_str, [])

        # Validate
        result = MultiPickValidator.validate_extraction(
            ocr_text=combined_ocr,
            parsed_picks=msg_picks,
            caption=caption,
            message_id=mid,
        )

        if result.needs_reparse:
            needs_reparse.append(mid_str) # Return string ID

    return parsed_picks, needs_reparse
