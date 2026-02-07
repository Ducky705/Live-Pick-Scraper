
import json
import os
import re
from functools import lru_cache

# Path to the team database
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "teams_db.json")

class UniversalMatcher:
    _instance = None
    _teams_data = []
    _index = {} # Map alias -> list of leagues

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UniversalMatcher, cls).__new__(cls)
            cls._instance._load_db()
        return cls._instance

    def _load_db(self):
        """Load the team database and build an index."""
        if not os.path.exists(DB_PATH):
            print(f"Warning: Team DB not found at {DB_PATH}")
            return

        try:
            with open(DB_PATH, "r") as f:
                self._teams_data = json.load(f)
                
            # Build Index
            # Map every alias (normalized) to a set of leagues
            self._index = {}
            for entry in self._teams_data:
                league = entry.get("league")
                for name in entry.get("names", []):
                    # Normalize strict: lowercase, no punctuation
                    norm_name = self._normalize_key(name)
                    if not norm_name: continue
                    
                    if norm_name not in self._index:
                        self._index[norm_name] = set()
                    self._index[norm_name].add(league)
                    
        except Exception as e:
            print(f"Error loading Team DB: {e}")

    def _normalize_key(self, text):
        """Normalize text for index keys (lowercase, no punctuation, single spaces)."""
        if not text: return ""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def infer_league(self, pick_text: str) -> str | None:
        """
        Infer the league from the pick text by searching for team names.
        Returns the league code (e.g. "nba") or None if ambiguous/not found.
        """
        norm_text = self._normalize_key(pick_text)
        if not norm_text: return None

        tokens = norm_text.split()
        
        # storage: league -> max_match_length
        candidates = {}

        # Check N-grams (1 to 4 words)
        for n in range(4, 0, -1):
            for i in range(len(tokens) - n + 1):
                phrase = " ".join(tokens[i : i + n])
                if phrase in self._index:
                    matched_leagues = self._index[phrase]
                    weight = len(phrase) # Use character length of the match as weight
                    
                    for lg in matched_leagues:
                        if lg not in candidates:
                            candidates[lg] = 0
                        candidates[lg] = max(candidates[lg], weight)

        if not candidates:
            return None
            
        # Decision Logic
        # Sort by:
        # 1. Match Length (descending) - specific names ("Florida Panthers") beat generic ("Panthers")
        # 2. Priority Hierarchy (descending) - resolution for equal match length
        
        PRIORITY = ["nfl", "nba", "mlb", "nhl", "epl", "ucl", "ncaaf", "ncaab"]
        
        def get_priority_score(lg):
             return PRIORITY.index(lg) if lg in PRIORITY else 999

        # Sort: Primary key = Length (desc), Secondary = Priority (asc/lower index is better)
        sorted_candidates = sorted(
            candidates.items(), 
            key=lambda item: (-item[1], get_priority_score(item[0]))
        )
        
        best_league, best_score = sorted_candidates[0]
        return best_league
