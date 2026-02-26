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
        "NCAAB": {"min_total": 90.0, "max_total": 250.0, "max_spread": 45.0, "spread_odds_range": (-200, 200)},
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
            "max bet alert",
            "promo code",
            "discount",
            "unit sweep",
            "subscriber",
            "subscription",
            "bankroll",
            # Hallucination Blocklist (Common OCR artifacts/Capper names)
            "tokyo",
            "brandon",
            "whale",
            "safe play",
            "unit play",
        ]
        text_lower = pick_text.lower()
        if any(phrase in text_lower for phrase in garbage_phrases):
             # Exception: "Whale Play" might be followed by a real pick?
             # Usually the extractor puts the pick separately. If the pick TEXT itself contains this,
             # and it's short, it's likely garbage.
             return False, f"Garbage text detected: '{pick_text}' contains blocked phrase"

        # 1. Check Team Name Validity (US-012)
        # Ensure the pick references a known team (unless it's a Player Prop or Parlay)
        # This filters out noise like "Join my VIP" classified as a pick.
        # Only enforce for Team Sports where we have a complete DB.
        team_sports = {"NBA", "NFL", "NCAAF", "NCAAB", "NHL", "MLB"}

        # If league is NOT in team_sports, we skip this check (e.g. UFC, Tennis, Soccer, KBL, Hockey)
        # This is critical for niche leagues that don't have team name databases
        should_check_team = sport in team_sports

        # US-300: Fast-pass for non-standard leagues
        # Skip ALL strict validation for leagues not in our RULES dict
        # This prevents valid Tennis, Hockey, KBL, College Baseball picks from being dropped
        niche_leagues = {"TENNIS", "SOCCER", "HOCKEY", "KBL", "NBL", "WTA", "ATP",
                         "COLLEGE BASEBALL", "PGA", "F1", "EUROLEAGUE", "Other"}
        if sport.upper() in niche_leagues or sport not in SemanticValidator.RULES:
            # Only run garbage/URL/odds checks (already done above), skip range validation
            return True, None

        if should_check_team and pick_type in ("Spread", "Moneyline", "Total", "Team Total"):
            # SKIP if we already enriched the game (game_id or opponent found)
            # This handles cases like "Over 45.5" where enrichment found the game from context
            if pick.get("game_id") or pick.get("opponent"):
                pass  # Trust the enrichment
            else:
                # Check URL/Noise first
                if "http" in pick_text or "t.me" in pick_text:
                     return False, f"Pick text contains URL/Link: '{pick_text}'"

                # Check if any valid team name is present in the pick text
                found_team = False
                pick_lower = pick_text.lower()

                # Check for Player Prop keywords - if present, this might be a misclassified prop
                # In that case, we shouldn't enforce Team Name (matches "Kenneth Walker: Rush Yds")
                prop_keywords = [
                    "pts", "points", "reb", "ast", "goal", "score", "sog", "shot", "hit", "base",
                    "yds", "yards", "att", "attempts", "threes", "3pm", "tackles", "int", "pass",
                    "rush", "rec", "reception"
                ]
                is_prop_like = any(k in pick_lower for k in prop_keywords)

                if is_prop_like:
                    # It's likely a prop. Skip team name check.
                    found_team = True

                if not found_team:
                    for team in SemanticValidator.VALID_TEAMS:
                        # Use word boundary check to avoid partial matches
                        # Escape team name just in case
                        pattern = rf"\b{re.escape(team)}\b"
                        if re.search(pattern, pick_lower):
                            found_team = True
                            break

                if not found_team:
                    # US-013: Check for uppercase abbreviations (Case Sensitive)
                    abbrevs = [
                        "WAS", "MIN", "PHI", "DAL", "CHI", "MIA", "HOU", "TEN", "SF", "CIN",
                        "BUF", "PIT", "CLE", "IND", "JAX", "DET", "GB", "NE", "NY", "LV",
                        "KC", "LAC", "LAL", "GSW", "OKC", "NOP", "SAS", "MIL", "TOR", "BOS",
                        "ATL", "CHA", "ORL", "BKN", "DEN", "UTA", "POR", "SAC"
                    ]
                    if any(re.search(rf"\b{a}\b", pick_text) for a in abbrevs):
                        found_team = True

                if not found_team:
                    # Double check: Is it an "Over/Under" without team name?
                    return False, f"No valid team name found in pick text: '{pick_text}'"

        # 2. Check Sport Consistency (if team name is known)
        # Simple keyword check in pick text
        for team, team_sport in SemanticValidator.TEAM_LEAGUES.items():
            if team.lower() in pick_text.lower():
                # If mapped sport doesn't match pick sport (and pick sport isn't Other)
                if sport != "Other" and sport != team_sport:
                    # Skip ambiguous names for now
                    ambiguous = ["Giants", "Cardinals", "Jets", "Kings", "Panthers", "Rangers"]
                    if team not in ambiguous:
                        return False, f"Team '{team}' belongs to {team_sport}, but league is {sport}"

        # 3. Check Numeric Ranges
        if sport in SemanticValidator.RULES:
            rules = SemanticValidator.RULES[sport]

            # TOTALS
            if pick_type in ("Total", "Team Total") and line is not None:
                # Check for Team Total Indicator
                is_team_total = (
                    "team total" in pick_text.lower()
                    or "tt" in pick_text.lower()
                    or pick_type == "Team Total"
                    or "1h" in pick_text.lower()  # 1st Half totals are lower
                    or "2h" in pick_text.lower()
                    or "1q" in pick_text.lower()
                )

                # RELAXATION: Check for Player Prop keywords classified as Total
                prop_keywords = [
                    "pts", "points", "reb", "ast", "goal", "score", "sog", "shot", "hit", "base",
                    "yds", "yards", "att", "attempts", "threes", "3pm", "tackles", "int", "pass",
                    "rush", "rec", "reception"
                ]
                is_prop_text = any(k in pick_text.lower() for k in prop_keywords)

                if not is_prop_text:
                    if is_team_total:
                        # Relaxed limits for Team Totals / Halves
                        # Heuristic: Min is 0.25x of Game Total Min, Max is 0.85x of Game Total Max
                        tt_min = rules["min_total"] * 0.25
                        tt_max = rules["max_total"] * 0.85

                        if line < tt_min or line > tt_max:
                             # Should we stricter?
                             if sport == "NFL" and line < 6.0: # TD props?
                                 pass
                             elif line < tt_min or line > tt_max:
                                 return False, f"Suspicious Team Total: {line} for {sport} (Expected {tt_min}-{tt_max})"

                    elif line < rules["min_total"] or line > rules["max_total"]:
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
                if odds is not None:
                    if odds >= 300 or odds <= -500:
                        return False, f"Suspicious Odds for Spread: {odds} (Likely Moneyline or Prop)"

        # 4. Type Logic
        # If type is "Moneyline" but line is set (e.g. -5.5), that's inconsistent.
        # Auto-fix: If line looks like odds (e.g. -145), move to odds.
        if pick_type == "Moneyline" and line is not None and abs(line) > 0:
            if abs(line) >= 50:
                # Likely odds
                if odds is None or odds == 0:
                    pick["odds"] = int(line)
                pick["line"] = 0.0
            else:
                return False, f"Moneyline should not have a line/spread value: {line}"

        # 5. Prop Logic
        if pick_type == "Player Prop":
            if line is not None and line > 300:  # 300+ passing yards is possible, but >300 is high for others
                return False, f"Suspicious Player Prop Line: {line}"

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
