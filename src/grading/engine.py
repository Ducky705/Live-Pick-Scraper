# src/grading/engine.py
"""
Core grading engine - evaluates picks against game results.
"""

import logging
from typing import List, Dict, Any, Optional, Union

from src.grading.schema import Pick, GradedPick, BetType, GradeResult
from src.grading.parser import PickParser
from src.grading.loader import DataLoader
from src.grading.matcher import Matcher
from src.grading.constants import STAT_KEY_MAP, SOCCER_LEAGUES, PERIOD_PATTERNS

logger = logging.getLogger(__name__)


class GraderEngine:
    """
    Main grading engine that evaluates picks against ESPN game data.
    """

    def __init__(self, scores: List[Dict[str, Any]]):
        """
        Initialize with pre-fetched scores.
        
        Args:
            scores: List of game dictionaries from DataLoader.fetch_scores()
        """
        self.scores = scores
        self._boxscore_cache: Dict[str, List[Dict]] = {}

    def grade(self, pick: Union[Pick, str], league_hint: str = "Other") -> GradedPick:
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

        try:
            # Route by bet type
            if pick.bet_type == BetType.PARLAY:
                return self._grade_parlay(pick)
            elif pick.bet_type == BetType.TEASER:
                return self._grade_parlay(pick)  # Same logic, just different type
            elif pick.bet_type == BetType.PERIOD:
                return self._grade_period(pick)
            elif pick.bet_type == BetType.PLAYER_PROP:
                return self._grade_prop(pick)
            elif pick.bet_type == BetType.TEAM_PROP:
                return self._grade_prop(pick)
            elif pick.bet_type == BetType.TOTAL:
                return self._grade_total(pick)
            elif pick.bet_type == BetType.SPREAD:
                return self._grade_spread(pick)
            elif pick.bet_type == BetType.MONEYLINE:
                return self._grade_moneyline(pick)
            else:
                return GradedPick(pick, GradeResult.PENDING, details="Unknown bet type")
                
        except Exception as e:
            logger.error(f"Error grading pick: {e}")
            return GradedPick(pick, GradeResult.ERROR, details=str(e))

    def grade_batch(self, picks: List[Dict[str, Any]]) -> List[GradedPick]:
        """
        Grade a batch of picks.
        
        Args:
            picks: List of dicts with 'pick' and 'league' keys
            
        Returns:
            List of GradedPick objects
        """
        results = []
        for p in picks:
            text = p.get('pick', p.get('p', ''))
            league = p.get('league', p.get('lg', 'other'))
            date = p.get('date')
            
            parsed = PickParser.parse(text, league, date)
            graded = self.grade(parsed)
            results.append(graded)
        
        return results

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
            leg_results=leg_results
        )

    # -------------------------------------------------------------------------
    # Period Grading
    # -------------------------------------------------------------------------

    def _grade_period(self, pick: Pick) -> GradedPick:
        """Grade a period-specific bet (1H, 1Q, F5, etc.)."""
        game = Matcher.find_game(pick.selection, pick.league, self.scores)
        if not game:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")

        # Get period scores
        period_scores = self._get_period_scores(game, pick.period)
        if period_scores is None:
            return GradedPick(pick, GradeResult.PENDING, details=f"Period {pick.period} data not available")

        ps1, ps2 = period_scores
        
        # Determine underlying bet type from metadata or re-parse
        underlying = pick.metadata.get('underlying_type', 'Moneyline')
        
        if underlying == 'Total' or pick.is_over is not None:
            # Total for period
            total = ps1 + ps2
            line = pick.line or 0
            summary = f"{pick.period} Total: {total} vs {line}"
            
            if pick.is_over:
                if total > line:
                    return GradedPick(pick, GradeResult.WIN, summary, game_id=game.get('id'))
                elif total < line:
                    return GradedPick(pick, GradeResult.LOSS, summary, game_id=game.get('id'))
            else:
                if total < line:
                    return GradedPick(pick, GradeResult.WIN, summary, game_id=game.get('id'))
                elif total > line:
                    return GradedPick(pick, GradeResult.LOSS, summary, game_id=game.get('id'))
            return GradedPick(pick, GradeResult.PUSH, summary, game_id=game.get('id'))
        
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
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game.get('id'))
            elif adj < ps_opp:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game.get('id'))
            return GradedPick(pick, GradeResult.PUSH, summary, game_id=game.get('id'))

    def _get_period_scores(self, game: Dict, period: str) -> Optional[tuple]:
        """Calculate scores for a specific period."""
        t1_lines = game.get('team1_data', {}).get('linescores', [])
        t2_lines = game.get('team2_data', {}).get('linescores', [])
        
        if not t1_lines or not t2_lines:
            return None
        
        # Map period to indices (1-based periods in ESPN data)
        period_map = {
            '1Q': [1], '2Q': [2], '3Q': [3], '4Q': [4],
            '1P': [1], '2P': [2], '3P': [3],
            '1H': [1, 2], '2H': [3, 4],
            'F5': [1, 2, 3, 4, 5], 'F3': [1, 2, 3], 'F1': [1]
        }
        
        target_periods = period_map.get(period, [])
        if not target_periods:
            return None
        
        def sum_periods(linescores, periods):
            total = 0
            for ls in linescores:
                p = int(ls.get('period', 0))
                if p in periods:
                    try:
                        total += float(ls.get('value', 0))
                    except:
                        pass
            return total
        
        return sum_periods(t1_lines, target_periods), sum_periods(t2_lines, target_periods)

    # -------------------------------------------------------------------------
    # Prop Grading
    # -------------------------------------------------------------------------

    def _grade_prop(self, pick: Pick) -> GradedPick:
        """Grade a player or team prop."""
        game = Matcher.find_game(pick.selection, pick.league, self.scores)
        if not game:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")

        game_id = game.get('id')
        
        # Try to find stat value
        stat_value = None
        found_name = pick.subject

        # 1. Check leaders data first (quick, no extra API call)
        leader, cat = Matcher.find_player_in_leaders(pick.subject, game)
        if leader:
            try:
                stat_value = float(leader.get('value', 0))
            except:
                pass

        # 2. Fetch full boxscore if needed
        if stat_value is None:
            boxscore = self._get_boxscore(game)
            if boxscore:
                player = Matcher.find_player_in_boxscore(pick.subject, boxscore)
                if player:
                    found_name = player.get('name', pick.subject)
                    stat_value = self._extract_stat(player, pick.stat)

        if stat_value is None:
            return GradedPick(
                pick, GradeResult.PENDING, 
                details=f"Stat {pick.stat} not found for {pick.subject}",
                game_id=game_id
            )

        # Compare
        line = pick.line or 0
        summary = f"{found_name} {pick.stat}: {stat_value} vs {line}"

        if pick.is_over:
            if stat_value > line:
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
            elif stat_value < line:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)
        else:
            if stat_value < line:
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
            elif stat_value > line:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        return GradedPick(pick, GradeResult.PUSH, summary, game_id=game_id)

    def _get_boxscore(self, game: Dict) -> Optional[List[Dict]]:
        """Get boxscore for a game, with caching."""
        game_id = game.get('id')
        if not game_id:
            return None
        
        if game_id in self._boxscore_cache:
            return self._boxscore_cache[game_id]
        
        if 'full_boxscore' in game:
            self._boxscore_cache[game_id] = game['full_boxscore']
            return game['full_boxscore']
        
        boxscore = DataLoader.fetch_boxscore(game)
        if boxscore:
            self._boxscore_cache[game_id] = boxscore
            game['full_boxscore'] = boxscore
        
        return boxscore

    def _extract_stat(self, player: Dict, stat_key: str) -> Optional[float]:
        """Extract a stat value from player data."""
        if not stat_key:
            return None
        
        stat_key_lower = stat_key.lower()
        
        # Handle combined stats (PRA)
        if stat_key_lower in ['pra', 'pts+reb+ast']:
            try:
                pts = float(player.get('points', player.get('pts', 0)))
                reb = float(player.get('rebounds', player.get('reb', player.get('totalrebounds', 0))))
                ast = float(player.get('assists', player.get('ast', 0)))
                return pts + reb + ast
            except:
                return None
        
        # Look up possible keys
        possible_keys = STAT_KEY_MAP.get(stat_key_lower, [stat_key_lower])
        
        for key in possible_keys:
            if key in player:
                try:
                    return float(player[key])
                except:
                    pass
            # Also check lowercase
            if key.lower() in player:
                try:
                    return float(player[key.lower()])
                except:
                    pass
        
        return None

    # -------------------------------------------------------------------------
    # Total Grading
    # -------------------------------------------------------------------------

    def _grade_total(self, pick: Pick) -> GradedPick:
        """Grade a total (over/under) bet."""
        game = Matcher.find_game(pick.selection, pick.league, self.scores)
        if not game:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")

        try:
            s1 = float(game.get('score1', 0) or 0)
            s2 = float(game.get('score2', 0) or 0)
        except:
            return GradedPick(pick, GradeResult.PENDING, details="Invalid scores")

        total = s1 + s2
        line = pick.line or 0
        
        # Sanity check: if total is 0 and line is > 5, scores are likely invalid
        # This catches tennis "game totals" where ESPN doesn't provide game counts
        if total == 0 and line > 5:
            return GradedPick(pick, GradeResult.PENDING, details="Scores appear invalid (0-0)")
        
        summary = f"Total: {total} vs {line}"
        game_id = game.get('id')

        if pick.is_over:
            if total > line:
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
            elif total < line:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)
        else:
            if total < line:
                return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
            elif total > line:
                return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        return GradedPick(pick, GradeResult.PUSH, summary, game_id=game_id)

    # -------------------------------------------------------------------------
    # Spread Grading
    # -------------------------------------------------------------------------

    def _grade_spread(self, pick: Pick) -> GradedPick:
        """Grade a spread bet."""
        game = Matcher.find_game(pick.selection, pick.league, self.scores)
        if not game:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")

        picked, opponent, is_t1 = Matcher.resolve_picked_team(pick.selection, game)
        if not picked:
            return GradedPick(pick, GradeResult.PENDING, details="Could not resolve team")

        try:
            s_picked = float(game['score1'] if is_t1 else game['score2'])
            s_opp = float(game['score2'] if is_t1 else game['score1'])
        except:
            return GradedPick(pick, GradeResult.PENDING, details="Invalid scores")

        line = pick.line or 0
        adj = s_picked + line
        summary = f"{picked} {s_picked} (+{line}={adj}) vs {opponent} {s_opp}"
        game_id = game.get('id')

        if adj > s_opp:
            return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
        elif adj < s_opp:
            return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        return GradedPick(pick, GradeResult.PUSH, summary, game_id=game_id)

    # -------------------------------------------------------------------------
    # Moneyline Grading
    # -------------------------------------------------------------------------

    def _grade_moneyline(self, pick: Pick) -> GradedPick:
        """Grade a moneyline bet."""
        game = Matcher.find_game(pick.selection, pick.league, self.scores)
        if not game:
            return GradedPick(pick, GradeResult.PENDING, details="Game not found")

        picked, opponent, is_t1 = Matcher.resolve_picked_team(pick.selection, game)
        if not picked:
            return GradedPick(pick, GradeResult.PENDING, details="Could not resolve team")

        # Check winner flags first
        winner_picked = game.get('winner1') if is_t1 else game.get('winner2')
        winner_opp = game.get('winner2') if is_t1 else game.get('winner1')

        try:
            s_picked = float(game['score1'] if is_t1 else game['score2'])
            s_opp = float(game['score2'] if is_t1 else game['score1'])
        except:
            s_picked = 0
            s_opp = 0

        # Build summary, handling None scores gracefully
        score1_display = game.get('score1') if game.get('score1') is not None else '?'
        score2_display = game.get('score2') if game.get('score2') is not None else '?'
        summary = f"{game['team1']} {score1_display} - {score2_display} {game['team2']}"
        game_id = game.get('id')

        if winner_picked:
            return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
        elif winner_opp:
            return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)

        # Fallback to score comparison
        if s_picked > s_opp:
            return GradedPick(pick, GradeResult.WIN, summary, game_id=game_id)
        elif s_picked < s_opp:
            return GradedPick(pick, GradeResult.LOSS, summary, game_id=game_id)
        
        # Tie handling
        league_lower = pick.league.lower()
        if league_lower in SOCCER_LEAGUES:
            # Soccer 3-way ML: Draw = Loss
            return GradedPick(pick, GradeResult.LOSS, summary + " (Draw)", game_id=game_id)
        
        return GradedPick(pick, GradeResult.PUSH, summary, game_id=game_id)
