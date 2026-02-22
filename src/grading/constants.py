# src/grading/constants.py
"""
Constants and mappings for the grading system.
"""

# =============================================================================
# LEAGUE MAPPINGS
# =============================================================================

# Maps internal league codes to ESPN API (Sport, League) tuples
ESPN_LEAGUE_MAP = {
    # Basketball
    "nba": ("basketball", "nba"),
    "wnba": ("basketball", "wnba"),
    "ncaab": ("basketball", "mens-college-basketball"),
    "wncaab": ("basketball", "womens-college-basketball"),
    # Football
    "nfl": ("football", "nfl"),
    "ncaaf": ("football", "college-football"),
    # Hockey
    "nhl": ("hockey", "nhl"),
    # Baseball
    "mlb": ("baseball", "mlb"),
    # Soccer
    "epl": ("soccer", "eng.1"),
    "mls": ("soccer", "usa.1"),
    "ucl": ("soccer", "uefa.champions"),
    "championship": ("soccer", "eng.2"),
    "laliga": ("soccer", "esp.1"),
    "bundesliga": ("soccer", "ger.1"),
    "seriea": ("soccer", "ita.1"),
    "ligue1": ("soccer", "fra.1"),
    "nwsl": ("soccer", "usa.nwsl"),
    "liga_mx": ("soccer", "mex.1"),
    "eredivisie": ("soccer", "ned.1"),
    # MMA/Combat
    "ufc": ("mma", "ufc"),
    "pfl": ("mma", "pfl"),
    "boxing": ("boxing", "boxing"),
    # Tennis
    "tennis": ("tennis", "atp"),
    "atp": ("tennis", "atp"),
    "wta": ("tennis", "wta"),
    # Racing
    "f1": ("racing", "f1"),
    "nascar": ("racing", "nascar-premier"),
    "indycar": ("racing", "irl"),
    # Golf
    "pga": ("golf", "pga"),
    "lpga": ("golf", "lpga"),
    # Lacrosse
    "pll": ("lacrosse", "pll"),
    # Other
    "rugby": ("rugby", "rugby-union"),
    "cricket": ("cricket", "cricket"),
}

# Synonyms for league normalization (includes identity mappings)
LEAGUE_ALIASES_MAP = {
    # Identity mappings (standard leagues)
    "nba": "nba",
    "nfl": "nfl",
    "nhl": "nhl",
    "mlb": "mlb",
    "ncaab": "ncaab",
    "ncaaf": "ncaaf",
    "wnba": "wnba",
    "wncaab": "wncaab",
    "epl": "epl",
    "mls": "mls",
    "ucl": "ucl",
    "ufc": "ufc",
    "atp": "atp",
    "wta": "wta",
    "pga": "pga",
    # Aliases
    "cfb": "ncaaf",
    "mcb": "ncaab",
    "cbb": "ncaab",
    "college football": "ncaaf",
    "college basketball": "ncaab",
    "mens college basketball": "ncaab",
    "premier league": "epl",
    "champions league": "ucl",
    "la liga": "laliga",
    "serie a": "seriea",
    "tennis": "atp",
    "other": "other",
    # New Sports
    "rugby": "rugby",
    "cricket": "cricket",
    "boxing": "boxing",
    "liga mx": "liga_mx",
    "eredivisie": "eredivisie",
    # Combat Sports
    "mma": "ufc",
    "mixed martial arts": "ufc",
    "bellator": "ufc",  # Group under UFC for grading unless PFL specific
    "pfl": "ufc",       # Group under UFC for grader simplicity (or keep separate if needed)
}

# Soccer leagues (for 3-way ML handling)
SOCCER_LEAGUES = {"epl", "mls", "ucl", "championship", "laliga", "bundesliga", "seriea", "ligue1", "nwsl", "liga_mx", "eredivisie"}

# Individual sports (use athlete names, not team names)
INDIVIDUAL_SPORTS = {"ufc", "pfl", "atp", "wta", "tennis", "pga", "lpga", "f1", "nascar", "indycar", "boxing"}

# =============================================================================
# STAT MAPPINGS (Pick Format -> ESPN JSON Key)
# =============================================================================

# Map the "Stat" string from picks to possible ESPN JSON keys (lowercase for matching)
STAT_KEY_MAP = {
    # BASKETBALL
    "pts": ["points", "pts", "p"],
    "reb": ["rebounds", "reb", "totalrebounds", "totreb"],
    "ast": ["assists", "ast", "a"],
    "blk": ["blocks", "blk"],
    "stl": ["steals", "stl"],
    "to": ["turnovers", "to"],
    "3pm": ["threepointfieldgoalsmade", "3pm", "fg3m", "threepointersmade", "threes", "3s"],
    "pra": ["pts+reb+ast", "pra"],  # Calculated
    "pts+reb+ast": ["pts+reb+ast", "pra"],  # Calculated
    # FOOTBALL
    "passyds": ["passingyards", "passyds", "passyards"],
    "rushyds": ["rushingyards", "rushyds", "rushyards"],
    "recyds": ["receivingyards", "recyds", "recyards"],
    "passtd": ["passingtouchdowns", "passtd", "passtds", "passingtds"],
    "rushtd": ["rushingtouchdowns", "rushtd", "rushtds", "rushingtds", "td", "tds", "touchdown", "touchdowns"],
    "rectd": ["receivingtouchdowns", "rectd", "rectds", "receivingtds"],
    "rec": ["receptions", "rec"],
    "comp": ["completions", "comp", "passingcompletions"],
    "int": ["interceptions", "int", "passinginterceptions"],
    "att": ["attempts", "att", "rushingcarries", "carries"],
    # BASEBALL
    "k": ["strikeouts", "k", "pitchingstrikeouts", "batterstrikeouts", "ks"],
    "h": ["hits", "h"],
    "hr": ["homeruns", "hr"],
    "rbi": ["runsbattedin", "rbi"],
    "r": ["runs", "r"],
    "tb": ["totalbases", "tb", "bases"],
    "totalbases": ["totalbases", "tb", "bases"],
    "bb": ["walks", "bb", "baseonballs"],
    "sb": ["stolenbases", "sb"],
    # HOCKEY
    "g": ["goals", "g", "goal", "score", "scorer", "anytimegoalscorer", "ags"],
    "a": ["assists", "a"],
    "sog": ["shotsongoal", "shots", "sog"],
    "p": ["points", "p"],
    "saves": ["saves", "sv"],
    "pim": ["penaltyminutes", "pim"],
}

# =============================================================================
# PERIOD IDENTIFIERS
# =============================================================================

PERIOD_PATTERNS = {
    "1h": "1H",
    "2h": "2H",
    "1q": "1Q",
    "2q": "2Q",
    "3q": "3Q",
    "4q": "4Q",
    "1p": "1P",
    "2p": "2P",
    "3p": "3P",
    "f5": "F5",
    "f3": "F3",
    "f1": "F1",
    "first half": "1H",
    "second half": "2H",
    "1st half": "1H",
    "2nd half": "2H",
    "first quarter": "1Q",
    "first 5": "F5",
    "first 5 innings": "F5",
    "first 3": "F3",
    "first inning": "F1",
}
