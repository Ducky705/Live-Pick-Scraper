
import json
import logging
from typing import Any

from dotenv import load_dotenv

from src.groq_client import groq_text_completion
from src.openrouter_client import openrouter_completion
from src.cerebras_client import cerebras_completion
from src.mistral_client import mistral_completion
from src.gemini_client import gemini_text_completion

from src.grading.schema import Pick, BetType
from datetime import datetime

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
        
        # TIER 1: ACCURACY CHAMPION (OpenRouter - stepfun)
        # ---------------------------------------------------------
        try:
            response = openrouter_completion(prompt, timeout=15)
            if response:
                return AIResolver._parse_response(response, pick_text, candidate_games, "OpenRouter")
        except Exception as e:
            logger.warning(f"[Tier 1] OpenRouter failed: {e}")

        # TIER 2: FAST BACKUPS (Mistral -> Cerebras)
        # ---------------------------------------------------------
        try:
             # Mistral (open-mistral-nemo)
             response = mistral_completion(prompt, model="open-mistral-nemo", timeout=15)
             if response:
                 return AIResolver._parse_response(response, pick_text, candidate_games, "Mistral")
        except Exception as e:
            logger.warning(f"[Tier 2] Mistral failed: {e}")

        try:
            # Cerebras (Llama 3.1 8b)
            response = cerebras_completion(prompt, model="llama3.1-8b", timeout=10)
            if response:
                return AIResolver._parse_response(response, pick_text, candidate_games, "Cerebras")
        except Exception as e:
            logger.warning(f"[Tier 2] Cerebras failed: {e}")

        # TIER 3: SAFETY NET (Gemini - if available)
        # ---------------------------------------------------------
        try:
            # Gemini (Flash 1.5 - Free Tier)
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
            if not data:
                return None
            
            game_id = data.get("game_id")
            resolved_team = data.get("team")
            
            if game_id:
                for g in games:
                    if str(g.get("id")) == str(game_id):
                        return g, resolved_team
            return None
        except Exception as e:
            logger.warning(f"Failed to parse response from {provider_name}: {e}")
            return None

    @staticmethod
    def resolve_batch(items: list[tuple[str, str]], games: list[dict[str, Any]]) -> dict[tuple[str, str], tuple[dict, str] | None]:
        """
        Resolve multiple picks in a single prompt to save time and API calls.
        
        Args:
            items: List of (pick_text, league) tuples
            games: List of candidate games
        Returns:
            Dictionary mapping original (pick_text, league) keys to their resolved (game, team_name) tuple or None
        """
        if not games or not items:
            return {item: None for item in items}
            
        results = {}
        # Collect candidate games.
        # It's better to show all games from the requested leagues.
        leagues_requested = {l.lower() for _, l in items if l}
        candidate_games = []
        for g in games:
            lg = str(g.get("league", "")).lower()
            if not leagues_requested or lg in leagues_requested:
                candidate_games.append(g)

        if not candidate_games:
            candidate_games = games
            
        candidate_games = candidate_games[:100] # Limit tokens

        game_list_str = "\n".join([
            f"- ID: {g.get('id')} | {g.get('team1')} vs {g.get('team2')} ({g.get('league')})"
            for g in candidate_games
        ])

        items_str = "\n".join([f"{i+1}. PICK: '{txt}' (League: {lg})" for i, (txt, lg) in enumerate(items)])

        prompt = f"""
You are a sports betting expert. Match the following list of picks to one of the games listed below.

AVAILABLE GAMES:
{game_list_str}

UNRESOLVED PICKS:
{items_str}

INSTRUCTIONS:
1. Try to match each pick to a game. Account for typos, nicknames, and aliases.
2. If it clearly matches, provide the mapped Game ID and the resolved Standard Team Name.
3. If no clear match exists, provide null.

OUTPUT FORMAT:
Return a JSON array of objects, EXACTLY ONE for each input pick, IN THE EXACT SAME ORDER.
[
    {{ "game_id": "string_id_from_list", "team": "Standard Team Name" }},
    {{ "game_id": null, "team": null }}
]
"""
        
        try:
            response = openrouter_completion(prompt, timeout=30)
            if response:
                text = response.replace("```json", "").replace("```", "").strip()
                # find the first '[' to avoid leading conversational text
                start_idx = text.find('[')
                end_idx = text.rfind(']') + 1
                if start_idx != -1 and end_idx != -1:
                    text = text[start_idx:end_idx]
                
                data = json.loads(text)
                
                if isinstance(data, list):
                    for i, (pick_text, league) in enumerate(items):
                        if i >= len(data): break
                        mapping = data[i]
                        game_id = mapping.get("game_id")
                        resolved_team = mapping.get("team")
                        
                        found_game = None
                        if game_id:
                            for g in candidate_games:
                                if str(g.get("id")) == str(game_id):
                                    found_game = g
                                    break
                                    
                        if found_game and resolved_team:
                            results[(pick_text, league)] = (found_game, resolved_team)
                        else:
                            results[(pick_text, league)] = None
                return {item: results.get(item) for item in items}
        except Exception as e:
            logger.warning(f"Batch AI Resolve failed: {e}")

        return {item: None for item in items}


    @staticmethod
    def parse_pick(pick_text: str, league: str) -> Pick | None:
        """
        Parse a complex or natural language pick using AI.
        Fallback for when regex parser fails or returns ambiguous results.
        """
        prompt = f"""
You are a sports betting parser. Extract structured betting information from the text.

TEXT: "{pick_text}"
LEAGUE CONTEXT: "{league}"

INSTRUCTIONS:
1. Identify the Bet Type (Moneyline, Spread, Total, Player Prop, Parlay, etc.).
2. If the text contains multiple distinct bets (e.g. "TeamA -5 TeamB ML"), identify it as a PARLAY.
3. Extract the Selection (Team Name, Player Name).
4. Extract the Line/Odds if present.
5. For Player Props, extract the Subject (Player) and Stat (e.g., 'pts', 'reb').
6. For Totals/Props, ensure 'is_over' is correctly identified (true/false).

EXAMPLES:
Text: "Knicks -5 Nets ML"
Output: {{ "bet_type": "Parlay", "legs": [{{ "bet_type": "Spread", "selection": "Knicks", "line": -5 }}, {{ "bet_type": "Moneyline", "selection": "Nets" }}] }}

Text: "I want the Chiefs to win"
Output: {{ "bet_type": "Moneyline", "selection": "Chiefs", "line": null }}

Text: "Packers -7"
Output: {{ "bet_type": "Spread", "selection": "Packers", "line": -7.0 }}

Text: "I want the Chiefs covering the spread"
Output: {{ "bet_type": "Spread", "selection": "Chiefs", "line": null }}

Text: "Bills -3 Chiefs Over 48"
Output: {{ "bet_type": "Parlay", "legs": [{{ "bet_type": "Spread", "selection": "Bills", "line": -3 }}, {{ "bet_type": "Total", "selection": "Chiefs", "line": 48, "is_over": true }}] }}

Text: "Davis 25+ points"
Output: {{ "bet_type": "Player Prop", "selection": "Davis", "line": 24.5, "stat": "pts", "is_over": true }}

OUTPUT FORMAT (JSON):
{{
    "bet_type": "Moneyline" | "Spread" | "Total" | "Player Prop" | "Parlay" | "Unknown",
    "selection": "Team/Player Name",
    "line": float or null,
    "odds": int or null,
    "subject": "Player Name (for props)",
    "stat": "Stat Key (points, rebounds, etc.)",
    "is_over": true/false/null,
    "legs": [ ...recursive pick objects for parlays... ]
}}
"""
        # TIER 1: OpenRouter
        try:
            response = openrouter_completion(prompt, timeout=15)
            if response:
                return AIResolver._parse_extraction_response(response, pick_text, league)
        except Exception as e:
            logger.warning(f"AI Parsing (OpenRouter) failed: {e}")

        # TIER 2: Mistral
        try:
            response = mistral_completion(prompt, model="open-mistral-nemo", timeout=15)
            if response:
                return AIResolver._parse_extraction_response(response, pick_text, league)
        except Exception as e:
            logger.warning(f"AI Parsing (Mistral) failed: {e}")

        # TIER 3: Cerebras
        try:
            # Cerebras (Llama 3.1 8b - Fast & Reliable)
            # 70b is giving 404, so using 8b with enhanced prompting
            response = cerebras_completion(prompt, model="llama3.1-8b", timeout=15)
            if response:
                return AIResolver._parse_extraction_response(response, pick_text, league)
        except Exception as e:
            logger.warning(f"AI Parsing (Cerebras 8b) failed: {e}")
            
        return None

    @staticmethod
    def _parse_extraction_response(response_text: str, original_text: str, league: str) -> Pick | None:
        """Parse JSON response into Pick object."""
        try:
            # Clean md blocks
            text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            
            b_type_str = data.get("bet_type", "Unknown").upper().replace(" ", "_")
            try:
                bet_type = BetType[b_type_str]
            except KeyError:
                bet_type = BetType.UNKNOWN

            # Recursive parsing for parlays
            legs = []
            if data.get("legs"):
                for leg_data in data["legs"]:
                    # Minimal reconstruction for legs
                    l_type = BetType.UNKNOWN
                    try:
                        l_type = BetType[leg_data.get("bet_type", "").upper().replace(" ", "_")]
                    except: pass
                    
                    legs.append(Pick(
                        raw_text=leg_data.get("selection", ""),
                        league=league,
                        bet_type=l_type,
                        selection=leg_data.get("selection", ""),
                        line=leg_data.get("line"),
                        is_over=leg_data.get("is_over"),
                        subject=leg_data.get("subject"),
                        stat=leg_data.get("stat"),
                    ))

            return Pick(
                raw_text=original_text,
                league=league,
                bet_type=bet_type,
                selection=data.get("selection", ""),
                line=data.get("line"),
                odds=data.get("odds"),
                subject=data.get("subject"),
                stat=data.get("stat"),
                is_over=data.get("is_over"),
                legs=legs
            )
        except Exception as e:
            logger.warning(f"Failed to parse AI extraction JSON: {e}")
            return None

