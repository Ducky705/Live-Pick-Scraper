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

