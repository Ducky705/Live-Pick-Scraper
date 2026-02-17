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
    def parse(pick_text: str, league: str = "Unknown", date: str | None = None) -> Pick:
        """
        Parse a pick string into a Pick object.

        Args:
            pick_text: Raw pick string
            league: League code
            date: Optional date string

        Returns:
            Parsed Pick object
        """
        from src.grading.universal_matcher import UniversalMatcher

        # Clean text
        text = pick_text.strip()
        
        # 0. Extract Units globally
        units_val, text = PickParser._extract_units(text)
        
        league_norm = LEAGUE_ALIASES_MAP.get(league.lower(), league.lower())

        # If league is unknown, try to infer from team names
        if league_norm in ["unknown", "other", ""]:
            inferred = UniversalMatcher().infer_league(text)
            if inferred:
                league_norm = inferred

        # 1. PARLAY DETECTION (Slash separator or explicit Parlay marker)
        if PickParser._is_parlay(text):
            pick = PickParser._parse_parlay(text, league_norm, date)
            if pick:
                pick.units = units_val
            return pick

        # 2. TEASER DETECTION
        if PickParser._is_teaser(text):
            pick = PickParser._parse_teaser(text, league_norm, date)
            if pick:
                pick.units = units_val
            return pick

        # 3. PROP DETECTION (Colon separator: "Player: Stat Over X")
        # Moved before Period detection to avoid "3P" (3 Pointers) being caught as Period "3P" (3rd Period)
        if PickParser._is_prop(text):
            # Guard: If the part before colon is a league/sport label, don't treat as prop
            if not PickParser._is_league_colon(text):
                pick = PickParser._parse_prop(text, league_norm, date)
                if pick:
                    pick.units = units_val
                return pick

        # 4. PERIOD DETECTION (1H, 1Q, F5, etc.)
        period = PickParser._detect_period(text)
        if period:
            # F6 Guard: If period code collides with a stat keyword, prefer prop/total
            # e.g. "3P" could mean 3rd Period OR 3-Pointers in basketball context
            stat_collision_periods = {"3P"}
            is_stat_collision = (
                period in stat_collision_periods
                and PickParser._has_prop_structure(text)
            )
            if not is_stat_collision:
                # Infer League from Period if Unknown
                if league_norm in ["unknown", "", "other"]:
                    if period in ["1Q", "2Q", "3Q", "4Q"]:
                        league_norm = "nba"
                pick = PickParser._parse_period_bet(text, league_norm, date, period)
                if pick:
                    pick.units = units_val
                return pick

        # 5. TOTAL DETECTION (Over/Under without colon)
        if PickParser._is_total(text):
            # INNOVATION: Check if it's actually a Player Prop misclassified as a Total
            # e.g. "Zion Williamson Over 22.5 Points"
            # NOTE: "goal", "goals", "score", "scorer" are REMOVED from this list.
            # In context "Denmark/USA O 6.5 Goals", "goals" refers to a GAME TOTAL,
            # not a player prop. Same with "sog" (shots on goal) when used with
            # team/game context. Keep only unambiguous individual stat keywords.
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
                "hit",
                "hits",
                "base",
                "bases",
                "strikeouts",
            ]

            
            # Use regex to avoid partial matches (e.g. "ks" in "Knicks")
            prop_regex = r"\b(" + "|".join(re.escape(k) for k in prop_keywords) + r")\b"
            
            if re.search(prop_regex, text, re.IGNORECASE):
                # Attempt to parse as prop by injecting a colon before the Over/Under
                # Pattern: Find first occurrence of Over/Under/o/u/O/U
                match = re.search(r"\b(over|under|o/u|[ou])\b", text, re.IGNORECASE)
                if match:
                    subject = text[: match.start()].strip()
                    rest = text[match.start() :].strip()
                    # Synthetic colon injection
                    synthetic_text = f"{subject}: {rest}"
                    pick = PickParser._parse_prop(synthetic_text, league_norm, date)
                    if pick:
                        pick.units = units_val
                    return pick

            pick = PickParser._parse_total(text, league_norm, date)
            if pick:
                pick.units = units_val
            return pick

        # --- ADAPTIVE PARSING LAYER ---
        from src.parsing.fingerprinter import Fingerprinter
        from src.parsing.registry import TemplateRegistry
        
        # Instantiate Registry (Singleton-ish typically, but load cheap here)
        # TODO: Move to class level or singleton to avoid reload
        registry = TemplateRegistry()
        
        fp = Fingerprinter.fingerprint(text)
        tmpl = registry.get_template(fp)
        
        if tmpl:
            # FAST PATH: Logic from Template
            pattern, mapping = tmpl
            match = pattern.match(text)
            if match:
                # Construct Pick from Match
                groups = match.groupdict()
                
                # Default Fields
                selection = groups.get(mapping.get("selection", "selection"), text)
                line_val = None
                odds_val = None
                
                if "line" in groups and groups["line"]:
                    try:
                        line_val = float(groups["line"])
                    except: pass
                    
                if "odds" in groups and groups["odds"]:
                    try:
                        odds_val = int(groups["odds"])
                    except: pass
                    
                units_val = None
                if "units" in groups and groups["units"]:
                    units_val = groups["units"]
                    
                # Simplistic return for now - assumes Spread/ML/Total based on fields
                pick = Pick(
                    raw_text=text,
                    league=league,
                    date=date,
                    bet_type=BetType.SPREAD if line_val else BetType.MONEYLINE,
                    selection=selection,
                    line=line_val,
                    odds=odds_val,
                    units=units_val
                )
                
                # Format Compliance: Ensure "Team ML" format
                if pick.bet_type == BetType.MONEYLINE:
                    if "ml" not in pick.selection.lower() and "moneyline" not in pick.selection.lower():
                        if not any(c.isdigit() for c in pick.selection):
                             pick.selection = f"{pick.selection} ML"
                
                if pick:
                     pick.units = units_val
                return pick
        else:
            # AUTO-LEARNING (Cache Miss)
            # Only attempt to learn if text seems "pick-like" (length > 5, has numbers?)
            # Heuristic: Don't learn extremely short or long texts
            if 5 < len(text) < 200:
                # OPTIMIZATION: Only attempt to learn if text contains at least one digit.
                # All valid bets (Odds, Lines, Units) contain digits.
                if not re.search(r"\d", text):
                    return None

                # LEARNER DISABLED
                pass

        # ------------------------------
        
        # 6. SPREAD vs MONEYLINE
        pick = PickParser._parse_spread_or_ml(text, league_norm, date)
        if pick:
            pick.units = units_val
        return pick

    # -------------------------------------------------------------------------
    # Detection Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_parlay(text: str) -> bool:
        """Check if text is a parlay."""
        # Check for explicit Parlay marker
        # Fix: Ensure "parlay" is followed by colon, not just somewhere in text
        if re.search(r"\bparlay\b.*:", text, re.IGNORECASE):
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

        # Check explicit long patterns first ("first half", "1st half", etc.)
        for pattern, period_id in PERIOD_PATTERNS.items():
            # Only match multi-word patterns via substring; single patterns via word boundary
            if " " in pattern:
                if pattern in text_lower:
                    return period_id
            else:
                # Use word boundary to avoid false positives (e.g. "f1" in "diff15")
                if re.search(r'\b' + re.escape(pattern) + r'\b', text_lower):
                    return period_id

        # Regex for compact format: "1H", "1Q", "F5", etc. at start of string only
        match = re.match(r"^([12][hq]|[1-4][qp]|f[135])\s+", text_lower)
        if match:
            return PERIOD_PATTERNS.get(match.group(1), match.group(1).upper())

        return None

    @staticmethod
    def _is_prop(text: str) -> bool:
        """Check if text is a prop bet (Player: Stat format)."""
        # Must have colon
        if ":" not in text:
            return False

        # Reject futures
        lower = text.lower()
        if "winner:" in lower or "champion:" in lower:
            return False

        # Ignore if the colon is likely a time (e.g. 10:05)
        non_time_colon_found = False
        for match in re.finditer(r":", text):
            start, end = match.span()
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
    def _is_league_colon(text: str) -> bool:
        """
        Check if the colon in text is a league/sport label prefix.
        e.g. "NCAAB: Iowa State -7" or "CBB: Duke -12.5"
        These should NOT be parsed as props.
        """
        parts = text.split(":", 1)
        if len(parts) < 2:
            return False
        prefix = parts[0].strip().lower()

        # Known league/sport labels that appear before colons
        league_labels = {
            "ncaab", "ncaaf", "nba", "nfl", "nhl", "mlb",
            "cbb", "cfb", "atp", "wta", "ufc", "pga",
            "epl", "mls", "ucl", "hockey", "soccer", "tennis",
            "baseball", "basketball", "football",
            "olympic hockey", "college basketball",
            "college baseball", "college football",
            "ncaab plays", "nba plays", "nfl plays",
            "cbb plays", "hockey plays", "ncaab add",
            "cbb add", "cbb adds", "ncaab adds",
            "potd", "ai potd", "parlay",
        }
        return prefix in league_labels

    @staticmethod
    def _has_prop_structure(text: str) -> bool:
        """
        Check if text has player-prop-like structure:
        contains Over/Under + a stat keyword like pts/reb/ast.
        """
        lower = text.lower()
        has_ou = bool(re.search(r'\b(over|under)\b', lower))
        stat_kw = ["pts", "points", "reb", "rebounds", "ast", "assists",
                   "threes", "3s", "yards", "td", "touchdown",
                   "strikeouts", "hits", "bases"]
        has_stat = any(re.search(r'\b' + re.escape(k) + r'\b', lower) for k in stat_kw)
        return has_ou and has_stat

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
                # Fix: replace only the first occurrence to avoid destroying duplicates in other parts of text
                text_clean = text.replace(paren_match.group(0), "", 1).strip()
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
    def _extract_units(text: str) -> tuple[str | None, str]:
        """
        Extract units from text (e.g. '2u', '(2U)', '1.5 units').
        Returns (units, clean_text).
        """
        text_clean = text
        units = None
        
        # Regex for units: 
        # Optional parens, number, "u" or "unit(s)", optional parens
        # Case insensitive
        match = re.search(r"(?:\(|^|\s)(\d+(?:\.\d+)?)\s*(?:u|units?)(?:\)|$|\s)", text, re.IGNORECASE)
        
        if match:
             try:
                 units = match.group(1)
                 # Remove the full match from text
                 text_clean = text.replace(match.group(0).strip(), "", 1).strip()
                 # Clean up any Double Spaces
                 text_clean = re.sub(r"\s+", " ", text_clean).strip()
             except:
                 pass
                 
        return units, text_clean

    @staticmethod
    def _parse_parlay(text: str, league: str, date: str | None) -> Pick:
        """Parse a parlay into a Pick with legs."""
        # Clean up "Parlay:" prefix if present
        if "parlay" in text.lower() and ":" in text:
             # Remove "Parlay:" or "Parlay :" prefix
             text = re.sub(r"^parlay\s*:\s*", "", text, flags=re.IGNORECASE)

        # Determine separator
        if "||" in text:
            legs_raw = [l.strip() for l in text.split("||") if l.strip()]
        elif "/" in text:
            legs_raw = [l.strip() for l in text.split("/") if l.strip()]
        elif "&" in text:
            legs_raw = [l.strip() for l in text.split("&") if l.strip()]
        elif " + " in text:
            legs_raw = [l.strip() for l in text.split("+") if l.strip()]
        elif "," in text:
             # Comma Support for explicitly marked parlays
            legs_raw = [l.strip() for l in text.split(",") if l.strip()]
        else:
            # Fallback
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

        # Recursion Guard: If we didn't split and didn't strip anything, parsing the same text again causes infinite loop.
        if len(legs_raw) == 1 and legs_raw[0] == text:
            # We failed to split the parlay. Fallback to spread/ML parse to avoid recursion.
            return PickParser._parse_spread_or_ml(text, league, date)

        for leg_text in legs_raw:
            # Recursion Guard 2: If leg text is almost strictly shorter than original, it's safe.
            # But if it's identical, skip.
            if len(leg_text) >= len(text) and leg_text == text:
                 return PickParser._parse_spread_or_ml(text, league, date)

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

        # Remove period identifiers (handle anywhere in string)
        for pattern in PERIOD_PATTERNS.keys():
            pattern_regex = r"\b" + re.escape(pattern) + r"\b"
            if re.search(pattern_regex, text_lower):
                text_clean = re.sub(pattern_regex, "", text, count=1, flags=re.IGNORECASE).strip()
                # Clean double spaces
                text_clean = re.sub(r"\s+", " ", text_clean)
                break

        # Remove compact period format (1H, 1Q, etc.) if still present (e.g. at start without space)
        # The above loop handles "2h " or " 2h ", but maybe not "2hPatriots" (unlikely with \b)
        # Keep the start regex as fallback or cleanup
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
        
        # Pattern: "Pts Over 25.5" or "Over 25.5 Pts" or "O 25.5"
        # Added [ou] to support single letter abbreviations
        line_match = re.search(r"(?:over|under|o/u|[ou]|>|<)\s*(\d+\.?\d*)", rest_lower)
        if line_match:
            line = float(line_match.group(1))
            is_over = not ("under" in rest_lower or "<" in rest_lower or re.search(r"\bu\b", rest_lower))
            # Remove line part to get stat
            stat = re.sub(r"(?:over|under|o/u|[ou]|>|<)\s*\d+\.?\d*", "", rest, flags=re.IGNORECASE).strip()
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
        is_ml = bool(re.search(r'\bml\b|\bmoneyline\b', text_lower))

        # Check for spread number
        # Note: Since we extracted odds (>=100), remaining numbers are likely spreads (-5.5, +3, etc.)
        # Use a more specific regex that requires +/- sign for spread detection
        spread_match = re.search(r'(?<![\w.])([+-])\s*(\d+\.?\d*)(?![\w])', text_clean)

        found_spread_line = None
        if spread_match:
            sign = spread_match.group(1)
            num = spread_match.group(2)
            try:
                val = float(num)
                if sign == "-":
                    val = -val
            except ValueError:
                val = 0.0

            # Filter out "76ers" -> "76" — check if followed by letters
            full_match = spread_match.group(0)
            end_pos = spread_match.end()
            is_part_of_word = (end_pos < len(text_clean) and text_clean[end_pos].isalpha())

            if not is_part_of_word:
                found_spread_line = val

        if is_ml or (not found_spread_line):
            # Moneyline: explicit ML, or no spread number found
            selection = text_clean.strip()
            # Append ML only if not already present and selection is a team name (no digits)
            if "ml" not in selection.lower() and "moneyline" not in selection.lower():
                if not any(c.isdigit() for c in selection):
                    selection = f"{selection} ML"

            return Pick(
                raw_text=text,
                league=league.upper(),
                date=date,
                bet_type=BetType.MONEYLINE,
                selection=selection,
                odds=odds,
            )
        else:
            # Spread: strip the spread value from the selection to get just the team name
            final_selection = text_clean
            if spread_match:
                final_selection = text_clean[:spread_match.start()] + text_clean[spread_match.end():]
                final_selection = re.sub(r'\s+', ' ', final_selection).strip()

            return Pick(
                raw_text=text,
                league=league.upper(),
                date=date,
                bet_type=BetType.SPREAD,
                selection=final_selection,
                line=found_spread_line,
                odds=odds,
            )
