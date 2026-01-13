# src/grader.py
import re
import unicodedata
import requests
import logging
from collections import defaultdict
from src.team_aliases import TEAM_ALIASES

LEAGUE_ALIASES = {
    "ncaaf": ["ncaaf", "cfb"],
    "cfb": ["ncaaf", "cfb"],
    "ncaab": ["ncaab", "mcb"],
    "mcb": ["ncaab", "mcb"],
    "soccer": ["epl", "mls", "ucl", "championship", "laliga", "bundesliga", "seriea", "ligue1", "nwsl"],
    "tennis": ["atp", "wta"],
    "f1": ["f1"],
    "nascar": ["nascar"],
    "indycar": ["indycar"],
    "pga": ["pga"],
    "lpga": ["lpga"],
    "pll": ["pll"],
    "lacrosse": ["pll"],
}

def normalize_name(name):
    if not name: return ""
    return str(name).replace(" ", "").lower()

def normalize_text(text):
    if not text: return ""
    text = unicodedata.normalize("NFKC", str(text))
    return text.replace("\u00A0", " ").replace("\u202F", " ").strip()

def team_in_description(description_lower, team_key):
    aliases = TEAM_ALIASES.get(team_key, [])
    for alias in aliases:
        pattern = r'\b' + re.escape(alias.lower()) + r'\b'
        if re.search(pattern, description_lower):
            return True
    return False

def get_period_scores(game_obj, period_key):
    """
    Calculates scores for a specific period (1Q, 2Q, 1H, 2H, etc).
    Returns (score1, score2) or (None, None) if data missing.
    """
    if not game_obj: return None, None
    
    t1_lines = game_obj.get('team1_data', {}).get('linescores', [])
    t2_lines = game_obj.get('team2_data', {}).get('linescores', [])
    
    if not t1_lines or not t2_lines: return None, None
    
    # Map period keys to 1-based indices
    target_periods = []
    
    # Identify Sport/League Context to adjust period mapping
    league_ctx = game_obj.get('league', '').lower()
    
    # Soccer Specific Period Mapping
    if league_ctx in ['epl', 'mls', 'ucl', 'soccer', 'eng.1', 'usa.1', 'uefa.champions', 'championship', 'laliga', 'bundesliga', 'seriea', 'ligue1', 'nwsl']:
        if period_key == '1H': target_periods = [1]
        elif period_key == '2H': target_periods = [2]
    # Standard Mapping (Basketball/Football/etc)
    else:
        if period_key in ['1Q', '1P']: target_periods = [1]
        elif period_key in ['2Q', '2P']: target_periods = [2]
        elif period_key in ['3Q', '3P']: target_periods = [3]
        elif period_key in ['4Q', '4P']: target_periods = [4]
        elif period_key == '1H': target_periods = [1, 2]
        elif period_key == '2H': target_periods = [3, 4]
        
    if not target_periods: return None, None
    
    def sum_periods(linescores, periods):
        total = 0
        for p in linescores:
            if int(p.get('period', 0)) in periods:
                total += float(p.get('value', 0))
        return total

    s1 = sum_periods(t1_lines, target_periods)
    s2 = sum_periods(t2_lines, target_periods)
    return s1, s2

def extract_stat_value(stat_list, stat_name_variants):
    """
    Helper to find a stat value from ESPN statistics list.
    """
    for stat in stat_list:
        s_name = stat.get('name', '').lower()
        if any(v.lower() == s_name for v in stat_name_variants):
            try:
                return float(stat.get('displayValue', 0))
            except:
                return 0.0
    return None

def grade_prop_bet(bet_desc, game_obj):
    """
    Grades Team Props and Player Props based on 'Subject: Stat' format.
    Returns (Result, Summary) or (None, None) if not a prop bet.
    """
    if ':' not in bet_desc: return None, None
    
    parts = bet_desc.split(':', 1)
    subject = parts[0].strip()
    rest = parts[1].strip().lower()
    
    STAT_MAP = {
        'pts': ['points', 'pts', 'goals', 'g'], # Allow G for Pts in simple contexts, or keep separate? 
                                                # Better to keep separate but maybe Pts maps to Points (which NHL has)
        'reb': ['rebounds', 'reb', 'avgRebounds'],
        'ast': ['assists', 'ast', 'avgAssists', 'a'],
        'passyds': ['passingYards'],
        'rushyds': ['rushingYards'],
        'recyds': ['receivingYards'],
        '3pm': ['threePointFieldGoalsMade', '3PM'],
        'to': ['turnovers'],
        # NHL / MLB
        'g': ['goals', 'g'],
        'sog': ['shotsOnGoal', 'sog'],
        'h': ['hits', 'h'],
        'hr': ['homeRuns', 'hr'],
        'r': ['runs', 'r'],
        'sb': ['stolenBases', 'sb']
    }
    
    target_stat_key = None
    for key in STAT_MAP:
        if key in rest or any(x in rest for x in STAT_MAP[key]):
            target_stat_key = key
            break
            
    if not target_stat_key:
        return None, None 

    line_match = re.search(r'(?:over|under|o/u|>|<)\s*(\d+(\.\d+)?)', rest)
    if not line_match:
         return None, None
    
    line = float(line_match.group(1))
    is_over = 'over' in rest or 'o ' in rest or '>' in rest
    
    t1_name = normalize_name(game_obj['team1'])
    t2_name = normalize_name(game_obj['team2'])
    sub_norm = normalize_name(subject)
    
    prop_value = None
    found_subject = ""
    
    if sub_norm in t1_name or subject.lower() in game_obj['team1'].lower():
        found_subject = game_obj['team1']
        prop_value = extract_stat_value(game_obj.get('team1_data', {}).get('statistics', []), STAT_MAP[target_stat_key])
    elif sub_norm in t2_name or subject.lower() in game_obj['team2'].lower():
        found_subject = game_obj['team2']
        prop_value = extract_stat_value(game_obj.get('team2_data', {}).get('statistics', []), STAT_MAP[target_stat_key])
    
    if prop_value is None:
        def search_leaders(team_data):
            for cat in team_data.get('leaders', []):
                cat_name = cat.get('name', '').lower()
                is_correct_category = any(v.lower() == cat_name for v in STAT_MAP[target_stat_key])
                if not is_correct_category: continue
                
                for leader in cat.get('leaders', []):
                    ath = leader.get('athlete', {})
                    aname = ath.get('displayName', '') or ath.get('fullName', '')
                    if normalize_name(subject) in normalize_name(aname):
                         return float(leader.get('value', 0)), aname
            return None, None

        val1, name1 = search_leaders(game_obj.get('team1_data', {}))
        if val1 is not None:
            prop_value = val1
            found_subject = name1
        else:
            val2, name2 = search_leaders(game_obj.get('team2_data', {}))
            if val2 is not None:
                prop_value = val2
                found_subject = name2

    # --- Full Boxscore Search (On Demand) ---
    if prop_value is None and 'full_boxscore' in game_obj:
        # Map generic keys (pts, reb) to ESPN boxscore keys (usually abbreviations)
        # We need a robust mapper here because keys vary by sport
        # Basketball: pts, reb, ast, stl, blk, to, fg3
        # Football: passingYards, rushingYards, receivingYards
        
        box_players = game_obj['full_boxscore']
        target_keys = STAT_MAP[target_stat_key] # e.g. ['points', 'pts']
        
        for p in box_players:
            p_name = p.get('name', '')
            if normalize_name(subject) in normalize_name(p_name):
                # Found player, look for stat
                # Check all target keys against p keys
                for k in target_keys:
                    # Try exact match or lower
                    for p_key, p_val in p.items():
                        if p_key.lower() == k.lower():
                             try:
                                 prop_value = float(p_val)
                                 found_subject = p_name
                                 break
                             except: pass
                    if prop_value is not None: break
            if prop_value is not None: break

    if prop_value is None:
        return "Unknown (Player/Stat Not Found)", f"Missing data for {subject} {target_stat_key}"

    result = "PUSH"
    if prop_value > line: result = "Win" if is_over else "Loss"
    elif prop_value < line: result = "Loss" if is_over else "Win"
    
    return result, f"{found_subject} {target_stat_key}: {prop_value} vs {line}"

def interpret_bet_result(bet_desc, team1_name, team2_name, score1, score2, sport, game_obj=None):
    desc = bet_desc.lower()
    
    # --- 0. Multi-Competitor Grading (F1, Golf) ---
    if game_obj and game_obj.get('type') == 'multi_competitor':
        # Find the participant in the competitors list
        # Extract name from bet
        # Typically bet is "Max Verstappen Winner" or "Rory McIlroy Top 5"
        
        # Simple extraction: iterate competitors and see if name is in desc
        participant = None
        for comp in game_obj.get('competitors', []):
            if normalize_name(comp.get('name', '')) in normalize_name(desc):
                participant = comp
                break
        
        if not participant:
            return "Unknown (Participant Not Found in Results)"
            
        # Parse Bet Type
        # Winner
        if "winner" in desc or "to win" in desc:
            return "Win" if participant.get('winner') else "Loss"
            
        # Top X
        top_match = re.search(r'top\s*(\d+)', desc)
        if top_match:
            threshold = int(top_match.group(1))
            rank = participant.get('rank')
            if not rank: return "Unknown (Rank Missing)"
            
            # Rank might be string "T1" -> 1
            try:
                rank_val = int(re.sub(r'\D', '', str(rank)))
                return "Win" if rank_val <= threshold else "Loss"
            except:
                return "Unknown (Rank Parse Error)"
                
        # Matchups (e.g. "Verstappen vs Hamilton") - Harder to parse reliably without strict format
        # If we assume head-to-head format "A vs B" was parsed? 
        # Currently the grader calls this function with team1/team2 from the GAME, not the BET.
        # But for multi-competitor, team1/team2 are undefined/empty in the call args (passed as None usually).
        
        return "Unknown (Bet Type Not Supported for Multi-Competitor)"

    # --- Standard Head-to-Head Grading ---
    s1 = 0.0
    s2 = 0.0
    try:
        s1 = float(score1)
        s2 = float(score2)
    except (ValueError, TypeError):
        pass

    # TENNIS SPECIAL: If scores are 0 (common in some API feeds), calculate from linescores
    if sport in ['atp', 'wta', 'tennis'] and s1 == 0 and s2 == 0 and game_obj:
        # Calculate sets won
        t1_lines = game_obj.get('team1_data', {}).get('linescores') or []
        t2_lines = game_obj.get('team2_data', {}).get('linescores') or []
        
        # Count sets won
        # A set is won if 'winner': true in linescore or based on score comparison
        # But simpler: For Total Sets Over/Under, we just need Total Sets Played.
        # Total Sets = len(t1_lines) (assuming data is complete for completed matches)
        # Note: This overwrites s1/s2 to be "Sets Won"? No, just use total for O/U.
        # We can't easily reconstruction "Sets Won" without parsing inner linescore winners.
        # But for O/U Sets, we just need the sum.
        
        # Let's try to reconstruct s1/s2 (Sets Won) for Spread/Moneyline logic too.
        s1_sets = 0
        s2_sets = 0
        for i in range(len(t1_lines)):
            val1 = float(t1_lines[i].get('value', 0))
            val2 = float(t2_lines[i].get('value', 0)) if i < len(t2_lines) else 0
            # Tennis Set Logic: 6-4, 7-6, 6-0, etc.
            if val1 > val2: s1_sets += 1
            elif val2 > val1: s2_sets += 1
            # Incompleted sets? Ignore.
        
        if s1_sets + s2_sets > 0:
            s1 = float(s1_sets)
            s2 = float(s2_sets)

    # --- 0. PROPS ---
    if game_obj and ':' in bet_desc:
        res, summary = grade_prop_bet(bet_desc, game_obj)
        if res: 
            return res

    # --- 0.5 PERIOD BETS ---
    # Enhanced regex to catch "1st Inning", "1st Period", "1st Half"
    period_match = re.search(r'\b(?:([1-4]q|[12]h|[1-4]p)|(?:1st|2nd|3rd|4th)\s*(?:inning|period|half|quarter))\b', desc, re.IGNORECASE)
    
    if period_match and game_obj:
        raw_match = period_match.group(0).lower()
        p_key = None
        
        # Normalize to standard keys
        if '1st' in raw_match:
            if 'half' in raw_match: p_key = '1H'
            else: p_key = '1P' # Inning/Period/Quarter -> 1P/1Q (mapped to 1)
        elif '2nd' in raw_match:
            if 'half' in raw_match: p_key = '2H'
            else: p_key = '2P'
        elif '3rd' in raw_match: p_key = '3P'
        elif '4th' in raw_match: p_key = '4P'
        else:
            p_key = period_match.group(1).upper()

        ps1, ps2 = get_period_scores(game_obj, p_key)
        if ps1 is not None and ps2 is not None:
            s1, s2 = ps1, ps2

    # --- 1. TOTALS (Over/Under) ---
    # TENNIS EXCEPTION: Move Tennis logic BEFORE generic totals to capture "Games"
    if sport in ['atp', 'wta', 'tennis'] and (("over" in desc or "under" in desc) or re.search(r'\bo/?u\b', desc)):
        total_match = re.search(r'(?:over|under|o/u)\s*(\d+(\.\d+)?)', desc) or \
                      re.search(r'(\d+(\.\d+)?)\s*(?:over|under|o/u)', desc)
        
        if total_match:
            try:
                line = float(total_match.group(1))
                # Heuristic: If line > 6.0 OR explicit "games", grade as Total Games
                if line > 6.0 or "game" in desc:
                    def sum_games(linescores):
                        return sum(float(x.get('value', 0)) for x in linescores)
                        
                    # Safely get linescores - direct dict access if game_obj is valid
                    l1 = []
                    l2 = []
                    
                    if game_obj and isinstance(game_obj, dict):
                        t1d = game_obj.get('team1_data')
                        if t1d and isinstance(t1d, dict): l1 = t1d.get('linescores') or []
                        
                        t2d = game_obj.get('team2_data')
                        if t2d and isinstance(t2d, dict): l2 = t2d.get('linescores') or []
                    
                    total_games = sum_games(l1) + sum_games(l2)
                    is_over = "over" in desc or "o " in desc or desc.startswith("o")
                    if "under" in desc or "u " in desc: is_over = False
                    
                    if total_games == line: return "PUSH"
                    if is_over: return "Win" if total_games > line else "Loss"
                    else: return "Win" if total_games < line else "Loss"
            except: pass

    if "over" in desc or "under" in desc or re.search(r'\bo/?u\b', desc):
        total_match = re.search(r'(?:over|under|o/u)\s*(\d+(\.\d+)?)', desc) or \
                      re.search(r'(\d+(\.\d+)?)\s*(?:over|under|o/u)', desc) or \
                      re.search(r'\b(\d{2,}(\.\d+)?)\b', desc)
        
        if not total_match:
            return "Unknown (No Line Found)"
        
        try:
            line = float(total_match.group(1))
        except:
            return "Unknown (Line Parse Error)"

        total_score = s1 + s2
        is_over = "over" in desc or "o " in desc or desc.startswith("o")
        if "under" in desc or "u " in desc:
            is_over = False
        
        if total_score == line: return "PUSH"
        if is_over: return "Win" if total_score > line else "Loss"
        else: return "Win" if total_score < line else "Loss"

    # --- 1.5 TENNIS TOTALS (Games vs Sets) ---
    # Heuristic: If sport is Tennis and line > 6.0, assume Games.
    # Standard Set Totals: 2.5 (Bo3) or 3.5/4.5 (Bo5).
    # Standard Game Totals: 19.5, 20.5, 21.5, etc.
    # Linescores in Tennis are Games per Set.
    # If line > 6.0, we sum all linescores.
    
    if sport in ['atp', 'wta', 'tennis'] and (("over" in desc or "under" in desc) or re.search(r'\bo/?u\b', desc)):
        # Extract line again if not found above (re-use match if possible but simpler to re-parse specific to this block)
        total_match = re.search(r'(?:over|under|o/u)\s*(\d+(\.\d+)?)', desc) or \
                      re.search(r'(\d+(\.\d+)?)\s*(?:over|under|o/u)', desc)
        
        if total_match:
            try:
                line = float(total_match.group(1))
                # Check for Game Total vs Set Total
                if line > 6.0 or "game" in desc:
                    # Calculate Total Games
                    def sum_games(linescores):
                        return sum(float(x.get('value', 0)) for x in linescores)
                        
                    # Safely get linescores - direct dict access if game_obj is valid
                    l1 = []
                    l2 = []
                    
                    if game_obj and isinstance(game_obj, dict):
                        t1d = game_obj.get('team1_data')
                        if t1d and isinstance(t1d, dict): l1 = t1d.get('linescores') or []
                        
                        t2d = game_obj.get('team2_data')
                        if t2d and isinstance(t2d, dict): l2 = t2d.get('linescores') or []
                    
                    games1 = sum_games(l1)
                    games2 = sum_games(l2)
                    
                    total_games = games1 + games2
                    is_over = "over" in desc or "o " in desc or desc.startswith("o")
                    if "under" in desc or "u " in desc: is_over = False
                    
                    if total_games == line: return "PUSH"
                    if is_over: return "Win" if total_games > line else "Loss"
                    else: return "Win" if total_games < line else "Loss"
            except: pass

    # --- 2. SPREAD & MONEYLINE ---
    # Use strict regex matching on original names to prevent substring errors (e.g. 'uf' in 'buffalo')
    t1_lower = team1_name.lower()
    t2_lower = team2_name.lower()
    
    team1_mentioned = False
    team2_mentioned = False
    
    # A. Check via Aliases
    for k, v in TEAM_ALIASES.items():
        if team_in_description(desc, k):
            for alias in v:
                # Use regex with word boundaries
                pattern = r'\b' + re.escape(alias.lower()) + r'\b'
                if re.search(pattern, t1_lower): 
                    team1_mentioned = True
                if re.search(pattern, t2_lower): 
                    team2_mentioned = True
    
    # B. Check Direct Name
    def check_direct(team_name, text):
        clean_tn = re.escape(team_name.lower())
        return re.search(r'\b' + clean_tn + r'\b', text) is not None

    if not team1_mentioned and not team2_mentioned:
         if check_direct(team1_name, desc): 
             team1_mentioned = True
         if check_direct(team2_name, desc): 
             team2_mentioned = True

    picked_team_score = 0
    opponent_score = 0
    picked_team_name = ""
    picked_winner = False # New: Winner flag check

    if team1_mentioned and not team2_mentioned:
        picked_team_name = team1_name
        picked_team_score = s1
        opponent_score = s2
        if game_obj:
            picked_winner = game_obj.get('winner1', False)
    elif team2_mentioned and not team1_mentioned:
        picked_team_name = team2_name
        picked_team_score = s2
        opponent_score = s1
        if game_obj:
            picked_winner = game_obj.get('winner2', False)
    elif team1_mentioned and team2_mentioned:
        # Both teams mentioned. Check for Draw bet.
        if "draw" in desc or "tie" in desc:
            return "Win" if s1 == s2 else "Loss"
        
        # Check for Total (Over/Under) - already handled above? 
        # No, Totals are handled before this block.
        # So if we are here, it's not a total.
        return "Unknown (Team Ambiguity - Both teams found but not Draw/Total)"
    else:
        return "Unknown (Team Ambiguity - No teams found)"

    spread_val = 0.0
    is_ml = "ml" in desc or "moneyline" in desc
    
    clean_desc = desc.replace(picked_team_name.lower(), '')
    found_spread = re.findall(r'[+-]?\d+(\.\d+)?', clean_desc)
    
    if found_spread and not is_ml:
        try:
            candidates = [float(x[0]) for x in re.findall(r'([+-]?\d+(\.\d+)?)', clean_desc)]
            valid_spreads = [c for c in candidates if abs(c) < 50]
            if valid_spreads:
                spread_val = valid_spreads[-1] 
        except: pass
    
    if is_ml or spread_val == 0:
        # ML Logic
        
        # Explicit Draw Check (Soccer)
        # If user bet "Draw", we wouldn't be here because team1_mentioned would likely be false?
        # Or if they bet "Arsenal ML", we check if Arsenal won.
        # If it's a draw, Arsenal ML is a Loss.
        
        # Check Winner Flag first (Most reliable for Tennis/UFC/Soccer)
        if picked_winner: return "Win"
        
        # If picked winner is False:
        # It could be a Loss OR a Draw.
        # If score is tied, and sport has draws, it's a Loss for ML.
        # But if sport doesn't have draws (NBA), it shouldn't be tied (unless OT missing, but scores usually final).
        
        # Fallback to Score Comparison
        if picked_team_score > opponent_score: return "Win"
        elif picked_team_score < opponent_score: return "Loss"
        else: 
            # Tie
            if "draw" in desc or "tie" in desc: return "Win"
            
            # Soccer ML (3-way) is a LOSS on a draw
            if sport in ['epl', 'mls', 'ucl', 'soccer', 'championship', 'laliga', 'bundesliga', 'seriea', 'ligue1', 'nwsl']:
                return "Loss"
                
            return "PUSH"

    else:
        # Spread Logic
        adj_score = picked_team_score + spread_val
        if adj_score > opponent_score: return "Win"
        elif adj_score < opponent_score: return "Loss"
        else: return "PUSH"


def _find_matching_game(bet_text, potential_games):
    """
    Helper to find a matching game from a list of candidates.
    Returns the game object or None.
    Prioritizes matches where BOTH participants are found in the bet text.
    """
    desc_norm = normalize_text(bet_text).lower()
    
    best_match = None
    best_score = 0
    
    for game in potential_games:
        current_score = 0
        
        # --- Handle Multi-Competitor (F1, Golf) ---
        if game.get('type') == 'multi_competitor':
            # Check if any competitor in the list matches the bet text
            for comp in game.get('competitors', []):
                c_name = normalize_name(comp.get('name', ''))
                if c_name and c_name in normalize_name(bet_text):
                    # We found the EVENT because the player is in it.
                    return game
            
            # Also check event name (e.g. "Abu Dhabi Grand Prix")
            if normalize_name(game.get('name', '')) in normalize_name(bet_text):
                return game
                
            continue

        # --- Handle Head-to-Head (Standard) ---
        t1_name = game.get('team1', '')
        t2_name = game.get('team2', '')
        
        t1_norm = normalize_name(t1_name)
        t2_norm = normalize_name(t2_name)
        
        t1_match = False
        t2_match = False
        
        # 1. Alias Matching
        for k, v in TEAM_ALIASES.items():
            if team_in_description(desc_norm, k):
                for alias in v:
                    an = normalize_name(alias)
                    if an and an in t1_norm: t1_match = True
                    if an and an in t2_norm: t2_match = True
        
        # 2. Direct Matching
        # Helper functions defined outside conditional scope for reuse
        def strict_match(team, text):
            return re.search(r'\b' + re.escape(team.lower()) + r'\b', text.lower())

        def last_name_match(full_name, text):
            parts = full_name.split()
            if len(parts) > 1:
                last = parts[-1].lower()
                if len(last) > 2:
                    return re.search(r'\b' + re.escape(last) + r'\b', text.lower())
            return False

        if not t1_match:
            if strict_match(t1_name, bet_text): t1_match = True
            
            # Last Name Matching (Individual Sports)
            if not t1_match:
                league = game.get('league', '').lower()
                if league in ['atp', 'wta', 'ufc', 'f1', 'pga', 'racing', 'golf', 'mma', 'tennis']:
                    if last_name_match(t1_name, bet_text): t1_match = True

        if not t2_match:
            # Re-use strict_match from above
            if strict_match(t2_name, bet_text): t2_match = True
            
            # Last Name Matching
            if not t2_match:
                league = game.get('league', '').lower()
                if league in ['atp', 'wta', 'ufc', 'f1', 'pga', 'racing', 'golf', 'mma', 'tennis']:
                    if last_name_match(t2_name, bet_text): t2_match = True

        # 3. Player Matching (if no team matched yet)
        # Only checks if NEITHER matched, but we want to score it.
        # Actually, standard player props usually mention the player name, not necessarily the opponent.
        # But if the bet is "LeBron James Over 25 Pts", match score is 1 (LeBron found).
        # If bet is "Lakers vs Celtics", match score is 2.
        
        if t1_match: current_score += 1
        if t2_match: current_score += 1
        
        # Player Prop specific check (if ':' in bet)
        if current_score == 0 and ':' in bet_text:
             parts = bet_text.split(':', 1)
             subject = normalize_name(parts[0])
             
             def check_leaders(team_data):
                 if not team_data: return False
                 for cat in team_data.get('leaders', []):
                     for leader in cat.get('leaders', []):
                         p_name = leader.get('athlete', {}).get('displayName', '') or \
                                  leader.get('athlete', {}).get('fullName', '')
                         if subject in normalize_name(p_name): return True
                 return False

             if check_leaders(game.get('team1_data')) or check_leaders(game.get('team2_data')):
                 current_score = 1 # Treat as match found

        # 4. Check Full Boxscore (if available)
        if current_score == 0 and 'full_boxscore' in game and ':' in bet_text:
             parts = bet_text.split(':', 1)
             subject = normalize_name(parts[0])
             for p in game['full_boxscore']:
                 if subject in normalize_name(p.get('name', '')):
                     current_score = 1
                     break

        # Update Best Match
        if current_score > best_score:
            best_score = current_score
            best_match = game
            
        # Optimization: If perfect match (2), return immediately
        if best_score >= 2:
            return best_match

    return best_match




def fetch_full_boxscore(game_id, league_name):
    """
    Fetches full boxscore for a game on demand.
    Returns parsed list of athletes with stats.
    """
    # Map league name to API path
    SPORT_LEAGUE_MAP = {
        'nba': 'basketball/nba',
        'wnba': 'basketball/wnba',
        'ncaab': 'basketball/mens-college-basketball',
        'wncaab': 'basketball/womens-college-basketball',
        'ncaaf': 'football/college-football',
        'nfl': 'football/nfl',
        'nhl': 'hockey/nhl',
        'mlb': 'baseball/mlb',
        'epl': 'soccer/eng.1',
        'mls': 'soccer/usa.1',
        'ucl': 'soccer/uefa.champions',
        'championship': 'soccer/eng.2',
        'laliga': 'soccer/esp.1',
        'bundesliga': 'soccer/ger.1',
        'seriea': 'soccer/ita.1',
        'ligue1': 'soccer/fra.1',
        'nwsl': 'soccer/usa.nwsl',
        'atp': 'tennis/atp',
        'wta': 'tennis/wta',
        'f1': 'racing/f1',
        'nascar': 'racing/nascar-premier',
        'indycar': 'racing/irl',
        'pga': 'golf/pga',
        'lpga': 'golf/lpga',
        'pll': 'lacrosse/pll'
    }
    
    path = SPORT_LEAGUE_MAP.get(league_name.lower())
    if not path: return None

    url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={game_id}"
    try:
        # logging.info(f"Fetching full boxscore for {league_name} {game_id}")
        resp = requests.get(url, timeout=5, verify=False)
        if resp.status_code != 200: return None
        
        data = resp.json()
        box = data.get('boxscore', {})
        
        # Merge stats into a simplified list of players
        # Structure: boxscore['players'] -> list of teams -> statistics -> athletes
        all_players = []
        
        for team in box.get('players', []):
            team_stats = team.get('statistics', [])
            for stat_group in team_stats:
                stat_names = stat_group.get('names', [])
                stat_keys = stat_group.get('keys', [])
                
                for ath in stat_group.get('athletes', []):
                    p_obj = ath.get('athlete', {})
                    name = p_obj.get('displayName', '') or p_obj.get('fullName', '')
                    stats = ath.get('stats', [])
                    
                    # Create a stats dict
                    p_stats = {'name': name, 'id': p_obj.get('id')}
                    for i, val in enumerate(stats):
                        if i < len(stat_keys):
                            p_stats[stat_keys[i]] = val
                            
                    all_players.append(p_stats)
        return all_players

    except Exception as e:
        # logging.error(f"Failed to fetch boxscore: {e}")
        return None

def grade_picks(picks, scores):
    graded_results = []
    
    # Optimization: Index scores by league first
    scores_by_league = defaultdict(list)
    for g in scores:
        scores_by_league[g.get('league', '').lower()].append(g)

    # Cross-League Map
    CROSS_LEAGUE_MAP = {
        'ncaaf': 'ncaab',
        'ncaab': 'ncaaf',
        'cfb': 'ncaab'
    }

    for pick in picks:
        pick_obj = pick.copy()
        
        try:
            bet_text = str(pick.get('pick', ''))
            sport = str(pick.get('league', '')).lower()
            
            matched_game = None
            
            # --- Attempt 1: Primary League ---
            target_leagues = LEAGUE_ALIASES.get(sport, [sport])
            potential_games = []
            for tl in target_leagues:
                potential_games.extend(scores_by_league.get(tl, []))
            
            matched_game = _find_matching_game(bet_text, potential_games)
            
            # --- Attempt 2: Cross-League Fallback ---
            if not matched_game and sport in CROSS_LEAGUE_MAP:
                alt_sport = CROSS_LEAGUE_MAP[sport]
                # logging.info(f"Fallback check: {sport} -> {alt_sport} for '{bet_text}'")
                
                alt_leagues = LEAGUE_ALIASES.get(alt_sport, [alt_sport])
                alt_games = []
                for tl in alt_leagues:
                    alt_games.extend(scores_by_league.get(tl, []))
                
                matched_game = _find_matching_game(bet_text, alt_games)
                
                if matched_game:
                    # Found in other league! Update the pick object
                    pick_obj['league'] = alt_sport.upper()
                    # logging.info(f"Corrected League: {sport} -> {alt_sport}")
                    sport = alt_sport # Update local var for interpret logic if needed

            if matched_game:
                # Handle Multi-Competitor arguments safely
                if matched_game.get('type') == 'multi_competitor':
                    # Pass dummy values for team/score as they are handled inside interpret via game_obj
                    t1_arg, t2_arg, s1_arg, s2_arg = "", "", 0, 0
                else:
                    t1_arg = matched_game.get('team1', '')
                    t2_arg = matched_game.get('team2', '')
                    s1_arg = matched_game.get('score1', 0)
                    s2_arg = matched_game.get('score2', 0)

                result = interpret_bet_result(
                    bet_text,
                    t1_arg,
                    t2_arg,
                    s1_arg,
                    s2_arg,
                    sport,
                    game_obj=matched_game
                )

                # --- ON-DEMAND BOXSCORE FETCH ---
                if "Unknown (Player" in str(result) and matched_game.get('id'):
                    # Check if we already fetched boxscore for this game
                    if 'full_boxscore' not in matched_game:
                        box_stats = fetch_full_boxscore(matched_game['id'], matched_game['league'])
                        if box_stats:
                            matched_game['full_boxscore'] = box_stats
                    
                    # Retry grading with full boxscore context
                    if 'full_boxscore' in matched_game:
                        # Re-run interpret
                        result = interpret_bet_result(
                            bet_text,
                            t1_arg,
                            t2_arg,
                            s1_arg,
                            s2_arg,
                            sport,
                            game_obj=matched_game
                        )

                pick_obj['result'] = result
                if matched_game.get('type') == 'multi_competitor':
                     pick_obj['score_summary'] = f"Event: {matched_game.get('name', 'Unknown')}"
                else:
                     pick_obj['score_summary'] = f"{matched_game.get('team1')} {matched_game.get('score1')} - {matched_game.get('score2')} {matched_game.get('team2')}"
            else:
                pick_obj['result'] = "Pending/Unknown"
                pick_obj['score_summary'] = ""
        
        except Exception as e:
            pick_obj['result'] = "Error"
            pick_obj['score_summary'] = str(e)
            
        graded_results.append(pick_obj)
        
    return graded_results