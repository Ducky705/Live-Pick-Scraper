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
    TEAM_PATTERN = re.compile(
        r"\b(?:Lakers|Celtics|Warriors|Heat|Nets|Bucks|76ers|Suns|Nuggets|Clippers|"
        r"Chiefs|Eagles|Cowboys|Bills|Ravens|49ers|Dolphins|Lions|"
        r"Yankees|Dodgers|Braves|Astros|Phillies|Padres|"
        r"Bruins|Maple Leafs|Rangers|Oilers|Panthers|Avalanche|"
        r"[A-Z][a-z]+\s+(?:vs?\.?|@)\s+[A-Z][a-z]+)\b",
        re.IGNORECASE,
    )

    ODDS_PATTERN = re.compile(r"[+-]\s*\d{3,4}(?!\d)")  # -110, +150, +1200
    LINE_PATTERN = re.compile(
        r"[-+]?\d+\.?\d*(?:\s*(?:pts?|points?|reb|ast|yds?|yards?|TDs?|games?))?",
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

        Args:
            ocr_text: Raw OCR text from image
            parsed_picks: List of picks extracted by AI
            caption: Optional message caption
            message_id: Optional message ID for logging

        Returns:
            ValidationResult indicating if extraction is complete
        """
        estimate = cls.estimate_pick_count(ocr_text, caption)
        actual_count = len(parsed_picks)

        # Calculate missing
        missing_count = max(0, estimate.estimated_count - actual_count)

        # Determine if valid
        # Allow some tolerance based on confidence
        # BUT: If we found 0 picks and expect > 0, we MUST reparse.
        if actual_count == 0 and estimate.estimated_count > 0:
            tolerance = 0
        else:
            tolerance = 1 if estimate.confidence > 0.6 else 2
        
        is_valid = missing_count <= tolerance

        # Determine if we should retry
        # Retry if missing > tolerance AND confidence is decent
        needs_reparse = (
            missing_count > tolerance
            and estimate.confidence > 0.4  # Lowered threshold to catch more misses
            and estimate.estimated_count >= 1
        )

        # Build reason
        if is_valid:
            reason = f"Extraction complete: {actual_count} picks (expected ~{estimate.estimated_count})"
        else:
            reason = f"Potential missing picks: got {actual_count}, expected ~{estimate.estimated_count}. Signals: {', '.join(estimate.signals[:3])}"

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
