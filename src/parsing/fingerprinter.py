import re


class Fingerprinter:
    """
    Converts raw pick text into a structural fingerprint.
    Used to lookup Regex templates.
    """

    @staticmethod
    def fingerprint(text: str) -> str:
        """
        Normalize text to a structural key.
        
        Example:
        - "Lakers -5 (2u)" -> "<TEXT> <LINE> (<UNITS>)"
        """
        # 1. Basic Cleanup
        # Convert to lowercase
        normalized = text.lower()

        # Remove Emojis and non-ascii noise (keep basic punctuation)
        # Keep: a-z, 0-9, ., -, +, (, ), :, %, /, space
        normalized = re.sub(r"[^a-z0-9\.\-\+\(\):\%\/\s]", "", normalized)

        # 2. Tokenize Entities (Order matters!)

        # ODDS: (-110, +200) -> <ODDS>
        # Pattern: ( +/- digit ) or +/- digit (if > 100)
        # Parenthesized odds
        normalized = re.sub(r"\(\s*[\+\-]?\s*\d{3,}\s*\)", " <ODDS> ", normalized)
        # Standalone odds (must be >= 100 or <= -100)
        # Heuristic: look for 3 digits
        normalized = re.sub(r"(?<!\d)[\+\-]\d{3,}(?!\d)", " <ODDS> ", normalized)

        # LINES / SPREADS: (-5.5, +3, -10) -> <LINE>
        # Look for numbers with optional sign and optional decimal
        # Ideally, we distinguish line from units. Units usually have 'u'.

        # UNITS: (2u, 5U, 1.5 units) -> <UNITS>
        normalized = re.sub(r"\d+(\.\d+)?\s*u(nits)?", " <UNITS> ", normalized)
        normalized = re.sub(r"\d+(\.\d+)?\s*\*", " <UNITS> ", normalized) # 5* play
        normalized = re.sub(r"\d+(\.\d+)?\s*%", " <UNITS> ", normalized) # 5% play

        # LINES (Remaining numbers)
        # Catch signed numbers (+5, -4.5)
        normalized = re.sub(r"[\+\-]\d+(\.\d+)?", " <LINE> ", normalized)
        # Catch just numbers if they look like totals? (over 220)
        # This is tricky without context. Let's map ALL remaining numbers to <NUM>
        normalized = re.sub(r"\d+(\.\d+)?", " <NUM> ", normalized)

        # DATES / TIMES (7:00 pm) -> <TIME>
        # (Should be done before numbers ideally, but simple for now)

        # TEXT BLOCKS
        # Map remaining words to <TEXT>
        normalized = re.sub(r"[a-z]+", "<TEXT>", normalized)

        # 3. Collapse
        # <TEXT> <TEXT> -> <TEXT>
        normalized = re.sub(r"(<TEXT>\s*)+", "<TEXT> ", normalized)

        # Clean whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized
