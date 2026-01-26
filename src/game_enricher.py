import logging
from typing import List, Dict, Any, Tuple
from src.score_fetcher import fetch_scores_for_date
from src.grading.constants import LEAGUE_ALIASES_MAP
from src.utils import normalize_string

logger = logging.getLogger(__name__)

def enrich_picks(picks: List[Dict[str, Any]], target_date: str) -> List[Dict[str, Any]]:
    """
    Enrich picks with opponent and game_date by looking up games in ESPN.
    
    Args:
        picks: List of pick dictionaries
        target_date: Date string (YYYY-MM-DD)
        
    Returns:
        Updated list of picks with 'opponent' and 'game_date' fields populated where found.
    """
    if not picks:
        return picks

    # 1. Identify relevant leagues
    relevant_leagues = set()
    for p in picks:
        # Skip if already enriched or has unknown league
        if p.get("opponent"):
            continue
            
        lg = (p.get("league") or p.get("lg") or "").lower()
        if lg and lg != "other" and lg != "unknown":
            normalized_lg = LEAGUE_ALIASES_MAP.get(lg, lg)
            if normalized_lg:
                relevant_leagues.add(normalized_lg)

    if not relevant_leagues:
        return picks

    # 2. Fetch scores (games)
    # We fetch ALL games (final_only=False) to ensure we catch scheduled games too
    logger.info(f"Fetching games for enrichment from {target_date} for leagues: {', '.join(sorted(relevant_leagues))}")
    try:
        games = fetch_scores_for_date(
            target_date,
            requested_leagues=list(relevant_leagues),
            final_only=False
        )
    except Exception as e:
        logger.error(f"Failed to fetch games for enrichment: {e}")
        return picks
    
    if not games:
        logger.info("No games found for enrichment.")
        return picks
    
    # 3. Build a lookup map: (league, team_normalized) -> game_details
    # This allows fast O(1) lookup
    game_lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    
    for game in games:
        league = game.get("league", "").lower()
        if not league: continue
        
        # Normalize team names from the API result
        team1_raw = game.get("team1", "")
        team2_raw = game.get("team2", "")
        
        team1_norm = normalize_string(team1_raw)
        team2_norm = normalize_string(team2_raw)
        
        # Store mapping for both teams
        # We assume the game is ON the target_date
        
        # Key: (league, team_name)
        # Note: In fetch_scores_for_date, team1 is usually Home, team2 is Away
        if team1_norm:
            game_lookup[(league, team1_norm)] = {
                "opponent": team2_raw,
                "game_date": target_date
            }
        
        if team2_norm:
            game_lookup[(league, team2_norm)] = {
                "opponent": team1_raw,
                "game_date": target_date
            }

    # 4. Enrich picks
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
        # We filter keys by league to reduce search space
        candidate_teams = [k[1] for k in game_lookup.keys() if k[0] == league]
        
        matched_team = None
        longest_match_len = 0
        
        for team in candidate_teams:
            # Check if team name is in pick text
            # e.g. team="lakers", pick="lakers -5" -> Match
            # We use simple substring check on normalized strings
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
    
    return picks
