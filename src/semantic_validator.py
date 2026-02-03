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
        if odds is not None:
            try:
                odds_val = float(odds)
                if odds_val > 5000 or odds_val < -5000:
                    return False, f"Impossible odds: {odds_val} (Range: -5000 to +5000)"
            except (ValueError, TypeError):
                pass

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

            # Construct pattern only once ideally, but here per pick is okay-ish or cache it?
            for team in SemanticValidator.VALID_TEAMS:
                # Use word boundary check, but handle apostrophes carefully
                # Innovation: Flexible team boundary
                if team in pick_lower:
                    idx = pick_lower.find(team)
                    # Check characters surrounding the match
                    is_start_ok = idx == 0 or not pick_lower[idx - 1].isalnum()
                    is_end_ok = idx + len(team) == len(pick_lower) or not pick_lower[idx + len(team)].isalnum()

                    if is_start_ok and is_end_ok:
                        found_team = True
                        break

            if not found_team:
                # US-013: Check for uppercase abbreviations (Case Sensitive)
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
                return False, f"No valid team name found in pick text: '{pick_text}'"

        # 2. Check Sport Consistency (if team name is known)
        for team, team_sport in SemanticValidator.TEAM_LEAGUES.items():
            if team.lower() in pick_text.lower():
                if sport != "Other" and sport != team_sport:
                    ambiguous = ["Giants", "Cardinals", "Jets", "Kings", "Panthers", "Rangers"]
                    if team not in ambiguous:
                        return False, f"Team '{team}' belongs to {team_sport}, but league is {sport}"

        # 2. Check Numeric Ranges
        if sport in SemanticValidator.RULES:
            rules = SemanticValidator.RULES[sport]

            # TOTALS
            if pick_type == "Total" and line is not None:
                prop_keywords = ["pts", "points", "reb", "ast", "goal", "score", "sog", "shot", "hit", "base"]
                is_prop_text = any(k in pick_text.lower() for k in prop_keywords)

                if not is_prop_text:
                    if line < rules["min_total"] or line > rules["max_total"]:
                        # INNOVATION: Proactive League Correction
                        # If the total matches another sport's range perfectly, switch to that sport.
                        for other_sport, other_rules in SemanticValidator.RULES.items():
                            if other_sport != sport:
                                if other_rules["min_total"] <= line <= other_rules["max_total"]:
                                    pick["league"] = other_sport
                                    return True, None  # Accept with corrected league

                        return (
                            False,
                            f"Suspicious Total: {line} for {sport} (Expected {rules['min_total']}-{rules['max_total']})",
                        )

            # SPREADS
            if pick_type == "Spread" and line is not None:
                if abs(line) > rules["max_spread"]:
                    return False, f"Suspicious Spread: {line} for {sport} (Expected max {rules['max_spread']})"

                # Check for "Moneyline-like" odds on a Spread
                if odds is not None:
                    try:
                        odds_val = float(odds)
                        if odds_val >= 300 or odds_val <= -500:
                            return False, f"Suspicious Odds for Spread: {odds_val} (Likely Moneyline or Prop)"
                    except (ValueError, TypeError):
                        pass

        # 3. Type Logic
        if pick_type == "Moneyline" and line is not None and abs(line) > 0:
            return False, f"Moneyline should not have a line/spread value: {line}"

        # 4. Prop Logic
        if pick_type == "Player Prop":
            if line is not None and line > 300:
                return False, f"Suspicious Player Prop Line: {line}"

            subject = pick.get("subject", "")
            for team in SemanticValidator.TEAM_LEAGUES.keys():
                if team.lower() in subject.lower():
                    # Relaxed: Allow team names in player prop subject (common Team Prop format)
                    pass

        return True, None

    @staticmethod
    def fix_pick(pick: dict[str, Any], reason: str) -> dict[str, Any]:
        """
        Attempt simple heuristic fixes before asking AI.
        """
        match = re.search(r"belongs to (\w+)", reason)
        if match:
            correct_sport = match.group(1)
            pick["league"] = correct_sport
            return pick

        match = re.search(r"likely (\w+) \(Range match\)", reason)
        if match:
            correct_sport = match.group(1)
            pick["league"] = correct_sport
            return pick

        return pick
