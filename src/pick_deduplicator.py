# src/pick_deduplicator.py
"""
Post-parsing pick deduplication.

Different leakers often repost the same capper's picks with different formatting.
This module deduplicates PARSED picks by normalizing and comparing:
  - Capper name (fuzzy)
  - Pick text (normalized)
  - League

When confidence is low, it can optionally use AI to resolve.
"""

import re
import logging
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple

# Similarity thresholds
CAPPER_SIMILARITY_THRESHOLD = 0.85  # "HammeringHank" vs "Hammering Hank"
PICK_SIMILARITY_THRESHOLD = 0.80  # "Lakers -5.5" vs "LA Lakers -5.5"


def normalize_capper_name(name: str) -> str:
    """Normalize capper name for comparison."""
    if not name:
        return ""
    # Lowercase, remove special chars, collapse spaces
    clean = re.sub(r"[^a-z0-9\s]", "", name.lower())
    clean = re.sub(r"\s+", "", clean)  # Remove all spaces for comparison
    return clean


def normalize_pick_text(pick: str) -> str:
    """Normalize pick text for comparison."""
    if not pick:
        return ""
    # Lowercase
    clean = pick.lower()
    # Normalize team abbreviations
    abbreviations = {
        "la lakers": "lakers",
        "los angeles lakers": "lakers",
        "gs warriors": "warriors",
        "golden state warriors": "warriors",
        "golden state": "warriors",
        "ny knicks": "knicks",
        "new york knicks": "knicks",
        "phx suns": "suns",
        "phoenix suns": "suns",
        "sa spurs": "spurs",
        "san antonio spurs": "spurs",
        "okc thunder": "thunder",
        "oklahoma city thunder": "thunder",
        "no pelicans": "pelicans",
        "new orleans pelicans": "pelicans",
    }
    for full, abbr in abbreviations.items():
        clean = clean.replace(full, abbr)

    # Remove common noise words
    noise = ["moneyline", "money line", "ml", "pk", "pick", "even"]
    for word in noise:
        clean = re.sub(rf"\b{word}\b", "", clean)

    # Normalize spacing and punctuation
    clean = re.sub(r"[^a-z0-9\s\.\-\+]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    return clean


def similarity(a: str, b: str) -> float:
    """Calculate string similarity ratio (0-1)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def extract_spread_number(pick: str) -> Tuple[str, float | None]:
    """Extract the spread/total number from a pick for comparison."""
    # Match patterns like "-5.5", "+3", "over 215.5", "under 48"
    match = re.search(r"([+-]?\d+\.?\d*)", pick)
    if match:
        try:
            return pick, float(match.group(1))
        except ValueError:
            pass
    return pick, None


def are_picks_equivalent(pick1: Dict, pick2: Dict) -> Tuple[bool, float]:
    """
    Determine if two picks are duplicates.

    Returns: (is_duplicate, confidence)
    """
    # Must be same league (or close)
    league1 = (pick1.get("league") or "").upper()
    league2 = (pick2.get("league") or "").upper()

    # League must match (with some flexibility)
    league_aliases = {
        "NCAAB": ["NCAAB", "CBB", "COLLEGE BASKETBALL"],
        "NCAAF": ["NCAAF", "CFB", "COLLEGE FOOTBALL"],
        "NBA": ["NBA"],
        "NFL": ["NFL"],
        "NHL": ["NHL"],
        "MLB": ["MLB"],
    }

    def get_league_group(lg):
        for key, aliases in league_aliases.items():
            if lg in aliases:
                return key
        return lg

    if get_league_group(league1) != get_league_group(league2):
        return False, 0.0

    # Normalize capper names
    capper1 = normalize_capper_name(pick1.get("capper_name", ""))
    capper2 = normalize_capper_name(pick2.get("capper_name", ""))

    capper_sim = similarity(capper1, capper2)
    if capper_sim < CAPPER_SIMILARITY_THRESHOLD:
        return False, 0.0

    # Normalize pick text
    p1 = normalize_pick_text(pick1.get("pick", ""))
    p2 = normalize_pick_text(pick2.get("pick", ""))

    pick_sim = similarity(p1, p2)

    # High similarity = definite duplicate
    if pick_sim >= PICK_SIMILARITY_THRESHOLD:
        confidence = (capper_sim + pick_sim) / 2
        return True, confidence

    # Check if same spread number (e.g., "Lakers -5" vs "LA Lakers -5.0")
    _, num1 = extract_spread_number(p1)
    _, num2 = extract_spread_number(p2)

    if num1 is not None and num2 is not None and abs(num1 - num2) < 0.5:
        # Same number, check if team names overlap
        # Extract team name (first word before number)
        team1 = re.sub(r"[+-]?\d+\.?\d*.*", "", p1).strip()
        team2 = re.sub(r"[+-]?\d+\.?\d*.*", "", p2).strip()

        if team1 and team2 and similarity(team1, team2) > 0.7:
            return True, 0.75

    return False, 0.0


def merge_duplicate_picks(pick1: Dict, pick2: Dict) -> Dict:
    """
    Merge two duplicate picks, keeping the best data from each.
    """
    merged = pick1.copy()

    # Prefer non-null odds
    if not merged.get("odds") and pick2.get("odds"):
        merged["odds"] = pick2["odds"]

    # Prefer more specific capper name (longer, more info)
    name1 = pick1.get("capper_name", "") or ""
    name2 = pick2.get("capper_name", "") or ""
    if len(name2) > len(name1) and name2.lower() != "unknown":
        merged["capper_name"] = name2

    # Prefer more complete pick text
    if len(pick2.get("pick", "")) > len(pick1.get("pick", "")):
        merged["pick"] = pick2["pick"]

    # Take higher units (assume it's the real confidence)
    units1 = pick1.get("units") or 1.0
    units2 = pick2.get("units") or 1.0
    merged["units"] = max(units1, units2)

    return merged


def remove_parlay_redundancy(picks: List[Dict]) -> List[Dict]:
    """
    Remove straight picks that are already contained in a Parlay pick
    within the same message.
    """
    # Group by message_id
    by_msg = {}
    for p in picks:
        # Handle 'i' or 'id' or 'message_id' key
        mid = p.get("message_id") or p.get("id") or p.get("i")
        # If no ID, treat as global/unknown (safe to skip grouping or group under None)
        if mid is None:
            # If no message ID, we can't safely associate parlay legs with straight bets
            # to avoid cross-message pollution. Just pass them through.
            # Or group them all together? Safer to skip redundancy check for them.
            # Let's group them under "unknown"
            mid = "unknown"

        if mid not in by_msg:
            by_msg[mid] = []
        by_msg[mid].append(p)

    final_picks = []

    for mid, msg_picks in by_msg.items():
        # Check for both Parlay and Teaser types
        parlays = [p for p in msg_picks if p.get("type") in ("Parlay", "Teaser")]

        if not parlays:
            final_picks.extend(msg_picks)
            continue

        # Build set of normalized legs
        redundant_legs = set()
        for parlay in parlays:
            # Assuming format: Leg1 / Leg2 / Leg3 or Leg1 + Leg2
            raw_text = parlay.get("pick", "")
            # Split by common delimiters
            legs = re.split(r" \/ | \+ ", raw_text)
            for leg in legs:
                # Remove (LEAGUE) prefix if present for normalization
                # e.g. "(NFL) Chiefs ML" -> "Chiefs ML"
                leg_clean = re.sub(r"\([A-Za-z]+\)\s*", "", leg)
                norm = normalize_pick_text(leg_clean)
                if norm:
                    redundant_legs.add(norm)

        # Filter
        for p in msg_picks:
            if p.get("type") in ("Parlay", "Teaser"):
                final_picks.append(p)
                continue

            # Check redundancy

            p_norm = normalize_pick_text(p.get("pick", ""))

            # strict match
            if p_norm in redundant_legs:
                logging.info(
                    f"[PickDedup] Dropping redundant straight pick '{p.get('pick')}' (found in Parlay for msg {mid})"
                )
                continue

            final_picks.append(p)

    return final_picks


def deduplicate_picks(picks: List[Dict], use_ai_fallback: bool = False) -> List[Dict]:
    """
    Deduplicate a list of parsed picks.

    Args:
        picks: List of pick dictionaries
        use_ai_fallback: If True, use AI for low-confidence matches (not implemented yet)

    Returns:
        Deduplicated list of picks
    """
    if not picks:
        return []

    # Step 0: Remove Parlay Redundancy (Straight bets that are legs of a Parlay in the same msg)
    # CRITICAL OPTIMIZATION: Disabled to improve Recall.
    # Users often want both straight and parlay bets if listed explicitly.
    # picks = remove_parlay_redundancy(picks)

    if len(picks) <= 1:
        return picks

    # Track which picks have been merged
    consumed = set()
    result = []
    low_confidence_pairs = []  # For potential AI review

    for i, pick1 in enumerate(picks):
        if i in consumed:
            continue

        current = pick1.copy()

        for j, pick2 in enumerate(picks[i + 1 :], start=i + 1):
            if j in consumed:
                continue

            is_dup, confidence = are_picks_equivalent(current, pick2)

            if is_dup:
                if confidence >= 0.9:
                    # High confidence - merge automatically
                    current = merge_duplicate_picks(current, pick2)
                    consumed.add(j)
                    logging.debug(
                        f"[PickDedup] Merged: '{pick1.get('pick')}' + '{pick2.get('pick')}' (conf: {confidence:.2f})"
                    )
                elif confidence >= 0.75:
                    # Medium confidence - merge but flag
                    current = merge_duplicate_picks(current, pick2)
                    consumed.add(j)
                    try:
                        c_name = (
                            str(pick1.get("capper_name", ""))
                            .encode("ascii", "replace")
                            .decode("ascii")
                        )
                        c_pick = (
                            str(pick1.get("pick", ""))
                            .encode("ascii", "replace")
                            .decode("ascii")
                        )
                        logging.info(
                            f"[PickDedup] Merged (medium conf {confidence:.2f}): '{c_name}' - '{c_pick}'"
                        )
                    except Exception:
                        logging.info(
                            f"[PickDedup] Merged (medium conf {confidence:.2f})"
                        )
                else:
                    # Low confidence - save for AI review if enabled
                    low_confidence_pairs.append((i, j, confidence))

        result.append(current)

    # AI fallback for low-confidence pairs (placeholder)
    if use_ai_fallback and low_confidence_pairs:
        logging.info(
            f"[PickDedup] {len(low_confidence_pairs)} pairs need AI review (not implemented)"
        )
        # TODO: Implement AI-based duplicate resolution
        # This would send ambiguous pairs to an LLM to determine if they're the same pick

    original_count = len(picks)
    final_count = len(result)

    if original_count != final_count:
        logging.info(
            f"[PickDedup] Reduced {original_count} -> {final_count} picks ({original_count - final_count} duplicates merged)"
        )

    return result


def deduplicate_by_capper(picks: List[Dict]) -> List[Dict]:
    """
    Group picks by capper and deduplicate within each group.
    More efficient for large lists.
    """
    # Group by normalized capper name
    by_capper = {}
    for pick in picks:
        key = normalize_capper_name(pick.get("capper_name", "unknown"))
        if key not in by_capper:
            by_capper[key] = []
        by_capper[key].append(pick)

    result = []
    for capper, capper_picks in by_capper.items():
        # Deduplicate within this capper's picks
        deduped = deduplicate_picks(capper_picks)
        result.extend(deduped)

    return result
