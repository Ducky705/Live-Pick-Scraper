# src/grading/matcher.py
"""
Team and player matching logic using aliases and fuzzy matching.
"""

import re
import difflib
from typing import Any

from src.grading.constants import LEAGUE_ALIASES_MAP
from src.team_aliases import TEAM_ALIASES
from src.player_map import PLAYER_TO_TEAM_MAP


class Matcher:
    """
    Matches pick text to games and players using aliases and heuristics.
    """

    @staticmethod
    def _fuzzy_match(target: str, candidates: list[str], threshold: float = 0.85) -> str | None:
        """
        Find best fuzzy match from candidates.
        Uses difflib for typo tolerance and token-based matching for word reordering.
        """
        # 1. Standard difflib (SequenceMatcher) - Good for typos
        matches = difflib.get_close_matches(target, candidates, n=1, cutoff=threshold)
        if matches:
            return matches[0]

        # 2. Token Set Matching - Good for reordering ("State Golden" vs "Golden State")
        # and partial matches ("Warriors" vs "Golden State Warriors")
        best_token_match = None
        best_token_score = 0.0
        
        target_tokens = set(Matcher.normalize(target).split())
        if not target_tokens:
            return None
            
        for cand in candidates:
            cand_tokens = set(Matcher.normalize(cand).split())
            if not cand_tokens:
                continue
                
            intersection = target_tokens.intersection(cand_tokens)
            if not intersection:
                continue
                
            # Score: Intersection over Min Length (Subset logic)
            # "Golden State" (2) in "Golden State Warriors" (3) -> 2/2 = 1.0
            # "State Golden" (2) in "Golden State" (2) -> 2/2 = 1.0
            scan_len = len(intersection)
            # Use min length of tokens to favor subsets matches
            denom = min(len(target_tokens), len(cand_tokens))
            score = scan_len / denom if denom > 0 else 0
            
            if score > best_token_score:
                best_token_score = score
                best_token_match = cand
        
        # Threshold for token matching should be high (0.9 or 1.0 typically for subsets)
        # But let's be safe.
        if best_token_score >= 0.9: # Almost perfect subset/reorder
            return best_token_match
            
        return None

    @staticmethod
    def normalize(name: str) -> str:
        """Normalize a name for comparison."""
        if not name:
            return ""
        return name.lower().replace(".", "").replace("'", "").replace("-", " ").strip()

    @staticmethod
    def find_game(
        pick_text: str,
        league: str,
        games: list[dict[str, Any]],
        line: float | None = None,
        odds: int | None = None,
        bet_type: Any | None = None,  # Avoid circular import, pass BetType enum value or None
    ) -> dict[str, Any] | None:
        """
        Find the best matching game for a pick.

        Args:
            pick_text: The pick text
            league: League code
            games: List of game dictionaries
            line: Optional betting line (e.g. -5.5) for disambiguation
            odds: Optional odds (e.g. -110) for disambiguation
            bet_type: Optional bet type for contextual matching

        Returns:
            Best matching game or None
        """
        target_league = LEAGUE_ALIASES_MAP.get(league.lower(), league.lower())

        # Filter games by league
        league_games = [
            g
            for g in games
            if LEAGUE_ALIASES_MAP.get(g.get("league", "").lower(), g.get("league", "").lower()) == target_league
        ]

        if not league_games:
            # Try cross-league fallback for common confusions
            if target_league == "ncaaf":
                league_games = [g for g in games if g.get("league", "").lower() == "ncaab"]
            elif target_league == "ncaab":
                league_games = [g for g in games if g.get("league", "").lower() == "ncaaf"]
            # Tennis Combined Logic: "Tennis", "ATP", "WTA" should search all tennis
            elif target_league in ["atp", "wta", "tennis"]:
                league_games = [g for g in games if g.get("league", "").lower() in ["atp", "wta"]]

        # 1. Try to find in league-filtered games first
        if league_games:
            result = Matcher._find_best_match(pick_text, league_games)
            # If we found a result, but we have line context, check if it's the BEST result compared to others
            # Or if it was ambiguous.
            # For now, stick to original logic: if unique match found, return it.
            if result:
                 # AMBIGUITY CHECK ENHANCEMENT:
                 # Even if we found a match, check if there are OTHER matches in this league that complicate things.
                 # E.g. "Giants" in a league with "SF Giants" and "NY Giants" (unlikely in same league usually, but possible)
                 pass
            
            if result:
                return result
        
        # 1.5 AMBIGUITY CHECK (Contextual Disambiguation)
        # If no specific league context was useful, search ALL games.
        matches = Matcher._find_all_matches(pick_text, games)
        if matches:
             # If exactly one match found, we have found our team
             if len(matches) == 1:
                 return matches[0]
             
             # If multiple matches, use CONTEXT (Line/Odds) to resolve
             if line is not None or odds is not None:
                 best_context_match = Matcher._resolve_ambiguity_with_context(matches, pick_text, line, odds)
                 if best_context_match:
                     return best_context_match

             # If context didn't help, return None (ambiguous)
             pass
        
        # 1.5 AMBIGUITY CHECK (User Request: "Which Kings played?")
        # If no specific league context was useful, search ALL games.
        # But ensure we only find ONE matching team.
        matches = Matcher._find_all_matches(pick_text, games)
        if matches:
             # If exactly one match found, we have found our "Kings"
             if len(matches) == 1:
                 return matches[0]
             
             # If multiple matches, we can't be sure unless we have more context.
             # but maybe one is a "perfect" match and others are partial?
             # For now, if multiple matches exist, we consider it ambiguous and return None
             # (letting downstream logic or AI handle it)
             pass
        
        # 2b. Check Player Aliases (Superstar Mapping)
        # If pick mentions "LeBron", map to "Los Angeles Lakers" and search for that team
        pick_lower = pick_text.lower()
        for player_alias, team_name in PLAYER_TO_TEAM_MAP.items():
            if player_alias in pick_lower: # Simple substring check (e.g. "lebron" in "lebron james over")
                 # Find game with this team
                 # We simply re-run _find_best_match with the TEAM NAME
                 team_match = Matcher._find_best_match(team_name, league_games or games)
                 if team_match:
                     return team_match

        # Fallback: try all games if league filter failed
        if league_games != games:
            fallback_match = Matcher._find_best_match(pick_text, games)
            if fallback_match:
                return fallback_match

        # 3. Fuzzy Match Fallback (Typos)
        # Collect all team names from relevant games
        candidate_teams = {}
        target_games = league_games or games
        for g in target_games:
            t1 = Matcher.normalize(g.get("team1", ""))
            t2 = Matcher.normalize(g.get("team2", ""))
            candidate_teams[t1] = g
            candidate_teams[t2] = g
            
        pick_norm = Matcher.normalize(pick_text)
        # Check if any significant word in pick loosely matches a team name
        words = pick_norm.split()
        possible_targets = [w for w in words if len(w) > 3] # standardized words
        # Also try bigrams
        if len(words) > 1:
            possible_targets.extend([" ".join(words[i:i+2]) for i in range(len(words)-1)])
            
        for target in possible_targets:
            fuzzy = Matcher._fuzzy_match(target, list(candidate_teams.keys()), threshold=0.85)
            if fuzzy:
                return candidate_teams[fuzzy]

        # 4. Last Resort: Check if pick mentions a player in the games
        # This handles cases like "Jalen Brunson: Over 25.5" where team is implied
        for game in league_games or games:
             # Check leaders first (fast)
             leader, _ = Matcher.find_player_in_leaders(pick_text, game)
             if leader:
                 return game
             
             # Note: Checking full boxscore here might be too slow for all games, 
             # so we stick to leaders for now.
        
        return None

    @staticmethod
    def _find_best_match(pick_text: str, games: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find the best matching game from a list of games."""
        if not games:
            return None

        best_match = None
        best_score = 0
        pick_norm = Matcher.normalize(pick_text)

        for game in games:
            score = 0

            t1 = game.get("team1", "")
            t2 = game.get("team2", "")

            if Matcher._team_in_text(t1, pick_norm):
                score += 1
            if Matcher._team_in_text(t2, pick_norm):
                score += 1

            if score > best_score:
                best_score = score
                best_match = game

            # Perfect match optimization
            if best_score >= 2:
                return best_match

        # Return if at least one team matched
        return best_match if best_score >= 1 else None

    @staticmethod
    def _find_all_matches(pick_text: str, games: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Find ALL matching games for a pick text. 
        Used for ambiguity resolution (e.g. "Kings" -> [Sacramento Kings, LA Kings]).
        """
        matches = []
        pick_norm = Matcher.normalize(pick_text)
        
        candidates = []

        for game in games:
            score = 0
            t1 = game.get("team1", "")
            t2 = game.get("team2", "")

            if Matcher._team_in_text(t1, pick_norm):
                score += 1
            if Matcher._team_in_text(t2, pick_norm):
                score += 1
            
            if score > 0:
                matches.append(game)
                
        # Deduplicate by game ID
        unique_matches = []
        seen_ids = set()
        for m in matches:
            if m.get("id") not in seen_ids:
                unique_matches.append(m)
                seen_ids.add(m.get("id"))
                
        return unique_matches

        return unique_matches

    @staticmethod
    def _resolve_ambiguity_with_context(
        matches: list[dict[str, Any]], 
        pick_text: str, 
        line: float | None = None, 
        odds: int | None = None
    ) -> dict[str, Any] | None:
        """
        Resolve ambiguity between multiple matches using line/odds context.
        """
        if not matches:
            return None
            
        # Strategy:
        # If we have line info, we can't easily cross-reference unless we have implied lines or fetched odds.
        # But for now, we can check basic league-specific logic if lines differ vastly.
        # e.g. "Kings -5" -> NBA (Kings) vs NHL (Kings ML or -1.5)
        # 
        # But wait, we don't know the lines of the matches unless we have them.
        # However, we can use the 'league' of the matches to infer likelihood.
        # 
        # If matches are from different leagues, use line magnitude.
        # NBA lines: usually > 100 (for Total) or any spread.
        # NHL lines: usually < 10 (Total) or -1.5 (+/-).
        # MLB lines: usually -1.5 (+/-) or Total < 15.
        # NFL lines: Spread < 20, Total < 60.
        
        matches_by_league = {}
        for m in matches:
            lg = m.get("league", "").lower()
            matches_by_league[lg] = m
            
        # Case 1: NBA vs NHL ("Kings")
        nba_match = matches_by_league.get("nba")
        nhl_match = matches_by_league.get("nhl")
        
        if nba_match and nhl_match and line is not None:
             # If line is large (e.g. 220), it's NBA Total.
             if abs(line) > 15:
                 return nba_match
             # If line is -5, likely NBA (hockey rarely -5)
             if abs(line) > 2.5:
                 return nba_match
        
        # Case 2: NFL vs MLB ("Giants")
        nfl_match = matches_by_league.get("nfl")
        mlb_match = matches_by_league.get("mlb")
        
        if nfl_match and mlb_match and line is not None:
             # NFL spreads often 3, 7. MLB usually 1.5.
             if abs(line) > 2.0:
                 return nfl_match
        
        return None  # Still ambiguous

    @staticmethod
    def _team_in_text(team_name: str, text: str) -> bool:
        """Check if team is mentioned in text using aliases."""
        if not team_name:
            return False

        team_norm = Matcher.normalize(team_name)

        # 1. Direct word boundary match
        if re.search(r"\b" + re.escape(team_norm) + r"\b", text):
            return True

        # 2. Check all aliases
        for canonical, aliases in TEAM_ALIASES.items():
            # Check if this team matches the canonical or any alias
            is_match = team_norm == Matcher.normalize(canonical)
            if not is_match:
                for alias in aliases:
                    if Matcher.normalize(alias) in team_norm or team_norm in Matcher.normalize(alias):
                        is_match = True
                        break

            if is_match:
                # Check if any alias is in the text
                for alias in aliases:
                    alias_norm = Matcher.normalize(alias)
                    if alias_norm and re.search(r"\b" + re.escape(alias_norm) + r"\b", text):
                        return True
                    # Also check if text contains significant part of alias
                    alias_words = alias_norm.split()
                    if len(alias_words) >= 2:
                        # Try matching first two words (e.g., "golden state")
                        partial = " ".join(alias_words[:2])
                        if len(partial) > 5 and re.search(r"\b" + re.escape(partial) + r"\b", text):
                            return True

        # 3. Last word fallback (e.g., "Lakers" from "Los Angeles Lakers")
        words = team_norm.split()
        if len(words) > 1:
            last = words[-1]
            if len(last) > 2 and re.search(r"\b" + re.escape(last) + r"\b", text):
                return True

        # 4. First significant words fallback (e.g., "Golden State" from "Golden State Warriors")
        if len(words) >= 2:
            first_two = " ".join(words[:2])
            if len(first_two) > 5 and re.search(r"\b" + re.escape(first_two) + r"\b", text):
                return True

        return False

    @staticmethod
    def _find_alias_match(team_name: str, text: str) -> tuple[int, str]:
        """
        Find the starting position and the specific alias of the team in the text.
        Returns: (start_index, matched_alias)
        If not found, returns (-1, "")
        """
        if not team_name:
            return -1, ""

        team_norm = Matcher.normalize(team_name)
        
        # 1. Direct match
        idx = text.find(team_norm)
        if idx != -1:
            return idx, team_norm

        # 2. Check Aliases
        for canonical, aliases in TEAM_ALIASES.items():
            if Matcher.normalize(canonical) == team_norm:
                # Found the team entry
                for alias in aliases:
                    alias_norm = Matcher.normalize(alias)
                    idx = text.find(alias_norm)
                    if idx != -1:
                        # Ensure word boundary for short aliases to avoid partial matches
                        if len(alias_norm) <= 3:
                            # Strict boundary check simulated
                            # (Simple find isn't enough for "ers" inside "players")
                            # But for now, let's trust the alias list isn't too generic
                            pass
                        return idx, alias_norm
                break
        
        return -1, ""

    @staticmethod
    def resolve_picked_team(pick_text: str, game: dict[str, Any]) -> tuple[str | None, str | None, bool]:
        """
        Determine which team was picked in the bet.
        Returns:
            Tuple of (picked_team, opponent_team, is_team1)
        """
        t1 = game.get("team1", "")
        t2 = game.get("team2", "")
        pick_norm = Matcher.normalize(pick_text)

        t1_match = Matcher._team_in_text(t1, pick_norm)
        t2_match = Matcher._team_in_text(t2, pick_norm)

        if t1_match and not t2_match:
            return t1, t2, True
        elif t2_match and not t1_match:
            return t2, t1, False
        elif t1_match and t2_match:
            # Ambiguous: Both teams found
            
            # Find WHERE they are matched
            i1, match1 = Matcher._find_alias_match(t1, pick_norm)
            i2, match2 = Matcher._find_alias_match(t2, pick_norm)

            # Heuristic 1: Count occurrences of the MATCHED string
            c1 = pick_norm.count(match1) if match1 else 0
            c2 = pick_norm.count(match2) if match2 else 0
            
            if c1 > c2:
                return t1, t2, True
            if c2 > c1:
                return t2, t1, False

            # Heuristic 2: Proximity to Line (digits)
            digit_match = re.search(r"[+-]?\d+\.?\d*", pick_norm)
            if digit_match:
                digit_idx = digit_match.start()
                if i1 != -1 and i2 != -1:
                    dist1 = abs(digit_idx - i1)
                    dist2 = abs(digit_idx - i2)
                    
                    if dist1 < dist2 - 5:
                        return t1, t2, True
                    if dist2 < dist1 - 5:
                        return t2, t1, False
            
            # Heuristic 3: First Mentioned
            if i1 != -1 and i2 != -1:
                if i1 < i2:
                    return t1, t2, True
                else:
                    return t2, t1, False
                
        return None, None, False

    @staticmethod
    def find_player_in_boxscore(player_name: str, boxscore: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        Find a player in the boxscore data.

        Args:
            player_name: Player name to search for
            boxscore: List of player stat dictionaries

        Returns:
            Player stats dict or None
        """
        if not boxscore:
            return None

        target = Matcher.normalize(player_name)
        if not target:
             return None

        # Split into first/last name
        parts = target.split()
        last_name = parts[-1] if parts else target
        first_name = parts[0] if len(parts) > 1 else ""
        
        candidates = []
        candidate_map = {}

        for player in boxscore:
            p_name = Matcher.normalize(player.get("name", ""))
            candidates.append(p_name)
            candidate_map[p_name] = player

            # Full name match (Substring)
            if target in p_name or p_name in target:
                return player

            # Last name match (common for props)
            p_parts = p_name.split()
            p_last = p_parts[-1] if p_parts else p_name

            if last_name == p_last:
                # Verify first initial if available
                if first_name and p_parts:
                    p_first = p_parts[0]
                    if len(first_name) > 0 and len(p_first) > 0 and first_name[0] == p_first[0]:
                        return player
                else:
                    return player
        
        # Fuzzy Fallback
        fuzzy_name = Matcher._fuzzy_match(target, candidates, threshold=0.85)
        if fuzzy_name:
             return candidate_map[fuzzy_name]

        return None

    @staticmethod
    def find_player_in_leaders(
        player_name: str, game: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str | None]:
        """
        Find a player in the game's leaders data.

        Returns:
            Tuple of (leader_entry, stat_category) or (None, None)
        """
        target = Matcher.normalize(player_name)

        for team_key in ["team1_data", "team2_data"]:
            team_data = game.get(team_key, {})
            leaders = team_data.get("leaders", [])

            for category in leaders:
                cat_name = category.get("name", "")
                for leader in category.get("leaders", []):
                    athlete = leader.get("athlete", {})
                    p_name = athlete.get("displayName", "") or athlete.get("fullName", "")
                    p_norm = Matcher.normalize(p_name)
                    
                    # Check both directions: Is player in text? Or text in player?
                    if target in p_norm or p_norm in target:
                        return leader, cat_name

        return None, None
