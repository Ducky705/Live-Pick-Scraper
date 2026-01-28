# src/utils.py
"""
Utility functions for the TelegramScraper.

This module provides shared helpers for:
- Text normalization and cleaning
- File operations
- Content detection
"""

from collections import Counter
import re
import os
import glob
import unicodedata
from typing import Optional


def normalize_string(text: Optional[str], remove_spaces: bool = False) -> str:
    """
    Normalize a string for comparison purposes.

    This is the canonical normalization function - use this instead of
    creating new normalize_name/normalize_text functions elsewhere.

    Args:
        text: Input string to normalize
        remove_spaces: If True, removes all spaces (useful for name matching)

    Returns:
        Normalized lowercase string with special chars removed

    Examples:
        >>> normalize_string("Los Angeles Lakers")
        'los angeles lakers'
        >>> normalize_string("Los Angeles Lakers", remove_spaces=True)
        'losangeleslakers'
        >>> normalize_string("Café André")
        'cafe andre'
    """
    if not text:
        return ""

    # Normalize unicode (NFKC handles accents, ligatures, etc.)
    text = unicodedata.normalize("NFKC", str(text))

    # Replace special whitespace with regular space
    text = text.replace("\u00a0", " ").replace("\u202f", " ")

    # Lowercase
    text = text.lower()

    # Remove special characters but keep alphanumeric and spaces
    text = re.sub(r"[^a-z0-9\s]", "", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    if remove_spaces:
        text = text.replace(" ", "")

    return text


def cleanup_temp_images(directory):
    """Deletes only .jpg files in the specified directory to save space."""
    if not os.path.exists(directory):
        return

    files = glob.glob(os.path.join(directory, "*.jpg"))
    if files:
        print(f"[System] Cleaning up {len(files)} old temporary images...")
        for f in files:
            try:
                os.remove(f)
            except Exception as e:
                print(f"Error deleting {f}: {e}")


def detect_common_watermark(messages_ocr_text):
    if not messages_ocr_text:
        return ""
    all_lines = []
    for text in messages_ocr_text:
        lines = [l.strip().lower() for l in text.split("\n") if len(l.strip()) > 3]
        all_lines.extend(lines)
    if not all_lines:
        return ""
    counts = Counter(all_lines)
    detected = []
    for line, count in counts.most_common(10):
        if count > 1 and ("@" in line or "dm" in line or "join" in line):
            detected.append(line)
    return ", ".join(detected[:3])


def filter_text(original_text, watermark_input):
    if not original_text:
        return ""

    terms = [t.strip() for t in watermark_input.split(",") if t.strip()]
    cleaned = original_text
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        cleaned = pattern.sub("", cleaned)

    noise_patterns = [
        r"DM\**\W+\**@cappersfree.*",
        r"@cappers(free|tree).*",
        r"➖➖+",
        r"✅",
        r"Join The BEST Team.*",
        r"Let\'s crush it.*",
        r"EXCLUSIVE PACKAGE.*",
    ]

    for pattern in noise_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    return "\n".join(lines)


def is_ad_content(text):
    if not text:
        return False
    text_upper = text.upper()
    ad_triggers = [
        "HUGE PROMO ALLERT",
        "DAYS FOR THE PRICE OF",
        "EXCLUSIVE PACKAGE",
        "CHEAPEST PRICES",
    ]
    if any(trigger in text_upper for trigger in ad_triggers):
        if not re.search(r"\d", text):
            return True
    return False


def backfill_odds(picks):
    """
    1. Identifies duplicates by pick text.
    2. Finds if any copy of that pick has valid odds.
    3. Fills missing odds from the valid ones.
    4. Does NOT default to -110 if nothing found.
    """
    odds_map = {}

    def normalize(s):
        return str(s).lower().replace(" ", "").strip()

    # Pass 1: Harvest known odds
    for p in picks:
        p_text = normalize(p.get("pick", ""))
        p_odds = p.get("odds")

        # Validate that odds is actually a number/string worth saving
        isValidOdds = (
            p_odds is not None
            and str(p_odds).strip() != ""
            and str(p_odds).lower() != "none"
        )

        if isValidOdds and p_text:
            if p_text not in odds_map:
                odds_map[p_text] = p_odds

    # Pass 2: Backfill or Leave Blank
    for p in picks:
        # Clean Capper Name
        if p.get("capper_name"):
            name = str(p["capper_name"]).strip()
            if len(name) > 3 and name.isupper():
                p["capper_name"] = name.title()
            elif name.lower() == "n/a":
                p["capper_name"] = "Unknown"
        else:
            p["capper_name"] = "Unknown"

        if not p.get("league"):
            p["league"] = "Other"

        # Handle Odds
        current_odds = p.get("odds")
        is_missing = (
            current_odds is None
            or str(current_odds).strip() == ""
            or str(current_odds).lower() == "none"
        )

        if is_missing:
            p_text = normalize(p.get("pick", ""))
            if p_text in odds_map:
                p["odds"] = odds_map[p_text]  # Crowdsourced match
            else:
                # Do NOT default to -110 unless we are absolutely sure.
                # Previously: p['odds'] = None
                # BUT: For Spread and Total, if odds are missing, -110 is the industry standard implication.
                # For Moneyline, missing odds usually means "I don't know", so leave as None.
                p_type = str(p.get("type")).lower()
                if p_type in ["spread", "total", "over", "under"]:
                    # Only default to -110 if it's a standard line bet
                    # But wait, "Oilers -175" parsed as Moneyline with missing odds...
                    # If we force -110 here, we break Moneyline logic.
                    # So, keep None. The pipeline handles this later if needed.
                    p["odds"] = None
                else:
                    p["odds"] = None

        # Unit Cap Logic
        raw_unit = p.get("units")
        if raw_unit is None or str(raw_unit).strip() in ["", "null", "None"]:
            p["units"] = 1.0
        else:
            try:
                clean_str = (
                    str(raw_unit)
                    .lower()
                    .replace("units", "")
                    .replace("unit", "")
                    .replace("u", "")
                    .strip()
                )
                val = float(clean_str)
                p["units"] = 1.0 if val > 25 else val
            except ValueError:
                p["units"] = 1.0

    return picks


def smart_backfill_odds(picks, target_date):
    """
    Smart odds backfilling that fetches from ESPN only for picks still missing odds.

    Strategy:
    1. First pass: Cross-reference within batch (existing backfill_odds logic)
    2. Identify picks still missing odds and their leagues
    3. Fetch ESPN odds only for needed leagues (parallel, cached)
    4. Match fetched odds to picks

    Args:
        picks: List of pick dictionaries
        target_date: Date string (YYYY-MM-DD or MM/DD/YYYY)

    Returns:
        Updated picks list with odds backfilled where possible
    """
    import concurrent.futures
    import logging

    logger = logging.getLogger(__name__)

    # Pass 1: Cross-reference within batch
    picks = backfill_odds(picks)

    # Identify picks still missing odds
    missing_odds_picks = []
    leagues_needed = set()

    for p in picks:
        current_odds = p.get("odds")
        is_missing = (
            current_odds is None
            or str(current_odds).strip() == ""
            or str(current_odds).lower() == "none"
        )

        if is_missing:
            league = (p.get("league") or p.get("lg") or "").lower()
            if league and league != "other":
                missing_odds_picks.append(p)
                leagues_needed.add(league)

    if not missing_odds_picks:
        logger.debug("All picks have odds, no ESPN fetch needed")
        return picks

    logger.info(
        f"Fetching ESPN odds for {len(leagues_needed)} leagues: {', '.join(sorted(leagues_needed))}"
    )

    try:
        from src.score_fetcher import fetch_odds_for_leagues
        from src.score_cache import get_cache

        cache = get_cache()

        # Normalize date
        import datetime

        if "-" in target_date:
            d = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        else:
            d = datetime.datetime.strptime(target_date, "%m/%d/%Y")
        api_date = d.strftime("%Y%m%d")

        # Check cache first, then fetch missing
        all_odds = {}
        leagues_to_fetch = []

        for league in leagues_needed:
            cached_odds = cache.get_odds(api_date, league)
            if cached_odds:
                all_odds.update(cached_odds)
            else:
                leagues_to_fetch.append(league)

        # Fetch missing leagues in parallel
        if leagues_to_fetch:
            fetched_odds = fetch_odds_for_leagues(target_date, leagues_to_fetch)
            all_odds.update(fetched_odds)

            # Cache the fetched odds by league
            for league in leagues_to_fetch:
                league_odds = {
                    k: v for k, v in fetched_odds.items() if k.startswith(f"{league}:")
                }
                if league_odds:
                    cache.set_odds(api_date, league, league_odds)

        # Pass 2: Match fetched odds to picks
        matched_count = 0
        for p in missing_odds_picks:
            pick_text = (p.get("pick") or "").lower()
            league = (p.get("league") or p.get("lg") or "").lower()

            for game_key, odds_data in all_odds.items():
                if not game_key.startswith(f"{league}:"):
                    continue

                home = (odds_data.get("home_team") or "").lower()
                away = (odds_data.get("away_team") or "").lower()

                # Check if pick mentions either team
                if _pick_mentions_team(pick_text, home) or _pick_mentions_team(
                    pick_text, away
                ):
                    # Determine which odds to use based on pick type
                    p["odds"] = _extract_appropriate_odds(p, odds_data)
                    if p["odds"]:
                        matched_count += 1
                    break

        logger.info(
            f"Backfilled odds for {matched_count}/{len(missing_odds_picks)} picks from ESPN"
        )

    except Exception as e:
        logger.warning(f"Smart odds backfill failed: {e}")

    return picks


def _pick_mentions_team(pick_text, team_name):
    """Check if a pick text mentions a team name."""
    if not team_name or not pick_text:
        return False

    # Direct match
    if team_name in pick_text:
        return True

    # Last word match (e.g., "lakers" from "los angeles lakers")
    words = team_name.split()
    if len(words) > 1:
        last_word = words[-1]
        if len(last_word) > 2 and last_word in pick_text:
            return True

    return False


def _extract_appropriate_odds(pick, odds_data):
    """Extract the appropriate odds based on pick type."""
    pick_text = (pick.get("pick") or "").lower()
    pick_type = (pick.get("type") or "").lower()

    # Spread
    if pick_type == "spread" or re.search(r"[+-]\d+\.?\d*", pick_text):
        # Try to determine home/away
        home = (odds_data.get("home_team") or "").lower()
        if _pick_mentions_team(pick_text, home):
            return odds_data.get("spread_home_odds")
        return odds_data.get("spread_away_odds")

    # Moneyline
    if pick_type == "moneyline" or "ml" in pick_text:
        home = (odds_data.get("home_team") or "").lower()
        if _pick_mentions_team(pick_text, home):
            return odds_data.get("moneyline_home")
        return odds_data.get("moneyline_away")

    # Total
    if pick_type == "total" or "over" in pick_text or "under" in pick_text:
        if "over" in pick_text:
            return odds_data.get("over_odds")
        return odds_data.get("under_odds")

    # Default: try moneyline
    return odds_data.get("moneyline_home") or odds_data.get("moneyline_away")


def clean_text_for_ai(text):
    """
    Retrieval-Augmented compression: Removes high-entropy noise to save tokens.
    """
    if not text:
        return ""

    # 1. Remove URLs
    text = re.sub(r"http\S+|www\.\S+", "", text)

    # 2. Remove standard legal disclaimers
    text = re.sub(r"(?i)(gambling\sproblem|1-800-\d{3}-\d{4}|call\s*1-800).*", "", text)

    # 3. Remove excess punctuation/separators
    text = re.sub(r"[-=_]{3,}", " ", text)

    # 4. Remove generic Telegram noise
    text = re.sub(
        r"(?i)(join\s*us|subscribe|link\s*in\s*bio|click\s*here|t\.me\/).*", "", text
    )

    # 5. CRITICAL: Remove known channel watermarks that get misidentified as cappers
    # These are channel branding, NOT capper names
    watermarks = [
        r"@?cappersfree",
        r"@?capperstree",
        r"@?cappers_free",
        r"@?freecappers",
        r"@?vippicks",
        r"@?freepicks",
        r"@?sportsbetting",
        r"DM\s*@\w+",  # "DM @username" patterns
        r"\bDK\b(?![a-z])",  # "DK" (DraftKings) standalone at start/end of words
        r"\bFD\b(?![a-z])",  # "FD" (FanDuel)
        r"\bMGM\b",  # "MGM"
    ]
    for wm in watermarks:
        text = re.sub(wm, " ", text, flags=re.IGNORECASE)  # Replace with space

    # 6. Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # 7. Normalize fractions (½ -> .5)
    # This prevents precision loss where ½ becomes .0 or is dropped
    text = text.replace("½", ".5")
    text = text.replace("1/2", ".5")  # Simple fraction replacement

    # 8. Normalize Double Chance / OR separators
    text = text.replace("||", " / ")

    return text[:2500]  # Safe clamp


def auto_group_parlays(picks, message_context):
    """
    Groups individual picks into a Parlay if the message context strongly implies a parlay.

    Args:
        picks: List of pick dictionaries
        message_context: Dict mapping message_id (int) -> full text context

    Returns:
        Updated list of picks with parlays grouped
    """
    if not picks or not message_context:
        return picks

    # Group by message_id
    picks_by_id = {}
    other_picks = []

    for p in picks:
        mid = p.get("message_id")
        if mid:
            try:
                mid_int = int(mid)
                if mid_int not in picks_by_id:
                    picks_by_id[mid_int] = []
                picks_by_id[mid_int].append(p)
            except (ValueError, TypeError):
                other_picks.append(p)
        else:
            other_picks.append(p)

    final_picks = []
    final_picks.extend(other_picks)

    for mid, msg_picks in picks_by_id.items():
        context = message_context.get(mid, "").upper()

        # Check for explicit Parlay indicators
        is_parlay_text = "PARLAY" in context or "BUILDER" in context

        # Filter for straight bets that might need grouping
        # We group anything that ISN'T already a MULTI-LEG Parlay.
        # Single-leg "Parlay" items (AI artifacts) should be treated as candidates for grouping.
        candidates = []
        for p in msg_picks:
            p_type = str(p.get("type")).lower()
            p_pick = str(p.get("pick", ""))

            # If it's already a multi-leg parlay (contains / or +), keep it separate
            if p_type == "parlay" and ("/" in p_pick or " + " in p_pick):
                continue

            # If it's explicitly "Unknown" type, keep it separate (usually noise)
            if p_type == "unknown":
                continue

            # Otherwise, it's a candidate (Spread, Moneyline, Total, or Single-Leg Parlay)
            candidates.append(p)

        # Existing explicit multi-leg parlays should be kept as is
        existing_parlays = [
            p
            for p in msg_picks
            if str(p.get("type")).lower() == "parlay"
            and ("/" in p.get("pick", "") or " + " in p.get("pick", ""))
        ]

        # Unknowns kept as is
        unknowns = [p for p in msg_picks if str(p.get("type")).lower() in ["unknown"]]

        # Rule: If text says Parlay, and we have > 1 candidate, group them.
        if is_parlay_text and len(candidates) > 1:
            # Construct merged pick
            merged_pick_text = " / ".join([str(p.get("pick", "")) for p in candidates])

            # Use the first leg's metadata
            base = candidates[0]

            new_pick = {
                "message_id": mid,
                "pick": merged_pick_text,
                "type": "Parlay",
                "odds": None,  # Reset odds for calculated parlay
                "units": base.get("units", 1.0),
                "league": base.get("league", "Other"),
                "capper_name": base.get("capper_name", "Unknown"),
                "confidence": 0.9,
                "reasoning": "Auto-grouped based on Parlay keyword in text.",
                "_source_text": base.get("_source_text", ""),
            }

            # Add the new grouped parlay + existing parlays + unknowns
            final_picks.append(new_pick)
            final_picks.extend(existing_parlays)
            final_picks.extend(unknowns)
        else:
            final_picks.extend(msg_picks)

    return final_picks
