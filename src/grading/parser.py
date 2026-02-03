# src/grading/parser.py
"""
Robust parser for pick strings according to pick_format.md specification.
"""

import re

from src.grading.constants import LEAGUE_ALIASES_MAP, PERIOD_PATTERNS, STAT_KEY_MAP
from src.grading.schema import BetType, Pick


class PickParser:
    """
    Parses raw pick strings into structured Pick objects.
    """

    @staticmethod
    def parse(text: str, league: str, date: str | None = None) -> Pick:
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

        # Clean up common prefixes like "1* " or "5% " or "GOW "
        # Keep it simple: remove digit+star or digit+% at start
        text = re.sub(r"^\d+\*?\s*", "", text)
        text = re.sub(r"^\d+%?\s*", "", text)

        # Remove timestamps like "10:05 pm" or "7:00 ET" to avoid confusing the Prop parser
        # Be careful not to remove "Over 2:30" (Prop?) No, usually Over 2.5
        # Regex: digit:digit followed optionally by am/pm/et/pt
        text = re.sub(
            r"\b\d{1,2}:\d{2}\s*(?:am|pm|et|est|pt|pst|ct|cst|mt|mst)?\b",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Clean up trailing punctuation (commas, etc)
        text = text.strip().rstrip(",").strip()

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
            # INNOVATION: Check if it's actually a Player Prop misclassified as a Total
            # e.g. "Zion Williamson Over 22.5 Points"
            prop_keywords = [
                "pts",
                "points",
                "reb",
                "rebounds",
                "ast",
                "assists",
                "threes",
                "3s",
                "yards",
                "td",
                "touchdown",
                "goal",
                "score",
                "sog",
                "shots",
                "shot",
                "hit",
                "hits",
                "base",
                "bases",
                "ks",
                "strikeouts",
                "scorer",
            ]
            if any(k in text.lower() for k in prop_keywords):
                # Attempt to parse as prop by injecting a colon before the Over/Under
                # Pattern: Find first occurrence of Over/Under/o/u/O/U
                match = re.search(r"\b(over|under|o/u|[ou])\b", text, re.IGNORECASE)
                if match:
                    subject = text[: match.start()].strip()
                    rest = text[match.start() :].strip()
                    # Synthetic colon injection
                    synthetic_text = f"{subject}: {rest}"
                    return PickParser._parse_prop(synthetic_text, league_norm, date)

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
            total_match = re.search(r"\b(over|under|o/u)\s*\d", text, re.IGNORECASE)
            if total_match:
                # Unless it's a parlay of totals (e.g. "Over 222.5 / Under 210")
                legs = text.split("/")
                # If both legs look like separate bets (have numbers/ML), it's a parlay
                is_parlay_of_totals = True
                for leg in legs:
                    if not re.search(r"\d|ML", leg):
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

            legs = [l.strip() for l in text.split("/") if l.strip()]
            if len(legs) >= 2:
                return True

        # Ampersand separator (less common for parlays, usually use /)
        if " & " in text:
            # Check for compound names first
            if any(name in text.lower() for name in ["william & mary", "texas a&m", "a & m", "w & m"]):
                return False

            legs = [l.strip() for l in text.split("&") if l.strip()]
            # Only treat as parlay if legs look like bets (have numbers or ML)
            valid_legs = 0
            for leg in legs:
                if re.search(r"\d|ML|Over|Under", leg, re.IGNORECASE):
                    valid_legs += 1

            if valid_legs >= 2:
                return True

        # Double Pipe separator (||)
        if "||" in text:
            return True

        # Plus separator ( + ) - Be careful not to match +100 or +3.5
        # Must be surrounded by spaces
        if " + " in text:
            # Check if it looks like "Pick A + Pick B"
            legs = [l.strip() for l in text.split("+") if l.strip()]
            valid_legs = 0
            for leg in legs:
                # Ignore if the leg is just a number (e.g. + 100)
                if leg.replace(".", "").isdigit():
                    continue
                if re.search(r"\d|ML|Over|Under", leg, re.IGNORECASE):
                    valid_legs += 1

            if valid_legs >= 2:
                return True

        return False

    @staticmethod
    def _is_teaser(text: str) -> bool:
        """Check if text is a teaser."""
        return "teaser" in text.lower()

    @staticmethod
    def _detect_period(text: str) -> str | None:
        """Detect if pick is a period bet and return period identifier."""
        text_lower = text.lower()

        # Check explicit patterns first
        for pattern, period_id in PERIOD_PATTERNS.items():
            if pattern in text_lower:
                return period_id

        # Regex for compact format: "1H", "1Q", "F5", etc. at start
        match = re.match(r"^([12][hq]|[1-4][qp]|f[135])\s+", text_lower)
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

        # Ignore if the colon is likely a time (e.g. 10:05)
        # Check if ALL colons are time-like
        # Regex for time: digit:digit
        # We want to know if there is a colon that is NOT a time
        # Split by colon
        parts = text.split(":")
        if len(parts) < 2:
            return False

        # Check around each split point (naive)
        # Better: find all colons and check surroundings
        non_time_colon_found = False
        for match in re.finditer(r":", text):
            start, end = match.span()
            # Check char before and after
            is_time = False
            if start > 0 and end < len(text):
                before = text[start - 1]
                after = text[end]
                if before.isdigit() and after.isdigit():
                    is_time = True

            if not is_time:
                non_time_colon_found = True
                break

        if not non_time_colon_found:
            return False

        return True

    @staticmethod
    def _is_total(text: str) -> bool:
        """Check if text is a total (over/under) bet."""
        text_lower = text.lower()
        return bool(re.search(r"\b(over|under|o/u)\b", text_lower) or re.search(r"\b[ou]\s+\d", text_lower))

    # -------------------------------------------------------------------------
    # Parsing Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_odds(text: str) -> tuple[int | None, str]:
        """
        Extract American odds from text and return (odds, clean_text).
        Looks for patterns like (-110), -110, +200.
        Usually 3 digits or more, or exactly -110/-105/etc.
        """
        text_clean = text
        odds = None

        # Pattern 1: Parentheses with odds, e.g. (-110), (+150), (- 120)
        paren_match = re.search(r"\(\s*([+-]?)\s*(\d{3,})\s*\)", text)
        if paren_match:
            try:
                # Reconstruct full number
                sign = paren_match.group(1) or ""
                num = paren_match.group(2)
                odds = int(sign + num)

                # Remove from text to avoid confusing line parser
                text_clean = text.replace(paren_match.group(0), "").strip()
                return odds, text_clean
            except ValueError:
                pass

        # Pattern 2: Standalone odds at end of string or separated
        # We look for [+-] and 3+ digits (e.g. -110, +1200, - 110)

        # Regex: boundary, optional sign, space?, 3+ digits, boundary
        matches = list(re.finditer(r"(?<!\d)([+-])\s*(\d{3,})(?!\d)", text_clean))
        if matches:
            # Take the last one as it's usually at the end
            m = matches[-1]
            try:
                sign = m.group(1)
                num = m.group(2)
                val = int(sign + num)

                # Heuristic: Odds are usually > 100 or < -100.
                if abs(val) >= 100:
                    odds = val
                    text_clean = text_clean[: m.start()] + text_clean[m.end() :]
                    text_clean = text_clean.strip()
            except ValueError:
                pass

        return odds, text_clean

    @staticmethod
    def _parse_parlay(text: str, league: str, date: str | None) -> Pick:
        """Parse a parlay into a Pick with legs."""
        # Determine separator
        if "||" in text:
            legs_raw = [l.strip() for l in text.split("||") if l.strip()]
        elif "/" in text:
            legs_raw = [l.strip() for l in text.split("/") if l.strip()]
        elif "&" in text:
            legs_raw = [l.strip() for l in text.split("&") if l.strip()]
        elif " + " in text:
            legs_raw = [l.strip() for l in text.split("+") if l.strip()]
        else:
            # Fallback (colon separated? e.g. "Parlay: Leg 1, Leg 2")
            # For now assume / as default to avoid breaking single lines
            legs_raw = [text]

        parlay_pick = Pick(
            raw_text=text,
            league=league.upper() if league != "other" else "Other",
            date=date,
            bet_type=BetType.PARLAY,
            selection=text,
        )

        all_same_league = True
        detected_leagues = set()

        for leg_text in legs_raw:
            # Extract (League) prefix if present
            leg_league = league
            clean_leg = leg_text

            match = re.match(r"\(([^)]+)\)\s*(.*)", leg_text)
            if match:
                prefix = match.group(1).lower()
                # Check if it's a teaser prefix like "Teaser 6pt NFL"
                if "teaser" in prefix:
                    # Extract league from teaser prefix
                    teaser_match = re.search(r"teaser\s+\d+pt\s+(\w+)", prefix)
                    if teaser_match:
                        leg_league = LEAGUE_ALIASES_MAP.get(
                            teaser_match.group(1).lower(), teaser_match.group(1).lower()
                        )
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
    def _parse_teaser(text: str, league: str, date: str | None) -> Pick:
        """Parse a teaser bet."""
        # Teasers are essentially parlays with adjusted lines
        # Format: "(Teaser 6pt NFL) Team -2.5 / (Teaser 6pt NFL) Team +8.5"
        pick = PickParser._parse_parlay(text, league, date)
        pick.bet_type = BetType.TEASER
        return pick

    @staticmethod
    def _parse_period_bet(text: str, league: str, date: str | None, period: str) -> Pick:
        """Parse a period-specific bet."""
        # Remove period prefix from text for further parsing
        text_clean = text
        text_lower = text.lower()

        # Remove period identifiers
        for pattern in PERIOD_PATTERNS.keys():
            if text_lower.startswith(pattern + " "):
                text_clean = text[len(pattern) :].strip()
                break

        # Remove compact period format (1H, 1Q, etc.)
        text_clean = re.sub(
            r"^[12][hq]\s+|^[1-4][qp]\s+|^f[135]\s+",
            "",
            text_clean,
            flags=re.IGNORECASE,
        ).strip()

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
            metadata={"underlying_type": underlying.bet_type.value},
            odds=underlying.odds,  # Propagate odds
        )

    @staticmethod
    def _parse_prop(text: str, league: str, date: str | None) -> Pick:
        """Parse a player or team prop bet."""
        # 0. Extract Odds first
        odds, text_clean = PickParser._extract_odds(text)

        parts = text_clean.split(":", 1)
        subject = parts[0].strip()
        rest = parts[1].strip()
        rest_lower = rest.lower()

        # Parse line and direction
        line = None
        is_over = None
        stat = rest

        # Pattern: "Pts Over 25.5" or "Over 25.5 Pts"
        line_match = re.search(r"(?:over|under|o/u|>|<)\s*(\d+\.?\d*)", rest_lower)
        if line_match:
            line = float(line_match.group(1))
            is_over = not ("under" in rest_lower or "<" in rest_lower or "u " in rest_lower)
            # Remove line part to get stat
            stat = re.sub(r"(?:over|under|o/u|>|<)\s*\d+\.?\d*", "", rest, flags=re.IGNORECASE).strip()
        else:
            # Try pattern: "25.5+ Pts" or "Pts 25.5+"
            plus_match = re.search(r"(\d+\.?\d*)\+", rest)
            if plus_match:
                line = float(plus_match.group(1))
                is_over = True
                stat = re.sub(r"\d+\.?\d*\+", "", rest).strip()

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
            is_over=is_over,
            odds=odds,
        )

    @staticmethod
    def _parse_total(text: str, league: str, date: str | None) -> Pick:
        """Parse a total (over/under) bet."""
        # 0. Extract Odds first
        odds, text_clean = PickParser._extract_odds(text)
        text_lower = text_clean.lower()

        # Extract line
        line_match = (
            re.search(r"(?:over|under|o/u)\s*(\d+\.?\d*)", text_lower)
            or re.search(r"(\d+\.?\d*)\s*(?:over|under|o/u)", text_lower)
            or re.search(r"\b[ou]\s*(\d+\.?\d*)", text_lower)
        )

        line = float(line_match.group(1)) if line_match else None
        is_over = not ("under" in text_lower or "u " in text_lower)

        return Pick(
            raw_text=text,
            league=league.upper(),
            date=date,
            bet_type=BetType.TOTAL,
            selection=text,
            line=line,
            is_over=is_over,
            odds=odds,
        )

    @staticmethod
    def _parse_spread_or_ml(text: str, league: str, date: str | None) -> Pick:
        """Parse as spread or moneyline."""
        # 0. Extract Odds first
        odds, text_clean = PickParser._extract_odds(text)
        text_lower = text_clean.lower()

        # Check for explicit ML
        is_ml = "ml" in text_lower or "moneyline" in text_lower

        # Check for spread number
        # Note: Since we extracted odds (>=100), remaining numbers are likely spreads (-5.5, +3, etc.)
        # Handle " - 5.5" or "-5.5" or "+3"
        spread_match = re.search(r"([+-])?\s*(\d+\.?\d*)", text_clean)

        found_spread_line = None
        if spread_match:
            # Enforce that it looks like a line:
            # 1. Has +/- sign
            # 2. Or is followed by 'pt' or 'point'
            # 3. Or text has 'spread'

            sign = spread_match.group(1) or ""
            num = spread_match.group(2)
            try:
                # If sign is "-", apply it. If empty or "+", it's positive.
                val = float(num)
                if sign == "-":
                    val = -val
            except ValueError:
                val = 0.0

            full_match = spread_match.group(0)
            has_sign = "+" in full_match or "-" in full_match

            # Filter out years? 2024. But odds extraction handles >100.
            # Filter out "76ers" -> "76"
            is_part_of_word = re.search(rf"{re.escape(full_match)}[a-zA-Z]", text_clean)

            if has_sign and not is_part_of_word:
                found_spread_line = val
            elif abs(val) < 50 and not is_part_of_word:
                # Likely a spread like "Lakers 5.5" (implied - or +?)
                # Dangerous to assume, but we have extracted odds so it's safer.
                pass

        if is_ml or (not found_spread_line and odds is not None) or (not found_spread_line and not is_ml):
            # Cases:
            # 1. Explicit ML -> ML
            # 2. No spread line found, but odds found (-175) -> ML (odds extracted above)
            # 3. No spread, no ml, no odds -> ML (default)
            return Pick(
                raw_text=text,
                league=league.upper(),
                date=date,
                bet_type=BetType.MONEYLINE,
                selection=text_clean.strip(),  # Cleaned text is the selection
                odds=odds,
            )
        else:
            return Pick(
                raw_text=text,
                league=league.upper(),
                date=date,
                bet_type=BetType.SPREAD,
                selection=text_clean.strip(),
                line=found_spread_line,
                odds=odds,
            )
