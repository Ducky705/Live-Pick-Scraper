"""
Semantic Validator
==================
Enforces "common sense" rules for sports betting picks.
Prevents hallucinations like "Lakers +500 Spread" or "NFL Total Over 150".
"""

import re
from typing import Dict, Any, Optional, Tuple, List
import logging

class SemanticValidator:
    """
    Validates betting picks against sport-specific logic rules.
    """
    
    # Sport-specific thresholds
    RULES = {
        "NBA": {
            "min_total": 170.0,
            "max_total": 280.0,
            "max_spread": 25.0, # Rare to see spreads > 25
            "spread_odds_range": (-200, 200) # Standard spreads usually -110ish
        },
        "NFL": {
            "min_total": 30.0,
            "max_total": 70.0,
            "max_spread": 21.0,
            "spread_odds_range": (-200, 200)
        },
        "NCAAF": {
            "min_total": 30.0,
            "max_total": 90.0,
            "max_spread": 60.0, # College spreads can be huge
            "spread_odds_range": (-200, 200)
        },
        "NCAAB": {
            "min_total": 100.0,
            "max_total": 180.0,
            "max_spread": 40.0,
            "spread_odds_range": (-200, 200)
        },
        "NHL": {
            "min_total": 4.0,
            "max_total": 10.0,
            "max_spread": 3.5, # Puck line usually 1.5, maybe 2.5
            "spread_odds_range": (-300, 300) # Puck lines can be juice heavy
        },
        "MLB": {
            "min_total": 5.0,
            "max_total": 15.0,
            "max_spread": 4.5, # Run line usually 1.5
            "spread_odds_range": (-300, 300)
        }
    }

    # Common team names mapped to leagues for cross-checking
    TEAM_LEAGUES = {
        "Lakers": "NBA", "Celtics": "NBA", "Warriors": "NBA", "Knicks": "NBA",
        "Chiefs": "NFL", "Eagles": "NFL", "Cowboys": "NFL", "49ers": "NFL",
        "Dodgers": "MLB", "Yankees": "MLB", "Braves": "MLB",
        "Oilers": "NHL", "Maple Leafs": "NHL", "Bruins": "NHL",
        # Colleges (Jan/Feb = Basketball)
        "Penn State": "NCAAB", "Duke": "NCAAB", "UNC": "NCAAB", "Kansas": "NCAAB", "Purdue": "NCAAB",
        "Alabama": "NCAAB", "Houston": "NCAAB", "UConn": "NCAAB", "Tennessee": "NCAAB"
    }

    @staticmethod
    def validate(pick: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a single pick.
        Returns (is_valid, reason_if_invalid).
        """
        sport = pick.get("league", "Other")
        pick_type = pick.get("type", "Unknown")
        line = pick.get("line")
        odds = pick.get("odds")
        # Ensure pick_text is a string
        pick_text = str(pick.get("pick") or "")
        
        # 1. Check Sport Consistency (if team name is known)
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
                if line < rules["min_total"] or line > rules["max_total"]:
                    # Exception: Alternate lines or Props misclassified as Totals
                    return False, f"Suspicious Total: {line} for {sport} (Expected {rules['min_total']}-{rules['max_total']})"

            # SPREADS
            if pick_type == "Spread" and line is not None:
                if abs(line) > rules["max_spread"]:
                    return False, f"Suspicious Spread: {line} for {sport} (Expected max {rules['max_spread']})"
                
                # Check for "Moneyline-like" odds on a Spread
                # e.g., Spread -5 with +500 odds is extremely unlikely (unless it's a heavily alt line)
                if odds is not None:
                    min_odds, max_odds = rules["spread_odds_range"]
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
            if line is not None and line > 300: # 300+ passing yards is possible, but >500 is rare
                return False, f"Suspicious Player Prop Line: {line}"
            
            # Check for team names in player prop subject
            # e.g. Subject: "Lakers" Market: "Points" -> Should be Team Prop
            subject = pick.get("subject", "")
            for team in SemanticValidator.TEAM_LEAGUES.keys():
                if team.lower() in subject.lower():
                    return False, f"Team Name '{team}' found in Player Prop subject (Should be Team Prop?)"

        return True, None

    @staticmethod
    def fix_pick(pick: Dict[str, Any], reason: str) -> Dict[str, Any]:
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
            
        return pick
