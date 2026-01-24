# src/grading/parser.py
"""
Robust parser for pick strings according to pick_format.md specification.
"""

import re
from typing import Optional, List
from src.grading.schema import Pick, BetType
from src.grading.constants import LEAGUE_ALIASES_MAP, PERIOD_PATTERNS, STAT_KEY_MAP


class PickParser:
    """
    Parses raw pick strings into structured Pick objects.
    """

    @staticmethod
    def parse(text: str, league: str, date: Optional[str] = None) -> Pick:
        """
        Parse a pick string into a Pick object.
        
        Args:
            text: Raw pick string (e.g., "Lakers -5.5", "LeBron James: Pts Over 25.5")
            league: League code (e.g., "NBA", "NFL")
            date: Optional date string
            
        Returns:
            Parsed Pick object
        """
        text = text.strip()
        league_norm = LEAGUE_ALIASES_MAP.get(league.lower(), league.lower())

        # 1. PARLAY DETECTION (Slash separator or explicit Parlay marker)
        if PickParser._is_parlay(text):
            return PickParser._parse_parlay(text, league_norm, date)

        # 2. TEASER DETECTION
        if PickParser._is_teaser(text):
            return PickParser._parse_teaser(text, league_norm, date)

        # 3. PERIOD DETECTION (1H, 1Q, F5, etc.)
        period = PickParser._detect_period(text)
        if period:
            return PickParser._parse_period_bet(text, league_norm, date, period)

        # 4. PROP DETECTION (Colon separator: "Player: Stat Over X")
        if PickParser._is_prop(text):
            return PickParser._parse_prop(text, league_norm, date)

        # 5. TOTAL DETECTION (Over/Under without colon)
        if PickParser._is_total(text):
            return PickParser._parse_total(text, league_norm, date)

        # 6. SPREAD vs MONEYLINE
        return PickParser._parse_spread_or_ml(text, league_norm, date)

    # -------------------------------------------------------------------------
    # Detection Helpers
    # -------------------------------------------------------------------------
    
    @staticmethod
    def _is_parlay(text: str) -> bool:
        """Check if text is a parlay."""
        # Check for explicit Parlay marker
        if "parlay" in text.lower() and ":" in text:
            return True
            
        # Slash separator with multiple legs
        if "/" in text:
            # FIRST: Check if it's actually a total (e.g., "Lakers/Clippers Under 222.5")
            # If it has Over/Under AND a number, it's likely a total, not a parlay
            total_match = re.search(r'\b(over|under|o/u)\s*\d', text, re.IGNORECASE)
            if total_match:
                # Unless it's a parlay of totals (e.g. "Over 222.5 / Under 210")
                legs = text.split('/')
                # If both legs look like separate bets (have numbers/ML), it's a parlay
                is_parlay_of_totals = True
                for leg in legs:
                    if not re.search(r'\d|ML', leg):
                        is_parlay_of_totals = False
                        break
                if not is_parlay_of_totals:
                    return False
            
            # Check for compound team names (William & Mary)
            # Simple check: if splitting by / yields "William & Mary", don't treat as parlay
            # But usually compound names use "&", not "/". 
            # If text is "William & Mary ML", it won't have "/" so this block is skipped.
            # If text is "William / Mary ML", we should catch it.
            if "William / Mary" in text or "A / M" in text:
                return False

            legs = [l.strip() for l in text.split('/') if l.strip()]
            if len(legs) >= 2:
                return True
        
        # Ampersand separator (less common for parlays, usually use /)
        if " & " in text:
             # Check for compound names first
             if any(name in text.lower() for name in ["william & mary", "texas a&m", "a & m", "w & m"]):
                 return False
                 
             legs = [l.strip() for l in text.split('&') if l.strip()]
             # Only treat as parlay if legs look like bets (have numbers or ML)
             valid_legs = 0
             for leg in legs:
                 if re.search(r'\d|ML|Over|Under', leg, re.IGNORECASE):
                     valid_legs += 1
             
             if valid_legs >= 2:
                 return True

        return False

    @staticmethod
    def _is_teaser(text: str) -> bool:
        """Check if text is a teaser."""
        return "teaser" in text.lower()

    @staticmethod
    def _detect_period(text: str) -> Optional[str]:
        """Detect if pick is a period bet and return period identifier."""
        text_lower = text.lower()
        
        # Check explicit patterns first
        for pattern, period_id in PERIOD_PATTERNS.items():
            if pattern in text_lower:
                return period_id
        
        # Regex for compact format: "1H", "1Q", "F5", etc. at start
        match = re.match(r'^([12][hq]|[1-4][qp]|f[135])\s+', text_lower)
        if match:
            return PERIOD_PATTERNS.get(match.group(1), match.group(1).upper())
        
        return None

    @staticmethod
    def _is_prop(text: str) -> bool:
        """Check if text is a prop bet (Player: Stat format)."""
        # Must have colon but not be a Future like "Winner: Team"
        if ":" not in text:
            return False
        if "winner:" in text.lower():
            return False
        if "champion:" in text.lower():
            return False
        return True

    @staticmethod
    def _is_total(text: str) -> bool:
        """Check if text is a total (over/under) bet."""
        text_lower = text.lower()
        return bool(
            re.search(r'\b(over|under|o/u)\b', text_lower) or
            re.search(r'\b[ou]\s+\d', text_lower)
        )

    # -------------------------------------------------------------------------
    # Parsing Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    def _parse_parlay(text: str, league: str, date: Optional[str]) -> Pick:
        """Parse a parlay into a Pick with legs."""
        legs_raw = [l.strip() for l in text.split('/') if l.strip()]
        
        parlay_pick = Pick(
            raw_text=text,
            league=league.upper() if league != "other" else "Other",
            date=date,
            bet_type=BetType.PARLAY,
            selection=text
        )
        
        all_same_league = True
        detected_leagues = set()
        
        for leg_text in legs_raw:
            # Extract (League) prefix if present
            leg_league = league
            clean_leg = leg_text
            
            match = re.match(r'\(([^)]+)\)\s*(.*)', leg_text)
            if match:
                prefix = match.group(1).lower()
                # Check if it's a teaser prefix like "Teaser 6pt NFL"
                if "teaser" in prefix:
                    # Extract league from teaser prefix
                    teaser_match = re.search(r'teaser\s+\d+pt\s+(\w+)', prefix)
                    if teaser_match:
                        leg_league = LEAGUE_ALIASES_MAP.get(teaser_match.group(1).lower(), teaser_match.group(1).lower())
                else:
                    leg_league = LEAGUE_ALIASES_MAP.get(prefix, prefix)
                clean_leg = match.group(2)
            
            detected_leagues.add(leg_league)
            parlay_pick.legs.append(PickParser.parse(clean_leg, leg_league, date))
        
        # Set parlay league: "Other" if mixed, else specific league
        if len(detected_leagues) > 1:
            parlay_pick.league = "Other"
        elif len(detected_leagues) == 1:
            parlay_pick.league = list(detected_leagues)[0].upper()
        
        return parlay_pick

    @staticmethod
    def _parse_teaser(text: str, league: str, date: Optional[str]) -> Pick:
        """Parse a teaser bet."""
        # Teasers are essentially parlays with adjusted lines
        # Format: "(Teaser 6pt NFL) Team -2.5 / (Teaser 6pt NFL) Team +8.5"
        pick = PickParser._parse_parlay(text, league, date)
        pick.bet_type = BetType.TEASER
        return pick

    @staticmethod
    def _parse_period_bet(text: str, league: str, date: Optional[str], period: str) -> Pick:
        """Parse a period-specific bet."""
        # Remove period prefix from text for further parsing
        text_clean = text
        text_lower = text.lower()
        
        # Remove period identifiers
        for pattern in PERIOD_PATTERNS.keys():
            if text_lower.startswith(pattern + " "):
                text_clean = text[len(pattern):].strip()
                break
        
        # Remove compact period format (1H, 1Q, etc.)
        text_clean = re.sub(r'^[12][hq]\s+|^[1-4][qp]\s+|^f[135]\s+', '', text_clean, flags=re.IGNORECASE).strip()
        
        # Now parse the underlying bet type
        underlying = PickParser.parse(text_clean, league, date)
        
        # Override to Period type
        return Pick(
            raw_text=text,
            league=league.upper(),
            date=date,
            bet_type=BetType.PERIOD,
            selection=text,
            line=underlying.line,
            is_over=underlying.is_over,
            period=period,
            metadata={"underlying_type": underlying.bet_type.value}
        )

    @staticmethod
    def _parse_prop(text: str, league: str, date: Optional[str]) -> Pick:
        """Parse a player or team prop bet."""
        parts = text.split(':', 1)
        subject = parts[0].strip()
        rest = parts[1].strip()
        rest_lower = rest.lower()
        
        # Parse line and direction
        line = None
        is_over = None
        stat = rest
        
        # Pattern: "Pts Over 25.5" or "Over 25.5 Pts"
        line_match = re.search(r'(?:over|under|o/u|>|<)\s*(\d+\.?\d*)', rest_lower)
        if line_match:
            line = float(line_match.group(1))
            is_over = not ('under' in rest_lower or '<' in rest_lower or 'u ' in rest_lower)
            # Remove line part to get stat
            stat = re.sub(r'(?:over|under|o/u|>|<)\s*\d+\.?\d*', '', rest, flags=re.IGNORECASE).strip()
        else:
            # Try pattern: "25.5+ Pts" or "Pts 25.5+"
            plus_match = re.search(r'(\d+\.?\d*)\+', rest)
            if plus_match:
                line = float(plus_match.group(1))
                is_over = True
                stat = re.sub(r'\d+\.?\d*\+', '', rest).strip()
        
        # Normalize stat key
        stat_normalized = stat.lower().replace(" ", "").replace("+", "")
        
        # Map to standard stat keys
        stat_key = stat_normalized
        for key, aliases in STAT_KEY_MAP.items():
            if stat_normalized in [a.replace(" ", "") for a in aliases] or stat_normalized == key:
                stat_key = key
                break
        
        return Pick(
            raw_text=text,
            league=league.upper(),
            date=date,
            bet_type=BetType.PLAYER_PROP,
            selection=text,
            subject=subject,
            stat=stat_key,
            line=line,
            is_over=is_over
        )

    @staticmethod
    def _parse_total(text: str, league: str, date: Optional[str]) -> Pick:
        """Parse a total (over/under) bet."""
        text_lower = text.lower()
        
        # Extract line
        line_match = (
            re.search(r'(?:over|under|o/u)\s*(\d+\.?\d*)', text_lower) or
            re.search(r'(\d+\.?\d*)\s*(?:over|under|o/u)', text_lower) or
            re.search(r'\b[ou]\s*(\d+\.?\d*)', text_lower)
        )
        
        line = float(line_match.group(1)) if line_match else None
        is_over = not ('under' in text_lower or 'u ' in text_lower)
        
        return Pick(
            raw_text=text,
            league=league.upper(),
            date=date,
            bet_type=BetType.TOTAL,
            selection=text,
            line=line,
            is_over=is_over
        )

    @staticmethod
    def _parse_spread_or_ml(text: str, league: str, date: Optional[str]) -> Pick:
        """Parse as spread or moneyline."""
        text_lower = text.lower()
        
        # Check for explicit ML
        is_ml = 'ml' in text_lower or 'moneyline' in text_lower
        
        # Check for spread number
        spread_match = re.search(r'([+-]\d+\.?\d*)', text)
        
        if is_ml or not spread_match:
            return Pick(
                raw_text=text,
                league=league.upper(),
                date=date,
                bet_type=BetType.MONEYLINE,
                selection=text
            )
        else:
            return Pick(
                raw_text=text,
                league=league.upper(),
                date=date,
                bet_type=BetType.SPREAD,
                selection=text,
                line=float(spread_match.group(1))
            )
