# src/grading/engine.py
"""
Core grading engine - evaluates picks against game results.
"""

import logging
from typing import Any

from src.grading.constants import SOCCER_LEAGUES, STAT_KEY_MAP
from src.grading.loader import DataLoader
from src.grading.matcher import Matcher
from src.grading.parser import PickParser
from src.grading.schema import BetType, GradedPick, GradeResult, Pick
from src.grading.ai_resolver import AIResolver

logger = logging.getLogger(__name__)


class GraderEngine:
    """
    Main grading engine that evaluates picks against ESPN game data.
    """

    def __init__(self, scores: list[dict[str, Any]]):
        """
        Initialize with pre-fetched scores.

        Args:
            scores: List of game dictionaries from DataLoader.fetch_scores()
        """
        self.scores = scores
        self._boxscore_cache: dict[str, list[dict]] = {}

    def grade(self, pick: Pick | str, league_hint: str = "Other") -> GradedPick:
        """
        Grade a single pick.

        Args:
            pick: Pick object or raw string
            league_hint: League hint if pick is a string

        Returns:
            GradedPick with result
        """
        # Parse if string
        if isinstance(pick, str):
            pick = PickParser.parse(pick, league_hint)

        # VALIDITY CHECK (Garbage Disposal)
        # Avoid grading nonsense like "Over 6.5" or "Team ML" without context
        from src.grading.validity_filter import ValidityFilter
        
        validator = ValidityFilter()
        is_valid, reason = validator.is_valid(pick.raw_text, pick.league)
        
        if not is_valid:
             logger.warning(f"Pick rejected by ValidityFilter: {pick.raw_text} ({reason})")
             return GradedPick(pick, GradeResult.VOID, details=f"Invalid: {reason}")

        try:
            # Initial Grading
            if pick.bet_type == BetType.PARLAY:
                result = self._grade_parlay(pick)
            elif pick.bet_type == BetType.TEASER:
                result = self._grade_parlay(pick)
            elif pick.bet_type == BetType.PERIOD:
                result = self._grade_period(pick)
            elif pick.bet_type == BetType.PLAYER_PROP:
                result = self._grade_prop(pick)
            elif pick.bet_type == BetType.TEAM_PROP:
                result = self._grade_prop(pick)
            elif pick.bet_type == BetType.TOTAL:
                result = self._grade_total(pick)
            elif pick.bet_type == BetType.SPREAD:
                result = self._grade_spread(pick)
            elif pick.bet_type == BetType.MONEYLINE:
                result = self._grade_moneyline(pick)
            else:
                result = GradedPick(pick, GradeResult.PENDING, details="Unknown bet type")
            
            return result

        except Exception as e:
            logger.error(f"Error grading pick: {e}")
            return GradedPick(pick, GradeResult.ERROR, details=str(e))

    def _find_game(
        self, 
        text: str, 
        league: str, 
        line: float | None = None, 
        odds: int | None = None
    ) -> tuple[dict[str, Any], str | None] | None:
        """
        Find a game using rule-based Matcher, falling back to AIResolver.
        Returns: (game_dict, optional_resolved_team_name)
        """
        # 1. Rule-Based Match (Fast)
        game = Matcher.find_game(text, league, self.scores, line=line, odds=odds)
        if game:
            return game, None
            
        # 1.5 Roster Search (Deep)
        # If Matcher failed (likely because player isn't a leader or team isn't mentioned),
        # search full rosters of all games.
        roster_match = self._find_game_with_roster_search(text, league)
        if roster_match:
            return roster_match
            
        # 2. AI Fallback (Slow)
        # Only try if we have scores to search
        if self.scores:
            logger.info(f"Triggering AI Resolver for: {text}")
            result = AIResolver.resolve_pick(text, league, self.scores)
            if result:
                # result is now (game, resolved_team_name)
                return result
                
        return None

    def _find_game_with_roster_search(self, text: str, league: str) -> tuple[dict[str, Any], str | None] | None:
        """
        Deep search for player props by iterating all active game rosters.
        """
        # Only attempt if it looks like a player prop
        if not self._is_likely_player_prop(text):
            return None

        logger.info(f"Searching rosters for: {text}")
        
        # Determine target league games
        if league and league.lower() != "other":
             # Use Matcher's league logic implicitly or just filter manually
             target_league = league.lower()
             games_to_search = [g for g in self.scores if Matcher.normalize(g.get("league", "")) == Matcher.normalize(target_league)]
             if not games_to_search:
                 # Try aliases
                 from src.grading.constants import LEAGUE_ALIASES_MAP
                 target_norm = LEAGUE_ALIASES_MAP.get(target_league, target_league)
                 games_to_search = [g for g in self.scores if LEAGUE_ALIASES_MAP.get(g.get("league", "").lower(), "") == target_norm]
        else:
             games_to_search = self.scores

        # Search each game
        parsed = PickParser.parse(text, league)
        target_name = parsed.subject or text 
        
        for game in games_to_search:
            # 1. Check leaders first (Fast)
            leader, _ = Matcher.find_player_in_leaders(target_name, game)
            if leader:
                return game, None

            # 2. Fetch full boxscore (Slow)
            boxscore = self._get_boxscore(game)
            if boxscore:
                player = Matcher.find_player_in_boxscore(target_name, boxscore)
                if player:
                    logger.info(f"Found player {target_name} in {game['team1']} vs {game['team2']}")
                    return game, None
        
        return None

    def _is_likely_player_prop(self, text: str) -> bool:
        """Check if text looks like a player prop."""
        text_lower = text.lower()
        keywords = ["pts", "reb", "ast", "over", "under", "yds", "td", "rec", "goals", "shots", "sog", "pra"]
        return any(kw in text_lower for kw in keywords)


    def grade_batch(self, picks: list[dict[str, Any]]) -> list[GradedPick]:
        """
        Grade a batch of picks with optimized boxscore pre-fetching.

        Args:
            picks: List of dicts with 'pick' and 'league' keys

        Returns:
            List of GradedPick objects
        """
        # Pre-fetch boxscores for player props to avoid sequential API calls
        self._prefetch_boxscores_for_props(picks)

        results = []
        for p in picks:
            text = p.get("pick", p.get("p", ""))
            league = p.get("league", p.get("lg", "other"))
            date = p.get("date")

            parsed = PickParser.parse(text, league, date)
            graded = self.grade(parsed)
            results.append(graded)

        return results

    def _prefetch_boxscores_for_props(self, picks: list[dict[str, Any]]):
        """
        Pre-fetch boxscores in parallel for all player prop picks.
        This avoids sequential API calls during grading.
        """
        import concurrent.futures

        from src.score_cache import get_cache

        cache = get_cache()
        games_to_fetch = {}  # game_id -> game dict

        # Identify all player props and their games
        for p in picks:
            text = p.get("pick", p.get("p", ""))
            league = p.get("league", p.get("lg", "other"))

            # Quick heuristic check for player props (has ":" in text or common stat keywords)
            is_likely_prop = ":" in text or any(
                kw in text.lower() for kw in ["pts", "reb", "ast", "over", "under", "yds", "td", "rec"]
            )

            if not is_likely_prop:
                continue

            # Find matching game
            result = self._find_game(text, league)  # Props don't usually have a line compatible with disambiguation yet
            if not result:
                continue
            game, _ = result

            game_id = game.get("id")
            if not game_id:
                continue

            # Skip if already in memory cache
            if game_id in self._boxscore_cache:
                continue

            # Check persistent cache
            cached_boxscore = cache.get_boxscore(game_id)
            if cached_boxscore:
                self._boxscore_cache[game_id] = cached_boxscore
                continue

            # Need to fetch
            games_to_fetch[game_id] = game

        if not games_to_fetch:
            return

        logger.info(f"Pre-fetching {len(games_to_fetch)} boxscores for player props...")

        # Fetch in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(DataLoader.fetch_boxscore, game): game_id for game_id, game in games_to_fetch.items()
            }

            for future in concurrent.futures.as_completed(futures):
                game_id = futures[future]
                try:
                    boxscore = future.result()
                    if boxscore:
                        self._boxscore_cache[game_id] = boxscore
                        cache.set_boxscore(game_id, boxscore)
                except Exception as e:
                    logger.debug(f"Failed to fetch boxscore for {game_id}: {e}")

    # -------------------------------------------------------------------------
    # Parlay Grading
    # -------------------------------------------------------------------------

    def _grade_parlay(self, pick: Pick) -> GradedPick:
        """Grade a parlay by recursively grading each leg."""
        if not pick.legs:
            return GradedPick(pick, GradeResult.PENDING, details="No legs found in parlay")

        leg_results = []
        has_loss = False
        has_pending = False
        details_parts = []

        for leg in pick.legs:
            leg_result = self.grade(leg)
            leg_results.append(leg_result)
            details_parts.append(f"{leg.selection[:30]}: {leg_result.grade.value}")

            if leg_result.grade == GradeResult.LOSS:
                has_loss = True
            elif leg_result.grade in (GradeResult.PENDING, GradeResult.ERROR):
                has_pending = True

        # Determine overall result
        if has_loss:
            final_grade = GradeResult.LOSS
        elif has_pending:
            final_grade = GradeResult.PENDING
        else:
            # All must be WIN or PUSH
            all_push = all(r.grade == GradeResult.PUSH for r in leg_results)
            final_grade = GradeResult.PUSH if all_push else GradeResult.WIN

        return GradedPick(
            pick=pick,
            grade=final_grade,
            score_summary=f"{len(pick.legs)} legs",
            details=" / ".join(details_parts),
            leg_results=leg_results,
        )

    # -------------------------------------------------------------------------
    # Period Grading
    # -------------------------------------------------------------------------

    def _grade_period(self, pick: Pick) -> GradedPick:
        """Grade a period-specific bet (1H, 1Q, F5, etc.)."""
        # Pass context (line/odds) to help disambiguate
        result = self._find_game(pick.selection, pick.league, line=pick.line, odds=pick.odds)
        if not result:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")
        game, resolved_team = result

        # Backfill league
        if game and not pick.league:
            pick.league = game.get("league", "")

        # Get period scores
        if not pick.period:
            return GradedPick(pick, GradeResult.PENDING, details="Period not specified")

        period_scores = self._get_period_scores(game, pick.period)
        if period_scores is None:
            return GradedPick(pick, GradeResult.PENDING, details=f"Period {pick.period} data not available")

        ps1, ps2 = period_scores

        # Determine underlying bet type from metadata or re-parse
        underlying = pick.metadata.get("underlying_type", "Moneyline")

        if underlying == "Total" or pick.is_over is not None:
            # Total for period
            total = ps1 + ps2
            line = pick.line or 0
            summary = f"{pick.period} Total: {total} vs {line}"

            if pick.is_over:
                if total > line:
                    return GradedPick(pick, GradeResult.WIN, summary, game_id=game.get("id"))
                elif total < line:
                    return GradedPick(pick, GradeResult.LOSS, summary, game_id=game.get("id"))
            elif total < line:
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game.get("id"))
            elif total > line:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game.get("id"))
            return GradedPick(pick, GradeResult.PUSH, summary, game_id=game.get("id"))

        else:
            # Spread or ML for period
            picked, opponent, is_t1 = Matcher.resolve_picked_team(pick.selection, game)
            if not picked:
                return GradedPick(pick, GradeResult.PENDING, details="Could not resolve team")

            ps_picked = ps1 if is_t1 else ps2
            ps_opp = ps2 if is_t1 else ps1

            line = pick.line or 0
            adj = ps_picked + line
            summary = f"{pick.period}: {picked} {ps_picked}+{line}={adj} vs {opponent} {ps_opp}"

            if adj > ps_opp:
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game.get("id"))
            elif adj < ps_opp:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game.get("id"))
            return GradedPick(pick, GradeResult.PUSH, summary, game_id=game.get("id"))

    def _get_period_scores(self, game: dict, period: str) -> tuple | None:
        """Calculate scores for a specific period."""
        t1_lines = game.get("team1_data", {}).get("linescores", [])
        t2_lines = game.get("team2_data", {}).get("linescores", [])

        if not t1_lines or not t2_lines:
            return None

        # Map period to indices (1-based periods in ESPN data)
        period_map = {
            "1Q": [1],
            "2Q": [2],
            "3Q": [3],
            "4Q": [4],
            "1P": [1],
            "2P": [2],
            "3P": [3],
            "1H": [1, 2],
            "2H": [3, 4],
            "F5": [1, 2, 3, 4, 5],
            "F3": [1, 2, 3],
            "F1": [1],
        }

        target_periods = period_map.get(period, [])
        if not target_periods:
            return None

        def sum_periods(linescores, periods):
            total = 0
            for ls in linescores:
                p = int(ls.get("period", 0))
                if p in periods:
                    try:
                        total += float(ls.get("value", 0))
                    except (ValueError, TypeError):
                        pass  # Skip invalid period scores
            return total

        return sum_periods(t1_lines, target_periods), sum_periods(t2_lines, target_periods)

    # -------------------------------------------------------------------------
    # Prop Grading
    # -------------------------------------------------------------------------

    def _grade_prop(self, pick: Pick) -> GradedPick:
        """Grade a player or team prop."""
        # Props usually target players, but team props might need context.
        result = self._find_game(pick.selection, pick.league, line=pick.line, odds=pick.odds)
        if not result:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")
        game, resolved_team = result

        # Backfill league
        if game and not pick.league:
            pick.league = game.get("league", "")

        game_id = game.get("id")

        # Ensure subject and stat are present
        if not pick.subject or not pick.stat:
            return GradedPick(pick, GradeResult.PENDING, details="Missing subject or stat for prop bet")

        # Try to find stat value
        stat_value = None
        found_name = pick.subject

        # 1. Check leaders data first (quick, no extra API call)
        leader, cat = Matcher.find_player_in_leaders(pick.subject, game)
        if leader:
            try:
                stat_value = float(leader.get("value", 0))
            except:
                pass

        # 2. Check Team Stats (for Team Props)
        # Check if subject matches team names
        is_team_prop = False
        team_key = None
        
        if Matcher._team_in_text(game["team1"], pick.subject):
            team_key = "team1_data"
            is_team_prop = True
        elif Matcher._team_in_text(game["team2"], pick.subject):
            team_key = "team2_data"
            is_team_prop = True
        elif pick.subject == game["team1"] or pick.subject in game["team1"]:
             team_key = "team1_data"
             is_team_prop = True
        elif pick.subject == game["team2"] or pick.subject in game["team2"]:
             team_key = "team2_data"
             is_team_prop = True
            
        if is_team_prop:
            # Look in team statistics
            team_stats = game.get(team_key, {}).get("statistics", [])
            # Extract stat
            # Common team props: Total Points, Rebounds, etc.
            # Map "Total Points" -> "points"
            # Extract stat
            # Common team props: Total Points, Rebounds, etc.
            # Map "Total Points" -> "points"
            clean_stat = pick.stat.lower().replace("total", "").strip()
            # Also handle camelCase in pick.stat if necessary, but lower() handles that.
            
            for stat_entry in team_stats:
                entry_name = stat_entry.get("name", "").lower()
                entry_abbr = stat_entry.get("abbreviation", "").lower()
                
                # Check exact or partial match
                if (clean_stat == entry_name or 
                    clean_stat == entry_abbr or
                    clean_stat in entry_name or
                    entry_name in clean_stat): # Check for containment (e.g. yards vs totalYards)
                    try:
                        stat_value = float(stat_entry.get("displayValue", "0"))
                        found_name = pick.subject
                        break
                    except:
                        pass
        
        # 3. Fetch full boxscore if still not found (Player Props deeper search)
        if stat_value is None and not is_team_prop:
            boxscore = self._get_boxscore(game)
            if boxscore:
                player = Matcher.find_player_in_boxscore(pick.subject, boxscore)
                if player:
                    found_name = player.get("name", pick.subject)
                    stat_value = self._extract_stat(player, pick.stat)

        if stat_value is None:
            return GradedPick(
                pick, GradeResult.PENDING, details=f"Stat {pick.stat} not found for {pick.subject}", game_id=game_id
            )

        # Compare
        line = pick.line or 0
        summary = f"{found_name} {pick.stat}: {stat_value} vs {line}"

        if pick.is_over:
            if stat_value > line:
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
            elif stat_value < line:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)
        elif stat_value < line:
            return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
        elif stat_value > line:
            return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        return GradedPick(pick, GradeResult.PUSH, summary, game_id=game_id)

    def _get_boxscore(self, game: dict) -> list[dict] | None:
        """Get boxscore for a game, with memory and persistent caching."""
        from src.score_cache import get_cache

        game_id = game.get("id")
        if not game_id:
            return None

        # 1. Check memory cache
        if game_id in self._boxscore_cache:
            return self._boxscore_cache[game_id]

        # 2. Check game object
        if "full_boxscore" in game:
            self._boxscore_cache[game_id] = game["full_boxscore"]
            return game["full_boxscore"]

        # 3. Check persistent cache
        cache = get_cache()
        cached = cache.get_boxscore(game_id)
        if cached:
            self._boxscore_cache[game_id] = cached
            return cached

        # 4. Fetch from API
        boxscore = DataLoader.fetch_boxscore(game)
        if boxscore:
            # DataLoader returns confirmed flattened list[dict]
            flat_boxscore = boxscore
            self._boxscore_cache[game_id] = flat_boxscore
            game["full_boxscore"] = flat_boxscore
            cache.set_boxscore(game_id, flat_boxscore) 
            return flat_boxscore

        return None

    def _flatten_boxscore(self, raw_boxscore: dict) -> list[dict]:
        """Flatten ESPN boxscore into a list of player dicts with named stats."""
        players_list = []
        
        # ESPN Boxscore structure: boxscore['players'] -> List of Team Groups
        team_groups = raw_boxscore.get("players", [])
        if not isinstance(team_groups, list):
             return []
             
        for team_group in team_groups:
            stats_groups = team_group.get("statistics", [])
            team_name = team_group.get("team", {}).get("displayName", "")
            
            for stat_cat in stats_groups:
                keys = stat_cat.get("keys", []) # e.g. ["min", "points", ...]
                # If keys missing, fallback to lowercased names
                if not keys:
                    keys = [n.lower() for n in stat_cat.get("names", [])]
                
                athletes = stat_cat.get("athletes", [])
                for entry in athletes:
                    athlete_data = entry.get("athlete", {})
                    # Name construction
                    name = athlete_data.get("displayName")
                    if not name:
                         fname = athlete_data.get("firstName", "")
                         lname = athlete_data.get("lastName", "")
                         if fname or lname:
                             name = f"{fname} {lname}".strip()
                         else:
                             name = "Unknown"
                    
                    stats_values = entry.get("stats", [])
                    
                    # Create player dict
                    p_dict = {
                        "name": name,
                        "team": team_name,
                        "id": athlete_data.get("id"),
                    }
                    
                    # Map keys to values
                    for i, key in enumerate(keys):
                        if i < len(stats_values):
                            p_dict[key] = stats_values[i]
                            
                    players_list.append(p_dict)
                    
        return players_list

    def _extract_stat(self, player: dict, stat_key: str) -> float | None:
        """Extract a stat value from player data."""
        if not stat_key:
            return None

        stat_key_lower = stat_key.lower()

        # Handle combined stats (PRA)
        if stat_key_lower in ["pra", "pts+reb+ast"]:
            try:
                pts = float(player.get("points", player.get("pts", 0)))
                reb = float(player.get("rebounds", player.get("reb", player.get("totalrebounds", 0))))
                ast = float(player.get("assists", player.get("ast", 0)))
                return pts + reb + ast
            except (ValueError, TypeError):
                return None

        # Look up possible keys
        possible_keys = STAT_KEY_MAP.get(stat_key_lower, [stat_key_lower])

        for key in possible_keys:
            if key in player:
                try:
                    return float(player[key])
                except (ValueError, TypeError):
                    pass  # Try next key
            # Also check lowercase
            if key.lower() in player:
                try:
                    return float(player[key.lower()])
                except (ValueError, TypeError):
                    pass  # Try next key

        return None

    # -------------------------------------------------------------------------
    # Total Grading
    # -------------------------------------------------------------------------

    def _grade_total(self, pick: Pick) -> GradedPick:
        """Grade a total (over/under) bet."""
        # Total line is very useful for disambiguation (NBA vs NHL)
        result = self._find_game(pick.selection, pick.league, line=pick.line, odds=pick.odds)
        if not result:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")
        game, resolved_team = result

        # Backfill league
        if game and not pick.league:
            pick.league = game.get("league", "")

        try:
            s1 = float(game.get("score1", 0) or 0)
            s2 = float(game.get("score2", 0) or 0)
        except:
            return GradedPick(pick, GradeResult.PENDING, details="Invalid scores")

        total = s1 + s2
        line = pick.line or 0

        # Sanity check: if total is 0 and line is > 5, scores are likely invalid
        # This catches tennis "game totals" where ESPN doesn't provide game counts
        if total == 0 and line > 5:
            return GradedPick(pick, GradeResult.PENDING, details="Scores appear invalid (0-0)")

        summary = f"Total: {total} vs {line}"
        game_id = game.get("id")

        if pick.is_over:
            if total > line:
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
            elif total < line:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)
        elif total < line:
            return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
        elif total > line:
            return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        return GradedPick(pick, GradeResult.PUSH, summary, game_id=game_id)

    # -------------------------------------------------------------------------
    # Spread Grading
    # -------------------------------------------------------------------------

    def _grade_spread(self, pick: Pick) -> GradedPick:
        """Grade a spread bet."""
        # Spread line is useful
        result = self._find_game(pick.selection, pick.league, line=pick.line, odds=pick.odds)
        if not result:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")
        game, resolved_team = result

        # POST-AI NORMALIZATION
        if resolved_team:
            pick.selection = resolved_team

        # Backfill league
        if game and not pick.league:
            pick.league = game.get("league", "")

        picked, opponent, is_t1 = Matcher.resolve_picked_team(pick.selection, game)
        if not picked:
            return GradedPick(pick, GradeResult.PENDING, details="Could not resolve team")

        try:
            s_picked = float(game["score1"] if is_t1 else game["score2"])
            s_opp = float(game["score2"] if is_t1 else game["score1"])
        except:
            return GradedPick(pick, GradeResult.PENDING, details="Invalid scores")

        line = pick.line or 0
        adj = s_picked + line
        summary = f"{picked} {s_picked} (+{line}={adj}) vs {opponent} {s_opp}"
        game_id = game.get("id")

        if adj > s_opp:
            return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
        elif adj < s_opp:
            return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        return GradedPick(pick, GradeResult.PUSH, summary, game_id=game_id)

    # -------------------------------------------------------------------------
    # Moneyline Grading
    # -------------------------------------------------------------------------

    def _grade_moneyline(self, pick: Pick) -> GradedPick:
        result = self._find_game(pick.selection, pick.league, line=pick.line, odds=pick.odds)
        if not result:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")
        game, resolved_team = result

        # POST-AI NORMALIZATION
        if resolved_team:
            pick.selection = resolved_team

        # Backfill league
        if game and not pick.league:
            pick.league = game.get("league", "")

        # Draw Handling
        if "draw" in pick.selection.lower() and "vs" in pick.selection.lower():
             # Implicit Draw pick (e.g. "Team A vs Team B Draw")
             is_draw_pick = True
             picked = "Draw"
        elif pick.selection.lower() == "draw":
             is_draw_pick = True
             picked = "Draw"
        else:
             is_draw_pick = False
             picked, opponent, is_t1 = Matcher.resolve_picked_team(pick.selection, game)

        if not picked and not is_draw_pick:
            return GradedPick(pick, GradeResult.PENDING, details="Could not resolve team")

        # Check winner flags first
        winner_picked = False
        winner_opp = False
        
        # Only check winner flags if it's a team pick
        if not is_draw_pick:
             is_t1 = (picked == game.get("team1")) or (picked == game.get("team1_display")) 
             # Safety re-resolve
             p_resolv, o_resolv, is_t1_flag = Matcher.resolve_picked_team(picked, game)
             if p_resolv:
                 is_t1 = is_t1_flag

             winner_picked = game.get("winner1") if is_t1 else game.get("winner2")
             winner_opp = game.get("winner2") if is_t1 else game.get("winner1")

        try:
            s1 = float(game.get("score1") or 0)
            s2 = float(game.get("score2") or 0)
        except:
            s1 = 0
            s2 = 0

        score1_display = game.get("score1") if game.get("score1") is not None else "?"
        score2_display = game.get("score2") if game.get("score2") is not None else "?"
        summary = f"{game['team1']} {score1_display} - {score2_display} {game['team2']}"
        game_id = game.get("id")

        if is_draw_pick:
            # Check for Draw
            # If status is None, assume Final (as we load from final-only source or validated matches)
            status = game.get("status")
            is_final = status == "STATUS_FINAL" or status is None
            
            if s1 == s2 and is_final: 
                 return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
            elif is_final:
                 return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)
            return GradedPick(pick, GradeResult.PENDING, summary, game_id=game_id)
        
        if winner_picked:
             return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
        elif winner_opp:
             return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        # Fallback to score comparison
        s_picked = s1 if is_t1 else s2
        s_opp = s2 if is_t1 else s1

        if s_picked > s_opp:
            return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
        elif s_picked < s_opp:
            return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        # Tie handling
        league_lower = pick.league.lower()
        if league_lower in SOCCER_LEAGUES:
            return GradedPick(pick, GradeResult.LOSS, summary + " (Draw)", game_id=game_id)

        return GradedPick(pick, GradeResult.PUSH, summary, game_id=game_id)
