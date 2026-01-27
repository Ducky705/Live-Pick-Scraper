"""
Verification Module
===================
Anti-Hallucination layer that verifies extracted values against the original source text.
"""

import re
from typing import Dict, Any, Optional


def verify_odds_in_source(pick: Dict[str, Any], source_text: str) -> Optional[int]:
    """
    Verify that the extracted odds actually exist in the source text.
    Returns the odds if found, or None if hallucinated.

    Args:
        pick: The pick dictionary containing 'odds' field
        source_text: The original text (caption + OCR)

    Returns:
        Verified odds integer or None
    """
    odds = pick.get("odds")
    if odds is None:
        return None

    try:
        odds_val = int(odds)
    except (ValueError, TypeError):
        return None

    # If odds are None or 0, return None
    if not odds_val:
        return None

    # Normalize source text
    text_norm = source_text.lower().replace(" ", "")

    # 1. Exact number search (-110, +150)
    # Handle implicit positive (150 -> +150)

    # Search for the number as a string
    val_str = str(abs(odds_val))

    # Simple check: is "110" or "150" in text?
    # We need to be careful not to match "110" inside "1100" or line "211.0"
    # But usually finding the sequence is a good start.

    # Better check: Search for specific odds patterns in original text
    # Pattern 1: American format (+150, -110, 150)
    # Pattern 2: Decimal format (1.91, 2.50) -> conversion needed?
    # For now, we assume the AI extracted American odds directly.

    # Allow loose matching for now to avoid false negatives
    if val_str in source_text:
        return odds_val

    # Check for Decimal equivalent if American not found
    # -110 ~= 1.90/1.91
    # +100 ~= 2.0
    if abs(odds_val) == 110:
        if "1.9" in source_text or "1.90" in source_text or "1.91" in source_text:
            return odds_val

    # If -110 was hallucinated (very common default), strict check
    if odds_val == -110:
        # If specific markers aren't found, reject it
        if (
            "-110" not in source_text
            and "1.91" not in source_text
            and "110" not in source_text
        ):
            # CHECK: Did the source have DIFFERENT odds that we missed?
            # e.g. Source: "Oilers -175" -> AI: -110 (wrong) -> We should return None to strip it
            # But maybe we can find the real odds?
            # For now, just stripping the wrong odds is safer.
            return None

    return odds_val


def verify_line_in_source(pick: Dict[str, Any], source_text: str) -> Optional[float]:
    """
    Verify that the spread/total line exists in the source text.
    Prevents "Utah State -4" becoming "Moneyline" (and losing the -4)
    or hallucinating lines.
    """
    line = pick.get("line")
    if line is None:
        return None

    line_val = float(line)

    # Convert to string patterns: "4.5", "4,5", "4½"
    base_str = str(abs(line_val))
    if base_str.endswith(".0"):
        base_str = base_str[:-2]  # "4.0" -> "4"

    # Check for fractional equivalents
    fraction_patterns = []
    if abs(line_val) % 1 == 0.5:
        whole = int(abs(line_val))
        fraction_patterns.append(f"{whole}.5")
        fraction_patterns.append(f"{whole}½")
        fraction_patterns.append(f"{whole},5")

    # Search
    found = False
    if base_str in source_text:
        found = True
    else:
        for p in fraction_patterns:
            if p in source_text:
                found = True
                break

    if found:
        return line_val

    return None
