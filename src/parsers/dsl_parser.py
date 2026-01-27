"""
DSL Parser for Sports Betting Extraction
========================================
Parses the "Compact Line Protocol" (CLP) output from the AI.

Format:
ID | CAPPER | LEAGUE | TYPE | PICK | ODDS | UNITS | REASONING

Example:
12345 | Dave | NBA | Spread | Lakers -5 | -110 | 1.0 | Spread bet
"""

import re
from typing import List, Dict, Any, Optional


def parse_dsl_lines(text: str) -> List[Dict[str, Any]]:
    """
    Parse a block of text containing DSL lines.
    Ignores lines that don't match the format (e.g. reasoning/thoughts).
    """
    picks = []

    # Regex for a valid line:
    # 1. ID (int)
    # 2. Capper (string)
    # 3. League (letters)
    # 4. Type (letters/spaces)
    # 5. Pick (anything)
    # 6. Odds (int, optional)
    # 7. Units (float/int, optional)
    # 8. Reasoning (optional)

    # We process line by line for robustness
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Handle Markdown headers (### ID|...)
        if line.startswith("#") and "|" in line:
            line = line.lstrip("#").strip()

        if not line or line.startswith("#") or line.startswith("//"):
            continue

        # Check for pipe count
        parts = [p.strip() for p in line.split("|")]

        # We expect at least 5 parts to be useful (id|capper|league|type|pick)
        if len(parts) < 5:
            continue

        # Parse fields
        message_id = parts[0]
        capper = parts[1]
        league = parts[2]
        bet_type = parts[3]
        pick_value = parts[4]

        odds = None
        units = 1.0
        reasoning = None

        # Odds
        if len(parts) >= 6:
            odds_str = parts[5]
            try:
                if odds_str and odds_str.lower() != "null":
                    # Remove non-numeric chars except -
                    clean = re.sub(r"[^\d\-]", "", odds_str)
                    if clean:
                        odds = int(float(clean))
            except ValueError:
                pass

        # Units
        if len(parts) >= 7:
            units_str = parts[6]
            try:
                if units_str and units_str.lower() != "null":
                    clean = re.sub(r"[^\d\.]", "", units_str)
                    if clean:
                        units = float(clean)
            except ValueError:
                pass

        # Reasoning
        if len(parts) >= 8:
            reasoning = parts[7]

        # Validation: League and Type should be relatively short
        if len(league) > 20 or len(bet_type) > 20:
            continue

        # Pick value shouldn't be empty
        if not pick_value:
            continue

        picks.append(
            {
                "id": message_id,  # Keep as string for safety initially
                "capper_name": capper,
                "league": league,
                "type": bet_type,
                "pick": pick_value,
                "odds": odds,
                "units": units,
                "reasoning": reasoning,
            }
        )

    return picks
