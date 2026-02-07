import logging
from typing import Any

from src.grading.constants import LEAGUE_ALIASES_MAP
from src.score_fetcher import fetch_scores_for_date, fetch_odds_for_date, get_odds_for_pick
from src.utils import normalize_string

logger = logging.getLogger(__name__)


def enrich_picks(picks: list[dict[str, Any]], target_date: str) -> list[dict[str, Any]]:
    """
    Enrich picks with opponent and game_date by looking up games in ESPN.
    Also fetches and applies odds if they are missing.

    Args:
        picks: List of pick dictionaries
        target_date: Date string (YYYY-MM-DD)

    Returns:
        Updated list of picks with 'opponent', 'game_date', and 'odds' fields populated where found.
    """
    if not picks:
        return picks

    # 1. Identify relevant leagues
    relevant_leagues = set()
    picks_needing_odds = []
    
    for p in picks:
        lg = (p.get("league") or p.get("lg") or "").lower()
        if lg and lg != "other" and lg != "unknown":
            normalized_lg = LEAGUE_ALIASES_MAP.get(lg, lg)
            if normalized_lg:
                relevant_leagues.add(normalized_lg)
                
                # Check if pick needs odds (has no odds, or odds is 0/None)
                # We interpret "missing odds" as None, empty string, or 0/0.0
                current_odds = p.get("odds")
                is_missing_odds = current_odds in [None, "", 0, 0.0, "0"]
                if is_missing_odds:
                    picks_needing_odds.append(p)

    if not relevant_leagues:
        return picks

    # 2. Fetch scores (games) for Enrichment
    # We fetch ALL games (final_only=False) to ensure we catch scheduled games too
    logger.info(f"Fetching games for enrichment from {target_date} for leagues: {', '.join(sorted(relevant_leagues))}")
    try:
        games = fetch_scores_for_date(target_date, requested_leagues=list(relevant_leagues), final_only=False)
    except Exception as e:
        logger.error(f"Failed to fetch games for enrichment: {e}")
        # Even if score fetch fails, we might still want to try odds? 
        # But usually odds depend on similar connectivity. Let's return to avoid long timeouts if offline.
        return picks

    if not games:
        logger.info("No games found for enrichment.")
        # Proceeding to odds might be futile if no scores found, but let's allow flow to continue 
        # just in case odds API behaves differently (unlikely).
        # Actually, if no games, we can't build game_lookup, so standard enrichment fails.
        # But odds enrichment is separate. Let's keep going.

    # 3. Build a lookup map: (league, team_normalized) -> game_details
    # This allows fast O(1) lookup
    game_lookup: dict[tuple[str, str], dict[str, Any]] = {}

    if games:
        for game in games:
            league = game.get("league", "").lower()
            if not league:
                continue

            # Normalize team names from the API result
            team1_raw = game.get("team1", "")
            team2_raw = game.get("team2", "")

            team1_norm = normalize_string(team1_raw)
            team2_norm = normalize_string(team2_raw)

            # Store mapping for both teams
            # We assume the game is ON the target_date
            if team1_norm:
                game_lookup[(league, team1_norm)] = {"opponent": team2_raw, "game_date": target_date}

            if team2_norm:
                game_lookup[(league, team2_norm)] = {"opponent": team1_raw, "game_date": target_date}

    # 4. Enrich picks with Opponent/Date
    enriched_count = 0
    for p in picks:
        # Skip if already has opponent
        if p.get("opponent"):
            continue

        lg = (p.get("league") or p.get("lg") or "").lower()
        league = LEAGUE_ALIASES_MAP.get(lg, lg)

        if not league or league not in relevant_leagues:
            continue

        pick_text = normalize_string(p.get("pick", ""))

        # Strategy: Find which team in the game_lookup (for this league) is mentioned in the pick text
        candidate_teams = [k[1] for k in game_lookup.keys() if k[0] == league]

        matched_team = None
        longest_match_len = 0

        for team in candidate_teams:
            if team in pick_text:
                if len(team) > longest_match_len:
                    matched_team = team
                    longest_match_len = len(team)

        if matched_team:
            details = game_lookup.get((league, matched_team))
            if details:
                p["opponent"] = details["opponent"]
                p["game_date"] = details["game_date"]
                enriched_count += 1

    if enriched_count > 0:
        logger.info(f"Enriched {enriched_count} picks with game details (Opponent/Date).")
        
    # 5. Fetch and Enrich Odds (if needed)
    if picks_needing_odds:
        try:
            logger.info("Fetching odds to backfill missing data...")
            odds_data = fetch_odds_for_date(target_date)
            
            odds_enriched_count = 0
            for p in picks_needing_odds:
                # Re-check if we have league (it might have been missing before, but unlikely if we are here)
                lg = (p.get("league") or p.get("lg") or "").lower()
                league = LEAGUE_ALIASES_MAP.get(lg, lg)
                
                if not league:
                    continue
                    
                pick_text = p.get("pick", "")
                
                # Get specific odds for this pick
                matched_odds = get_odds_for_pick(pick_text, league, odds_data)
                
                if matched_odds:
                    # Determine which odd value to use based on pick type/text
                    
                    found_odd = None
                    pick_lower = pick_text.lower()
                    
                    # Simple heuristic mapping
                    home_team = matched_odds.get("home_team", "").lower()
                    away_team = matched_odds.get("away_team", "").lower()
                    
                    is_home = _is_team_in_text(home_team, pick_lower)
                    is_away = _is_team_in_text(away_team, pick_lower)
                    
                    # Detect Bet Type
                    is_over = "over" in pick_lower or " o " in pick_lower
                    is_under = "under" in pick_lower or " u " in pick_lower
                    is_spread = "+" in pick_text or "-" in pick_text # Very rough check for spread line
                    
                    if is_over:
                        found_odd = matched_odds.get("over_odds")
                    elif is_under:
                        found_odd = matched_odds.get("under_odds")
                    elif is_spread:
                        # Spread betting
                        if is_home:
                            found_odd = matched_odds.get("spread_home_odds")
                        elif is_away:
                            found_odd = matched_odds.get("spread_away_odds")
                    else:
                        # Default to Moneyline if no spread indicators
                        if is_home:
                             found_odd = matched_odds.get("moneyline_home")
                        elif is_away:
                             found_odd = matched_odds.get("moneyline_away")
                    
                    if found_odd:
                        p["odds"] = found_odd
                        p["deduction_source"] = "ESPN_API_BACKFILL"
                        odds_enriched_count += 1
                        
            if odds_enriched_count > 0:
                logger.info(f"Backfilled odds for {odds_enriched_count} picks from ESPN.")

        except Exception as e:
            logger.error(f"Failed to backfill odds: {e}")

    return picks

def _is_team_in_text(team_name: str, text: str) -> bool:
    """Helper to check if team name matches text."""
    if not team_name: return False
    # Check full name or significant parts
    if team_name in text: return True
    
    # Check words > 3 chars
    words = [w for w in team_name.split() if len(w) > 3]
    if not words: return False
    
    # Require at least one significant word if strict, but maybe simplistic is okay
    for w in words:
        if w in text:
            return True
            
    return False
