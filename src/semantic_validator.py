"""
Semantic Validator
==================
Enforces "common sense" rules for sports betting picks.
Prevents hallucinations like "Lakers +500 Spread" or "NFL Total Over 150".
"""

import re
from typing import Any

from src.team_aliases import TEAM_ALIASES


class SemanticValidator:
    """
    Validates betting picks against sport-specific logic rules.
    """

    # Flatten TEAM_ALIASES for fast lookup
    # Normalize keys to lowercase for case-insensitive matching
    VALID_TEAMS: set[str] = set()
    for canonical, aliases in TEAM_ALIASES.items():
        VALID_TEAMS.add(canonical.lower())
        for alias in aliases:
            VALID_TEAMS.add(alias.lower())

    # Sport-specific thresholds
    RULES = {
        "NBA": {
            "min_total": 170.0,
            "max_total": 280.0,
            "max_spread": 25.0,  # Rare to see spreads > 25
            "spread_odds_range": (-200, 200),  # Standard spreads usually -110ish
        },
        "NFL": {"min_total": 30.0, "max_total": 70.0, "max_spread": 21.0, "spread_odds_range": (-200, 200)},
        "NCAAF": {
            "min_total": 30.0,
            "max_total": 90.0,
            "max_spread": 60.0,  # College spreads can be huge
            "spread_odds_range": (-200, 200),
        },
        "NCAAB": {"min_total": 100.0, "max_total": 180.0, "max_spread": 40.0, "spread_odds_range": (-200, 200)},
        "NHL": {
            "min_total": 4.0,
            "max_total": 10.0,
            "max_spread": 3.5,  # Puck line usually 1.5, maybe 2.5
            "spread_odds_range": (-300, 300),  # Puck lines can be juice heavy
        },
        "MLB": {
            "min_total": 5.0,
            "max_total": 15.0,
            "max_spread": 4.5,  # Run line usually 1.5
            "spread_odds_range": (-300, 300),
        },
    }

    # Common team names mapped to leagues for cross-checking
    TEAM_LEAGUES = {
        "Lakers": "NBA",
        "Celtics": "NBA",
        "Warriors": "NBA",
        "Knicks": "NBA",
        "Chiefs": "NFL",
        "Eagles": "NFL",
        "Cowboys": "NFL",
        "49ers": "NFL",
        "Dodgers": "MLB",
        "Yankees": "MLB",
        "Braves": "MLB",
        "Oilers": "NHL",
        "Maple Leafs": "NHL",
        "Bruins": "NHL",
        # Colleges (Jan/Feb = Basketball)
        "Penn State": "NCAAB",
        "Duke": "NCAAB",
        "UNC": "NCAAB",
        "Kansas": "NCAAB",
        "Purdue": "NCAAB",
        "Alabama": "NCAAB",
        "Houston": "NCAAB",
        "UConn": "NCAAB",
        "Tennessee": "NCAAB",
    }

    @staticmethod
    def validate(pick: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate a single pick.
        Returns (is_valid, reason_if_invalid).
        """
        sport = pick.get("league", "Other")

        # US-013: Normalize Leagues (CBB->NCAAB, CFB->NCAAF)
        # We do this here to ensure validation rules apply correctly
        if sport == "CBB":
            sport = "NCAAB"
            pick["league"] = "NCAAB"
        elif sport == "CFB":
            sport = "NCAAF"
            pick["league"] = "NCAAF"

        pick_type = pick.get("type", "Unknown")
        line = pick.get("line")
        odds = pick.get("odds")
        # Ensure pick_text is a string
        pick_text = str(pick.get("pick") or "")

        # 0. Check Odds (US-012)
        # Filter impossible odds (> +5000 or < -5000)
        # This catches OCR errors like "+12345" or hallucinated odds
        if odds is not None and isinstance(odds, (int, float)):
            try:
                odds_val = float(odds)
                if odds_val > 5000 or odds_val < -5000:
                    return False, f"Impossible odds: {odds_val} (Range: -5000 to +5000)"
            except ValueError:
                pass

        # 0.5. Garbage/Spam Detection (US-014)
        # Filter out common marketing/spam phrases that get extracted as picks
        garbage_phrases = [
            "profit made",
            "sweep tonight",
            "join vip",
            "link in bio",
            "dm for",
            "message me",
            "guaranteed win",
            "whale play",
            "max bet alert",
            "promo code",
            "discount",
            "unit sweep",
            "subscriber",
            "subscription",
            "bankroll",
        ]
        text_lower = pick_text.lower()
        if any(phrase in text_lower for phrase in garbage_phrases):
             # Exception: "Whale Play" might be followed by a real pick?
             # Usually the extractor puts the pick separately. If the pick TEXT itself contains this, 
             # and it's short, it's likely garbage.
             # If pick text > 50 chars, maybe it's "Whale Play: Lakers -5".
             # But Extractor should have cleaned it.
             return False, f"Garbage text detected: '{pick_text}' contains blocked phrase"

        # 1. Check Team Name Validity (US-012)
        # Ensure the pick references a known team (unless it's a Player Prop or Parlay)
        # This filters out noise like "Join my VIP" classified as a pick.
        # Only enforce for Team Sports where we have a complete DB.
        team_sports = {"NBA", "NFL", "NCAAF", "NCAAB", "NHL", "MLB"}

        # If league is unknown/other, we try to guess if it's a team sport?
        # Or just enforce it if it LOOKS like a team pick?
        # If league is NOT in team_sports, we skip this check (e.g. UFC, Tennis, Soccer if not in DB)
        should_check_team = sport in team_sports

        if should_check_team and pick_type in ("Spread", "Moneyline", "Total", "Team Total"):
            # Check if any valid team name is present in the pick text
            found_team = False
            pick_lower = pick_text.lower()

            # Optimization: Create a regex pattern for all teams?
            # Or just iterate and use regex for each?
            # Creating one giant regex is faster.
            # We can cache this pattern at class level if needed, but for now just do it.
            # Note: escaping regex special chars in team names

            # Construct pattern only once ideally, but here per pick is okay-ish or cache it?
            # Let's simple check: iterate and use \b

            for team in SemanticValidator.VALID_TEAMS:
                # Use word boundary check to avoid partial matches (e.g. "sun" in "sunday")
                # Pre-compile or use re.search
                # Escape team name just in case (e.g. "A's")
                pattern = rf"\b{re.escape(team)}\b"
                if re.search(pattern, pick_lower):
                    found_team = True
                    break

            if not found_team:
                # US-013: Check for uppercase abbreviations (Case Sensitive)
                # These are dangerous to add to TEAM_ALIASES (e.g. "WAS" vs "was", "MIN" vs "min")
                abbrevs = [
                    "WAS",
                    "MIN",
                    "PHI",
                    "DAL",
                    "CHI",
                    "MIA",
                    "HOU",
                    "TEN",
                    "SF",
                    "CIN",
                    "BUF",
                    "PIT",
                    "CLE",
                    "IND",
                    "JAX",
                    "DET",
                    "GB",
                    "NE",
                    "NY",
                    "LV",
                    "KC",
                    "LAC",
                    "LAL",
                    "GSW",
                    "OKC",
                    "NOP",
                    "SAS",
                    "MIL",
                    "TOR",
                    "BOS",
                    "ATL",
                    "CHA",
                    "ORL",
                    "BKN",
                    "DEN",
                    "UTA",
                    "POR",
                    "SAC",
                ]
                if any(re.search(rf"\b{a}\b", pick_text) for a in abbrevs):
                    found_team = True

            if not found_team:
                # Double check: Is it an "Over/Under" without team name?
                # If so, it's technically invalid as we don't know the game,
                # UNLESS it's a "Grand Salami" or specific league prop, but we'll flag it.
                return False, f"No valid team name found in pick text: '{pick_text}'"

        # 2. Check Sport Consistency (if team name is known)
        # Simple keyword check in pick text
        for team, team_sport in SemanticValidator.TEAM_LEAGUES.items():
            if team.lower() in pick_text.lower():
                # If mapped sport doesn't match pick sport (and pick sport isn't Other)
                if sport != "Other" and sport != team_sport:
                    # Allow NCAAF/NFL overlap in some contexts or manual override, but flag mismatch
                    # Exception: "Giants" (MLB/NFL), "Cardinals" (MLB/NFL), "Jets" (NFL/NHL), "Kings" (NBA/NHL)
                    # We skip ambiguous names for now
                    ambiguous = ["Giants", "Cardinals", "Jets", "Kings", "Panthers", "Rangers"]
                    if team not in ambiguous:
                        return False, f"Team '{team}' belongs to {team_sport}, but league is {sport}"

        # 2. Check Numeric Ranges
        if sport in SemanticValidator.RULES:
            rules = SemanticValidator.RULES[sport]

            # TOTALS
            if pick_type == "Total" and line is not None:
                # RELAXATION: Check for Player Prop keywords classified as Total
                prop_keywords = ["pts", "points", "reb", "ast", "goal", "score", "sog", "shot", "hit", "base"]
                is_prop_text = any(k in pick_text.lower() for k in prop_keywords)

                if not is_prop_text:
                    if line < rules["min_total"] or line > rules["max_total"]:
                        # Check for cross-sport match (e.g. NHL total in NBA)
                        for other_sport, other_rules in SemanticValidator.RULES.items():
                            if other_sport != sport:
                                if other_rules["min_total"] <= line <= other_rules["max_total"]:
                                    return False, f"Suspicious Total for {sport}, likely {other_sport} (Range match)"

                        # Exception: Alternate lines or Props misclassified as Totals
                        return (
                            False,
                            f"Suspicious Total: {line} for {sport} (Expected {rules['min_total']}-{rules['max_total']})",
                        )

            # SPREADS
            if pick_type == "Spread" and line is not None:
                if abs(line) > rules["max_spread"]:
                    return False, f"Suspicious Spread: {line} for {sport} (Expected max {rules['max_spread']})"

                # Check for "Moneyline-like" odds on a Spread
                # e.g., Spread -5 with +500 odds is extremely unlikely (unless it's a heavily alt line)
                if odds is not None:
                    # If odds are way outside normal spread juice (e.g. +400), it might be a ML or Prop
                    if odds >= 300 or odds <= -500:
                        return False, f"Suspicious Odds for Spread: {odds} (Likely Moneyline or Prop)"

        # 3. Type Logic
        # If type is "Moneyline" but line is set (e.g. -5.5), that's inconsistent
        if pick_type == "Moneyline" and line is not None and abs(line) > 0:
            # Some parsers might put moneyline odds in line field? No, line should be point spread.
            # Exception: "Pick'em" might be represented as 0
            return False, f"Moneyline should not have a line/spread value: {line}"

        # 4. Prop Logic
        if pick_type == "Player Prop":
            # If line is 0.5 or 1.5, that's fine.
            # If line is > 100 (except maybe rushing yards), suspicious for most sports
            if line is not None and line > 300:  # 300+ passing yards is possible, but >500 is rare
                return False, f"Suspicious Player Prop Line: {line}"

            # Check for team names in player prop subject
            # e.g. Subject: "Lakers" Market: "Points" -> Should be Team Prop
            subject = pick.get("subject", "")
            for team in SemanticValidator.TEAM_LEAGUES.keys():
                if team.lower() in subject.lower():
                    return False, f"Team Name '{team}' found in Player Prop subject (Should be Team Prop?)"

        return True, None

    @staticmethod
    def fix_pick(pick: dict[str, Any], reason: str) -> dict[str, Any]:
        """
        Attempt simple heuristic fixes before asking AI.
        """
        # Example: Mismatch Sport
        # If Reason is "Team 'Lakers' belongs to NBA", simply switch league
        match = re.search(r"belongs to (\w+)", reason)
        if match:
            correct_sport = match.group(1)
            pick["league"] = correct_sport
            return pick

        # Example: Range match logic
        match = re.search(r"likely (\w+) \(Range match\)", reason)
        if match:
            correct_sport = match.group(1)
            pick["league"] = correct_sport
            return pick

        return pick
