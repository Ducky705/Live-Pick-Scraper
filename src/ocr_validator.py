"""
OCR Quality Validator
=====================
Determines if OCR output is "usable" (not garbage/cut-off text).

Key Checks:
1. Minimum viable length
2. Word/garbage ratio (real words vs random symbols)
3. Pick pattern presence (flexible regex for betting terms)
4. Line structure (betting slips have multiple lines)
5. No OCR artifacts (repeated chars, truncation markers)

Usage:
    from src.ocr_validator import is_usable_ocr, OCRQuality

    is_good, confidence, reasons = is_usable_ocr(text)
"""

import re
from dataclasses import dataclass
from enum import Enum


class OCRQuality(Enum):
    """OCR quality classification."""

    EXCELLENT = "excellent"  # High confidence, many pick patterns
    GOOD = "good"  # Usable, some pick patterns detected
    MARGINAL = "marginal"  # Might work, low confidence
    GARBAGE = "garbage"  # Unusable, needs vision AI


@dataclass
class OCRValidationResult:
    """Detailed OCR validation result."""

    is_usable: bool
    quality: OCRQuality
    confidence: float  # 0.0 - 1.0
    reasons: list[str]
    pick_patterns_found: int
    garbage_patterns_found: int
    word_quality_ratio: float
    team_names_found: int = 0


# --- PICK PATTERN DETECTION ---
# These patterns indicate betting-related content (flexible matching)

PICK_PATTERNS = [
    # Spreads and lines
    r"[+-]\d+\.?\d*",  # +3.5, -7, +150, -110
    r"[+-]\s*\d+\.?\d*",  # + 3.5, - 7 (with space)
    # Totals
    r"[oO](?:ver)?\s*\d+\.?\d*",  # over 220, Over 45.5, o220
    r"[uU](?:nder)?\s*\d+\.?\d*",  # under 45, Under 220.5, u45
    r"[oO]/[uU]\s*\d+",  # O/U 220
    # Moneyline
    r"\b[Mm][Ll]\b",  # ML, ml
    r"\bmoneyline\b",  # moneyline
    r"\bmoney\s*line\b",  # money line
    # Units and stakes
    r"\d+\.?\d*\s*[uU](?:nits?)?\b",  # 2u, 5 units, 1.5u
    r"\b[uU](?:nits?)?\s*\d+",  # u2, units 5
    # Periods
    r"\b1[Hh]\b|\b2[Hh]\b",  # 1H, 2H
    r"\b1st\s*[Hh](?:alf)?\b",  # 1st Half, 1st H
    r"\b2nd\s*[Hh](?:alf)?\b",  # 2nd Half
    r"\b[Qq][1-4]\b",  # Q1, Q2, Q3, Q4
    # Bet types
    r"\bparlay\b",
    r"\bteaser\b",
    r"\bspread\b",
    r"\bprop\b",
    r"\btotal\b",
    r"\bstraight\b",
    # Player props
    r"\bpts\b|\bpoints\b",
    r"\brebs?\b|\brebounds?\b",
    r"\basts?\b|\bassists?\b",
    r"\b3pm\b|\bthrees\b",
    r"\btds?\b|\btouchdowns?\b",
    r"\byards\b",
    r"\bstrikeouts?\b|\bk\'?s\b",
    # Team abbreviations (common 2-4 letter codes)
    r"\b[A-Z]{2,4}\b",  # LAL, NYG, PHI, etc.
    # Odds formats
    r"@\s*[+-]?\d+",  # @+150, @-110
    r"\(\s*[+-]?\d+\s*\)",  # (+150), (-110)
    # Win/Loss indicators
    r"\bwin\b|\bloss\b|\bpush\b|\bvoid\b",
    r"[✅❌⬜🟢🔴]",  # Emoji indicators
]

# --- GARBAGE PATTERN DETECTION ---
# These patterns indicate OCR failures

GARBAGE_PATTERNS = [
    r"(.)\1{5,}",  # Repeated chars: "aaaaaa", "======="
    r"[^a-zA-Z0-9\s\.\+\-\@\(\)]{6,}",  # Long chains of weird symbols
    r"^\s*$",  # Empty/whitespace only
    r"^.{0,8}$",  # Too short (< 8 chars)
    r"[\x00-\x1f]",  # Control characters
    r"[□■▪▫◊◦●○]",  # OCR artifact symbols
]

# --- COMMON ENGLISH WORDS ---
# Used to check if text contains real words vs gibberish

COMMON_WORDS = {
    # Betting terms
    "over",
    "under",
    "spread",
    "total",
    "parlay",
    "teaser",
    "moneyline",
    "pick",
    "play",
    "bet",
    "wager",
    "lock",
    "fade",
    "lean",
    "sharp",
    "units",
    "odds",
    "line",
    "risk",
    "payout",
    "return",
    "stake",
    "win",
    "loss",
    "push",
    "void",
    "pending",
    "graded",
    "settled",
    # Sports terms
    "game",
    "match",
    "team",
    "player",
    "score",
    "points",
    "assists",
    "rebounds",
    "touchdowns",
    "yards",
    "goals",
    "runs",
    "hits",
    "quarter",
    "half",
    "period",
    "inning",
    "set",
    "round",
    # Time terms
    "today",
    "tonight",
    "tomorrow",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "pm",
    "am",
    "est",
    "pst",
    # Common words
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "have",
    "are",
    "was",
    "will",
    "can",
    "all",
    "but",
    "not",
    "you",
    "your",
    "our",
    # Sports/Team names (partial)
    "lakers",
    "celtics",
    "warriors",
    "bulls",
    "heat",
    "nets",
    "knicks",
    "chiefs",
    "eagles",
    "cowboys",
    "patriots",
    "bills",
    "raiders",
    "yankees",
    "dodgers",
    "astros",
    "braves",
    "mets",
    "cubs",
}


def count_pick_patterns(text: str) -> int:
    """Count how many pick-related patterns are found in text."""
    if not text:
        return 0

    count = 0
    text_lower = text.lower()

    for pattern in PICK_PATTERNS:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        except re.error:
            continue

    return count


def count_garbage_patterns(text: str) -> int:
    """Count how many garbage patterns are found in text."""
    if not text:
        return 0

    count = 0
    for pattern in GARBAGE_PATTERNS:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        except re.error:
            continue

    return count


def calculate_word_quality_ratio(text: str) -> float:
    """
    Calculate what percentage of words are recognizable English/betting terms.
    Returns 0.0 - 1.0
    """
    if not text:
        return 0.0

    # Extract words (letters only, 2+ chars)
    words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())

    if not words:
        return 0.0

    # Count recognized words
    recognized = sum(1 for w in words if w in COMMON_WORDS)

    # Also count words that look like team abbreviations or names
    # (Capitalized, 3-15 chars)
    name_pattern = re.compile(r"^[A-Z][a-z]{2,14}$")
    for word in re.findall(r"\b[A-Z][a-z]{2,14}\b", text):
        recognized += 0.5  # Partial credit for proper nouns

    return min(1.0, recognized / len(words))


def check_line_structure(text: str) -> tuple[bool, int]:
    """
    Check if text has proper line structure (multiple lines).
    Betting slips typically have 3+ lines.
    Returns (has_structure, line_count)
    """
    if not text:
        return False, 0

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Filter out very short lines (likely noise)
    meaningful_lines = [l for l in lines if len(l) > 5]

    return len(meaningful_lines) >= 2, len(meaningful_lines)


def is_usable_ocr(text: str) -> tuple[bool, float, list[str]]:
    """
    Main validation function.

    Returns:
        Tuple of (is_usable: bool, confidence: 0.0-1.0, reasons: List[str])
    """
    result = validate_ocr_detailed(text)
    return result.is_usable, result.confidence, result.reasons


def validate_ocr_detailed(text: str) -> OCRValidationResult:
    """
    Detailed OCR validation with full diagnostics.

    Scoring Logic:
    - Start at 0.5 (neutral)
    - Add/subtract based on indicators
    - Threshold for "usable" is 0.5
    """
    if not text or not text.strip():
        return OCRValidationResult(
            is_usable=False,
            quality=OCRQuality.GARBAGE,
            confidence=0.0,
            reasons=["Empty or whitespace-only text"],
            pick_patterns_found=0,
            garbage_patterns_found=0,
            word_quality_ratio=0.0,
        )

    text = text.strip()
    reasons = []
    score = 0.5  # Start neutral

    # 1. Length check
    length = len(text)
    if length < 10:
        score -= 0.3
        reasons.append(f"Too short ({length} chars)")
    elif length < 30:
        score -= 0.1
        reasons.append(f"Short text ({length} chars)")
    elif length > 100:
        score += 0.1
        reasons.append(f"Good length ({length} chars)")

    # 2. Pick patterns
    pick_count = count_pick_patterns(text)
    if pick_count >= 5:
        score += 0.3
        reasons.append(f"Many pick patterns ({pick_count})")
    elif pick_count >= 2:
        score += 0.2
        reasons.append(f"Some pick patterns ({pick_count})")
    elif pick_count >= 1:
        score += 0.1
        reasons.append(f"Few pick patterns ({pick_count})")
    else:
        score -= 0.1
        reasons.append("No pick patterns detected")

    # 3. Garbage patterns
    garbage_count = count_garbage_patterns(text)
    if garbage_count >= 3:
        score -= 0.3
        reasons.append(f"Many garbage patterns ({garbage_count})")
    elif garbage_count >= 1:
        score -= 0.1
        reasons.append(f"Some garbage patterns ({garbage_count})")

    # 4. Word quality
    word_ratio = calculate_word_quality_ratio(text)
    if word_ratio >= 0.4:
        score += 0.15
        reasons.append(f"Good word quality ({word_ratio:.0%})")
    elif word_ratio >= 0.2:
        score += 0.05
    elif word_ratio < 0.1:
        score -= 0.15
        reasons.append(f"Low word quality ({word_ratio:.0%})")

    # 5. Line structure
    has_structure, line_count = check_line_structure(text)
    if has_structure:
        score += 0.1
        reasons.append(f"Good structure ({line_count} lines)")

    # 6. Team Name Verification (Sanity Check)
    team_count = check_team_overlap(text)
    if team_count >= 2:
        score += 0.25 # Huge boost for finding real teams
        reasons.append(f"Teams found: {team_count}")
        # If we have teams, we are almost certainly looking at a bet
    elif team_count == 1:
        score += 0.1
        reasons.append(f"Team found: {team_count}")

    # Clamp score
    score = max(0.0, min(1.0, score))

    # Determine quality level
    if score >= 0.75:
        quality = OCRQuality.EXCELLENT
    elif score >= 0.55:
        quality = OCRQuality.GOOD
    elif score >= 0.4:
        quality = OCRQuality.MARGINAL
    else:
        quality = OCRQuality.GARBAGE

    # Usable if score >= 0.5 (or has at least 2 pick patterns)
    is_usable = score >= 0.5 or pick_count >= 2

    return OCRValidationResult(
        is_usable=is_usable,
        quality=quality,
        confidence=score,
        reasons=reasons,
        pick_patterns_found=pick_count,
        garbage_patterns_found=garbage_count,
        word_quality_ratio=word_ratio,
        team_names_found=team_count,
    )


def quick_validate(text: str) -> bool:
    """
    Fast validation for hot path.
    Returns True if OCR is likely usable.
    """
    if not text or len(text) < 10:
        return False

    # Quick pick pattern check (just a few key ones)
    quick_patterns = [
        r"[+-]\d+\.?\d*",  # Spreads
        r"[oOuU]\s*\d+",  # Totals
        r"\b[Mm][Ll]\b",  # Moneyline
        r"\d+\s*[uU]",  # Units
    ]

    for pattern in quick_patterns:
        if re.search(pattern, text):
            return True

    # Fallback: check word count
    words = text.split()
    return len(words) >= 5




def check_team_overlap(text: str) -> int:
    """
    Check if text contains known team names/aliases.
    Returns count of unique teams found.
    """
    from src.team_aliases import TEAM_ALIASES
    
    if not text:
        return 0
        
    text_lower = text.lower()
    found_teams = set()
    
    # We flatten the aliases for efficient searching? 
    # Or just iterate. The alias list is ~200 items, not too bad.
    # To be safer/faster, we could pre-compile this, but lazy import is fine for now.
    
    for team_key, aliases in TEAM_ALIASES.items():
        for alias in aliases:
            # simple substring check, or regex for word boundary?
            # word boundary is safer: \bknicks\b
            # But some aliases might be multi-word: "new york knicks"
            if alias in text_lower:
                 found_teams.add(team_key)
                 break # Found this team, move to next string
                 
    return len(found_teams)

