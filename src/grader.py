# src/grader.py
import re
import unicodedata
from collections import defaultdict
from src.team_aliases import TEAM_ALIASES

LEAGUE_ALIASES = {
    "ncaaf": ["ncaaf", "cfb"],
    "cfb": ["ncaaf", "cfb"],
    "ncaab": ["ncaab", "mcb"],
    "mcb": ["ncaab", "mcb"],
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

def interpret_bet_result(bet_desc, team1_name, team2_name, score1, score2, sport):
    try:
        s1 = float(score1)
        s2 = float(score2)
    except (ValueError, TypeError):
        return "Error: Invalid Score"

    desc = bet_desc.lower()

    # --- 1. TOTALS (Over/Under) ---
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

    # --- 2. SPREAD & MONEYLINE ---
    t1_norm = normalize_name(team1_name)
    t2_norm = normalize_name(team2_name)
    
    team1_mentioned = False
    team2_mentioned = False
    
    # A. Check via Aliases
    for k, v in TEAM_ALIASES.items():
        if team_in_description(desc, k):
            for alias in v:
                an = normalize_name(alias)
                if an and an in t1_norm: team1_mentioned = True
                if an and an in t2_norm: team2_mentioned = True
    
    # B. Check Direct Name
    def check_direct(team_name, text):
        clean_tn = re.escape(team_name.lower())
        return re.search(r'\b' + clean_tn + r'\b', text) is not None

    if not team1_mentioned and not team2_mentioned:
         if check_direct(team1_name, desc): team1_mentioned = True
         if check_direct(team2_name, desc): team2_mentioned = True

    picked_team_score = 0
    opponent_score = 0
    picked_team_name = ""

    if team1_mentioned and not team2_mentioned:
        picked_team_name = team1_name
        picked_team_score = s1
        opponent_score = s2
    elif team2_mentioned and not team1_mentioned:
        picked_team_name = team2_name
        picked_team_score = s2
        opponent_score = s1
    else:
        return "Unknown (Team Ambiguity)"

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
        if picked_team_score > opponent_score: return "Win"
        elif picked_team_score < opponent_score: return "Loss"
        else: return "PUSH"
    else:
        adj_score = picked_team_score + spread_val
        if adj_score > opponent_score: return "Win"
        elif adj_score < opponent_score: return "Loss"
        else: return "PUSH"

def grade_picks(picks, scores):
    graded_results = []
    
    # Optimization: Index scores by league first
    scores_by_league = defaultdict(list)
    for g in scores:
        scores_by_league[g.get('league', '').lower()].append(g)

    for pick in picks:
        pick_obj = pick.copy()
        
        try:
            bet_text = str(pick.get('pick', ''))
            sport = str(pick.get('league', '')).lower()
            
            matched_game = None
            
            # Only look at games in the relevant league(s)
            target_leagues = LEAGUE_ALIASES.get(sport, [sport])
            potential_games = []
            for tl in target_leagues:
                potential_games.extend(scores_by_league.get(tl, []))
            
            for game in potential_games:
                t1_name = game.get('team1', '')
                t2_name = game.get('team2', '')
                
                t1_norm = normalize_name(t1_name)
                t2_norm = normalize_name(t2_name)
                
                t1_match = False
                t2_match = False
                
                # 1. Alias Matching
                desc_norm = normalize_text(bet_text).lower()
                for k, v in TEAM_ALIASES.items():
                    if team_in_description(desc_norm, k):
                        for alias in v:
                            an = normalize_name(alias)
                            if an and an in t1_norm: t1_match = True
                            if an and an in t2_norm: t2_match = True
                
                # 2. Direct Matching
                if not t1_match and not t2_match:
                    def strict_match(team, text):
                        return re.search(r'\b' + re.escape(team.lower()) + r'\b', text.lower())

                    if strict_match(t1_name, bet_text): t1_match = True
                    if strict_match(t2_name, bet_text): t2_match = True

                if t1_match or t2_match:
                    matched_game = game
                    break
            
            if matched_game:
                result = interpret_bet_result(
                    bet_text,
                    matched_game['team1'],
                    matched_game['team2'],
                    matched_game['score1'],
                    matched_game['score2'],
                    sport
                )
                pick_obj['result'] = result
                pick_obj['score_summary'] = f"{matched_game['team1']} {matched_game['score1']} - {matched_game['score2']} {matched_game['team2']}"
            else:
                pick_obj['result'] = "Pending/Unknown"
                pick_obj['score_summary'] = ""
        
        except Exception as e:
            pick_obj['result'] = "Error"
            pick_obj['score_summary'] = str(e)
            
        graded_results.append(pick_obj)
        
    return graded_results