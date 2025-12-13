import re
from typing import Optional
import config

LEAGUE_KEYWORDS = {
    'NFL': [
        'Lions', 'Chiefs', 'Bills', 'Eagles', '49ers', 'Ravens', 'Cowboys', 'Bengals', 
        'Dolphins', 'Browns', 'Texans', 'Jaguars', 'Steelers', 'Colts', 'Seahawks', 
        'Buccaneers', 'Packers', 'Rams', 'Falcons', 'Saints', 'Vikings', 'Bears', 
        'Raiders', 'Broncos', 'Chargers', 'Giants', 'Commanders', 'Titans', 'Cardinals', 
        'Panthers', 'Patriots', 'Jets', 'Niners', 'Bucs', 'Pats', 'Commies', 'G-Men'
    ],
    'NBA': [
        'Celtics', 'Nuggets', 'Bucks', 'Timberwolves', 'Thunder', 'Clippers', 'Suns', 
        'Knicks', 'Cavaliers', 'Magic', 'Sixers', '76ers', 'Pacers', 'Heat', 'Kings', 
        'Mavericks', 'Lakers', 'Warriors', 'Pelicans', 'Rockets', 'Grizzlies', 'Hawks', 
        'Nets', 'Jazz', 'Bulls', 'Raptors', 'Hornets', 'Wizards', 'Pistons', 'Spurs', 
        'Trail Blazers', 'Blazers', 'Cavs', 'Mavs', 'Wolves', 'T-Wolves'
    ],
    'NHL': [
        'Bruins', 'Rangers', 'Stars', 'Canucks', 'Panthers', 'Avalanche', 'Jets', 
        'Oilers', 'Hurricanes', 'Maple Leafs', 'Leafs', 'Golden Knights', 'Knights', 
        'Predators', 'Preds', 'Kings', 'Lightning', 'Bolts', 'Red Wings', 'Wings', 
        'Blues', 'Flyers', 'Capitals', 'Caps', 'Islanders', 'Isles', 'Devils', 
        'Flames', 'Kraken', 'Penguins', 'Pens', 'Wild', 'Sabres', 'Senators', 'Sens', 
        'Coyotes', 'Utah HC', 'Utah Mammoth', 'Canadiens', 'Habs', 'Blackhawks', 
        'Hawks', 'Ducks', 'Blue Jackets', 'Jackets', 'Sharks'
    ],
    'MLB': [
        'Yankees', 'Dodgers', 'Orioles', 'Phillies', 'Braves', 'Guardians', 'Brewers', 
        'Padres', 'Royals', 'Twins', 'Astros', 'Mariners', 'Diamondbacks', 'D-Backs', 
        'Mets', 'Rays', 'Red Sox', 'Tigers', 'Cubs', 'Giants', 'Reds', 'Cardinals', 
        'Blue Jays', 'Jays', 'Pirates', 'Nationals', 'Nats', 'Angels', 'Rangers', 
        'Marlins', 'Rockies', 'Athletics', "A's", 'White Sox', 'Guardians'
    ],
    'NCAAF': [
        'Alabama', 'Bama', 'Crimson Tide', 'Georgia', 'Bulldogs', 'Texas', 'Longhorns', 
        'Oklahoma', 'Sooners', 'LSU', 'Tigers', 'Ole Miss', 'Rebels', 'Missouri', 'Mizzou', 
        'Tennessee', 'Vols', 'Volunteers', 'Kentucky', 'Wildcats', 'Florida', 'Gators', 
        'Auburn', 'Texas A&M', 'Aggies', 'South Carolina', 'Gamecocks', 'Arkansas', 
        'Razorbacks', 'Mississippi State', 'Bulldogs', 'Vanderbilt', 'Commodores',
        'Ohio State', 'Buckeyes', 'Michigan', 'Wolverines', 'Penn State', 'Nittany Lions', 
        'Oregon', 'Ducks', 'USC', 'Trojans', 'Washington', 'Huskies', 'UCLA', 'Bruins', 
        'Nebraska', 'Cornhuskers', 'Wisconsin', 'Badgers', 'Iowa', 'Hawkeyes', 
        'Michigan State', 'Spartans', 'Minnesota', 'Gophers', 'Illinois', 'Illini', 
        'Purdue', 'Boilermakers', 'Northwestern', 'Wildcats', 'Maryland', 'Terps', 
        'Rutgers', 'Scarlet Knights', 'Indiana', 'Hoosiers'
    ]
}

def standardize_league(val: str) -> str:
    if not val: return 'Other'
    val = val.upper().strip()
    if val in config.LEAGUE_MAP: return config.LEAGUE_MAP[val]
    
    aliases = {
        'NCAA FOOTBALL': 'NCAAF', 'CFB': 'NCAAF', 'COLLEGE FOOTBALL': 'NCAAF',
        'NCAA BASKETBALL': 'NCAAB', 'CBB': 'NCAAB', 'COLLEGE BASKETBALL': 'NCAAB', 
        'COLLEGE HOOPS': 'NCAAB', 'NCAAM': 'NCAAB', 'CBK': 'NCAAB',
        'PREMIER LEAGUE': 'EPL', 'CHAMPIONS LEAGUE': 'UCL', 'LA LIGA': 'UCL', 
        'BUNDESLIGA': 'UCL', 'SERIE A': 'UCL', 'LIGUE 1': 'UCL', 'EURO SOCCER': 'UCL',
        'MMA': 'UFC', 'FIGHTING': 'UFC', 'BOXING': 'UFC',
        'KBO': 'MLB', 'NPB': 'MLB',
        'FORMULA 1': 'F1', 'FORMULA ONE': 'F1',
        'GOLF': 'PGA', 'PGA TOUR': 'PGA',
        'TENNIS': 'TENNIS', 'ATP': 'TENNIS', 'WTA': 'TENNIS'
    }
    
    for alias, standard in aliases.items():
        if alias in val:
            return standard
            
    return 'Other'

def standardize_bet_type(val: str) -> str:
    if not val: return 'Unknown'
    val = val.upper().strip()
    mapping = {
        'MONEYLINE': 'Moneyline', 'ML': 'Moneyline', 'M/L': 'Moneyline', 'WIN': 'Moneyline',
        'SPREAD': 'Spread', 'POINT SPREAD': 'Spread', 'RUN LINE': 'Spread', 
        'PUCK LINE': 'Spread', 'ATS': 'Spread', 'HANDICAP': 'Spread',
        'TOTAL': 'Total', 'OVER/UNDER': 'Total', 'O/U': 'Total',
        'PLAYER PROP': 'Player Prop', 'PROP': 'Player Prop', 'PRA': 'Player Prop',
        'TEAM PROP': 'Team Prop', 'GAME PROP': 'Game Prop', 
        'TT': 'Team Prop', 'TTU': 'Team Prop', 'TTO': 'Team Prop',
        'PARLAY': 'Parlay', 'TEASER': 'Teaser', 'SGP': 'Parlay',
        'FUTURE': 'Future', 'TO WIN': 'Future', 'OUTRIGHT': 'Future',
        'PERIOD': 'Period', 'QUARTER': 'Period', 'HALF': 'Period', 
        '1H': 'Period', '1Q': 'Period', '2H': 'Period', '2Q': 'Period',
        'YRFI': 'Game Prop', 'NRFI': 'Game Prop',
        'ANYTIME TD': 'Player Prop', 'ATD': 'Player Prop'
    }
    for k, v in mapping.items():
        if k in val: return v
    return 'Unknown'

def _smart_title_case(text: str) -> str:
    if not text: return ""
    text = text.title()
    
    # 1. Canonical Team Mapping
    team_map = {
        r'\bBama\b': 'Alabama', r'\bUga\b': 'Georgia', r'\bMiss St\b': 'Mississippi State',
        r'\bMich St\b': 'Michigan State', r'\bOh St\b': 'Ohio State', r'\bOsu\b': 'Ohio State',
        r'\bLsu\b': 'LSU', r'\bUsc\b': 'USC', r'\bTcu\b': 'TCU', r'\bSmu\b': 'SMU',
        r'\bUcla\b': 'UCLA', r'\bUnlv\b': 'UNLV', r'\bByu\b': 'BYU', r'\bUcf\b': 'UCF',
        r'\bFsu\b': 'Florida State', r'\bUnc\b': 'North Carolina', r'\bUva\b': 'Virginia',
        r'\bVtech\b': 'Virginia Tech', r'\bGtech\b': 'Georgia Tech',
        r'\bNiners\b': '49ers', r'\bPhilly\b': 'Philadelphia', r'\bPats\b': 'Patriots',
        r'\bBucs\b': 'Buccaneers', r'\bJags\b': 'Jaguars', r'\bCommies\b': 'Commanders',
        r'\bMavs\b': 'Mavericks', r'\bCavs\b': 'Cavaliers', r'\bWolves\b': 'Timberwolves',
        r'\bT-Wolves\b': 'Timberwolves', r'\bBlazers\b': 'Trail Blazers',
        r'\bHabs\b': 'Canadiens', r'\bSens\b': 'Senators', r'\bCaps\b': 'Capitals',
        r'\bKnights\b': 'Golden Knights', r'\bJackets\b': 'Blue Jackets', r'\bPreds\b': 'Predators',
        r'\bD-Backs\b': 'Diamondbacks', r'\bJays\b': 'Blue Jays', r'\bNats\b': 'Nationals'
    }
    
    for pattern, replacement in team_map.items():
        text = re.sub(pattern, replacement, text, flags=re.I)

    # 2. General Acronym Fixes
    replacements = {
        r'\bMl\b': 'ML', r'\bNfl\b': 'NFL', r'\bNba\b': 'NBA', r'\bMlb\b': 'MLB',
        r'\bNhl\b': 'NHL', r'\bNcaaf\b': 'NCAAF', r'\bNcaab\b': 'NCAAB',
        r'\bUfc\b': 'UFC', r'\bWnba\b': 'WNBA', r'\bMls\b': 'MLS',
        r'\bPra\b': 'PRA', r'\bSog\b': 'SOG', r'\bTtu\b': 'TTU', r'\bTto\b': 'TTO',
        r'\bAtt\b': 'ATT', r'\bYds\b': 'Yds', r'\bTds\b': 'TDs', r' Td\b': 'TD',
        r'\bYrfi\b': 'YRFI', r'\bNrfi\b': 'NRFI', r'\bSgp\b': 'SGP',
        r'\bAtd\b': 'Anytime TD', r'\bAnytime Td\b': 'Anytime TD',
        r'\b1H\b': '1H', r'\b2H\b': '2H', r'\b1Q\b': '1Q', r'\bOt\b': 'OT',
        r'\bVs\b': 'vs'
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    
    return text.strip()

def format_pick_value(pick: str, bet_type: str, league: str) -> str:
    if not pick: return "Unknown Pick"
    pick = pick.strip()
    pick = _smart_title_case(pick)
    
    if bet_type == 'Unknown': return pick

    if bet_type == 'Moneyline':
        clean = re.sub(r'\bML\b|\bMoneyline\b', '', pick, flags=re.I).strip()
        return f"{clean} ML"

    if bet_type == 'Spread':
        match = re.search(r'(.+?)\s*([-+]\d+(\.\d+)?)', pick)
        if match:
            team = match.group(1).strip()
            spread = match.group(2).strip()
            return f"{team} {spread}"
        return pick

    if bet_type == 'Total':
        pick = re.sub(r'\b(O|Over)\s*(\d)', r'Over \2', pick, flags=re.I)
        pick = re.sub(r'\b(U|Under)\s*(\d)', r'Under \2', pick, flags=re.I)
        return pick

    if bet_type == 'Player Prop':
        if "Anytime TD" in pick or "ATD" in pick:
            clean = re.sub(r'\b(Anytime TD|ATD)\b', '', pick, flags=re.I).strip()
            return f"{clean} Anytime TD"
            
        if ':' not in pick:
            parts = pick.split()
            if len(parts) > 2:
                return f"{parts[0]} {parts[1]}: {' '.join(parts[2:])}"
        return pick

    return pick

def infer_league(pick_text: str) -> str:
    if not pick_text: return 'Other'
    for league, teams in LEAGUE_KEYWORDS.items():
        for team in teams:
            if re.search(r'\b' + re.escape(team) + r'\b', pick_text, re.IGNORECASE):
                return league
    return 'Other'
