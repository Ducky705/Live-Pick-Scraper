import json
import logging
from typing import Tuple

from src.provider_pool import pooled_completion

class ValidityFilter:
    """
    Filters out 'nonsense' or invalid picks using LLM validation.
    """

    def __init__(self, model: str = "auto"):
        self.model = model

    def is_valid(self, pick_text: str, league: str = "Unknown") -> Tuple[bool, str]:
        """
        Determines if a pick text is valid and contains enough information to be graded.
        """
        # Fast heuristic checks first
        if not pick_text or len(pick_text.strip()) < 3:
            return False, "Text too short"
        
        # If it's just a number or very short common garbage
        if pick_text.replace(".", "").replace("-", "").isdigit():
             return False, "Numeric only"

        # Heuristic: Rejects obvious non-picks (Marketing, URLs, noise)
        lower_text = pick_text.lower()
        garbage_phrases = ["vip", "subscribe", "link in bio", "dm for", "promo", "discount", "package", "guaranteed", "bankroll"]
        if any(g in lower_text for g in garbage_phrases):
             return False, "Marketing/Garbage detected"
             
        # Heuristic: Must contain at least one digit OR a betting keyword
        # Valid picks: "Lakers -5", "Over 210", "Lakers ML"
        # Invalid: "Lakers", "Austin", "Analysis below"
        betting_keywords = ["over", "under", "ml", "moneyline", "spread", "pts", "reb", "ast", "win", "u", "unit"]
        has_digit = any(c.isdigit() for c in pick_text)
        has_keyword = any(k in lower_text for k in betting_keywords)
        
        
        # NFL/NHL/MLB/Soccer common aliases could be added here
        # For now, we trust the LLM if it's not a digit pick but looks like a team.
        
        known_teams = ["bucks", "lakers", "warriors", "heat", "celtics", "nuggets", "suns", "clippers", "mavericks", "kings", "thunder", "wolves", "timberwolves", "knicks", "nets", "sixers", "76ers", "pacers", "bulls", "pistons", "magic", "hornets", "wizards", "hawks", "spurs", "rockets", "grizzlies", "pelicans", "jazz", "blazers", "trail blazers", "raptors",
                       "chiefs", "49ers", "ravens", "lions", "bills", "packers", "cowboys", "eagles", "dolphins", "browns", "texans", "steelers", "bengals", "jaguars", "colts", "titans", "broncos", "raiders", "chargers", "giants", "commanders", "bears", "vikings", "falcons", "saints", "buccaneers", "panthers", "cardinals", "rams", "seahawks", "jets", "patriots",
                       "canadiens", "maple leafs", "leafs", "senators", "bruins", "sabres", "wings", "red wings", "panthers", "lightning", "hurricanes", "capitals", "devils", "islanders", "rangers", "flyers", "penguins", "jackets", "blue jackets", "avalanche", "stars", "wild", "predators", "blues", "coyotes", "ducks", "flames", "oilers", "kings", "sharks", "kraken", "canucks", "knights", "golden knights",
                       "yankees", "red sox", "orioles", "rays", "jays", "blue jays", "guardians", "tigers", "twins", "royals", "white sox", "mariners", "angels", "astros", "athletics", "rangers", "braves", "marlins", "mets", "phillies", "nationals", "cubs", "reds", "brewers", "pirates", "cardinals", "diamondbacks", "rockies", "dodgers", "padres", "giants"]

        # RELAXED HEURISTIC:
        # If no digits/keywords, BUT it is a known team name, allow it.
        is_known_team = lower_text in known_teams or lower_text.split(" ")[0] in known_teams
        
        if not has_digit and not has_keyword and not is_known_team:
             # Final check: Is it roughly 1-3 words and not garbage?
             # Might be a team we missed. 
             # Let's be strict on "no digits/keywords" UNLESS it's a known team or specifically whitelisted.
             # User specifically mentioned "Bucks".
             return False, "No betting structure (digits/keywords) found and not a known team alias"

        # Construct Prompt
        prompt = f"""
You are a Sports Betting Validator. Your job is to determine if the following text is a VALID betting pick that contains enough information to be graded (Team/Player AND Bet Type/Spread/Total).

Text: "{pick_text}"
Context League: {league}

Rules:
1. REJECT generic fragments like "Over 6.5", "-7.5", "Team ML", "Player Prop" if no specific team/player is named.
2. REJECT garbage strings, marketing fluff, or non-pick text.
3. ACCEPT valid picks even if they use nicknames (e.g., "Lakers -5", "LeBron O 25.5").
4. ACCEPT if it refers to a specific game context implied (e.g. "Over 215" might be invalid without teams, but "Lakers/Suns Over 215" is valid).
5. ACCEPT "Lakers vs Celtics Over 215.5" (Standard Format).
6. ACCEPT single team names (e.g. "Bucks", "Lakers", "Kansas City") as IMPLIED MONEYLINE bets. This is a common shorthand.

Respond in JSON format:
{{
    "is_valid": true/false,
    "reason": "Brief explanation"
}}
"""
        
        try:
            # Use Hybrid Pool for robustness
            response = pooled_completion(prompt, timeout=10)
            if not response:
                # Fail open but log warning
                logger.warning(f"ValidityFilter API failed for: {pick_text}")
                return True, "Validator API Error"
            
            data = json.loads(response)
            return data.get("is_valid", True), data.get("reason", "No reason provided")
            
            data = json.loads(response)
            return data.get("is_valid", True), data.get("reason", "No reason provided")

        except Exception as e:
            logger.error(f"Validity filter error: {e}")
            return True, f"Error: {e}"

