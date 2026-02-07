
import json
import logging
from typing import Any

from dotenv import load_dotenv

from src.groq_client import groq_text_completion
from src.openrouter_client import openrouter_completion
from src.cerebras_client import cerebras_completion
from src.mistral_client import mistral_completion
from src.gemini_client import gemini_text_completion

load_dotenv()

logger = logging.getLogger(__name__)

class AIResolver:
    """
    AI-powered fallback resolver for ambiguous or unmatched picks.
    Uses LLM to match a pick text to a list of available games when rule-based matching fails.
    """

    @staticmethod
    def resolve_pick(pick_text: str, league: str, games: list[dict[str, Any]]) -> tuple[dict[str, Any], str] | None:
        """
        Attempt to resolve a pick to a game using AI.
        
        Args:
            pick_text: The raw pick text (e.g., "Norte Dame +18")
            league: The target league (optional context)
            games: List of candidate games for the date
            
        Returns:
            Tuple of (game_dict, resolved_team_name), or None if unresolved.
        """
        if not games:
            return None
            
        # Filter games by league if provided (optimization)
        candidate_games = games
        if league:
            filtered = [g for g in games if g.get("league", "").lower() == league.lower()]
            if filtered:
                candidate_games = filtered
                
        # Constrain candidates to save tokens (top 50 should cover most days per league)
        candidate_games = candidate_games[:50]
        
        # Build prompt
        game_list_str = "\n".join([
            f"- ID: {g.get('id')} | {g.get('team1')} vs {g.get('team2')} ({g.get('league')})"
            for g in candidate_games
        ])
        
        prompt = f"""
You are a sports betting expert. Match the following pick to one of the games listed below.

PICK: "{pick_text}"
LEAGUE CONTEXT: "{league}"

AVAILABLE GAMES:
{game_list_str}

INSTRUCTIONS:
1. Identify which game this pick refers to.
2. Account for typos, nicknames, and aliases (e.g. "Norte Dame" -> "Notre Dame", "Cincy" -> "Cincinnati").
3. If the pick clearly matches a game, return the Game ID and the resolved Team Name.
4. If no clear match exists, return null.

OUTPUT FORMAT (JSON):
{{
    "game_id": "string_id_from_list",
    "team": "Standard Team Name",
    "reason": "explanation"
}}
        """
        
        # TIER 1: SPEED (Cerebras -> Groq)
        # ---------------------------------------------------------
        try:
            # 1. Cerebras (Llama 3.3 70b)
            # "CHAMPION" provider for concurrency
            response = cerebras_completion(prompt, model="llama-3.3-70b", timeout=10)
            if response:
                return AIResolver._parse_response(response, pick_text, candidate_games, "Cerebras")
        except Exception as e:
            logger.warning(f"[Tier 1] Cerebras failed: {e}")

        try:
            # 2. Groq (Llama 3.3 70b)
            # "FASTEST" provider
            response = groq_text_completion(prompt, timeout=10)
            if response:
                return AIResolver._parse_response(response, pick_text, candidate_games, "Groq")
        except Exception as e:
            logger.warning(f"[Tier 1] Groq failed: {e}")

        # TIER 2: QUALITY (Mistral -> OpenRouter)
        # ---------------------------------------------------------
        try:
             # 3. Mistral (Codestral/Large - Great for JSON)
             response = mistral_completion(prompt, model="mistral-large-latest", timeout=15)
             if response:
                 return AIResolver._parse_response(response, pick_text, candidate_games, "Mistral")
        except Exception as e:
            logger.warning(f"[Tier 2] Mistral failed: {e}")

        try:
            # 4. OpenRouter (DeepSeek/Llama fallback)
            response = openrouter_completion(prompt, timeout=15)
            if response:
                return AIResolver._parse_response(response, pick_text, candidate_games, "OpenRouter")
        except Exception as e:
            logger.warning(f"[Tier 2] OpenRouter failed: {e}")

        # TIER 3: SAFETY NET (Gemini)
        # ---------------------------------------------------------
        try:
            # 5. Gemini (Flash 1.5 - Free Tier)
            response = gemini_text_completion(prompt, model="gemini-1.5-flash", timeout=15)
            if response:
                return AIResolver._parse_response(response, pick_text, candidate_games, "Gemini")
        except Exception as e:
             logger.warning(f"[Tier 3] Gemini failed: {e}")

        logger.error(f"ALL AI Tiers failed for '{pick_text}'")
        return None

    @staticmethod
    def _parse_response(response_text: str, pick_text: str, games: list[dict], provider_name: str):
        """Helper to parse JSON response from any LLM."""
        try:
            data = json.loads(response_text)
            game_id = data.get("game_id")
            resolved_team = data.get("team")
            
            if game_id:
                for g in games:
                    if str(g.get("id")) == str(game_id):
                        logger.info(f"AI Resolved ({provider_name}) '{pick_text}' -> {g['team1']} vs {g['team2']} (Team: {resolved_team})")
                        return g, resolved_team
            return None
        except Exception as e:
            logger.warning(f"Failed to parse response from {provider_name}: {e}")
            return None
