# File: ./ai_parser.py
import logging
import json
import re
import time
import openai
from config import OPENROUTER_API_KEY, AI_PARSER_MODEL

# --- AI Client Initialization ---
ai_client = None
if OPENROUTER_API_KEY:
    try:
        ai_client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
else:
    logging.warning("OPENROUTER_API_KEY not found. AI parsing will be disabled.")

def parse_with_ai(raw_picks: list) -> list:
    """Sends raw text to an AI model for structured parsing."""
    if not ai_client:
        logging.error("AI client not configured. Cannot parse picks.")
        return []

    # --- START OF FINAL, PRODUCTION-READY PROMPT ---
    formatting_guide = """
    ### Sports Pick Data Formatting Guide

    ### 0. CRITICAL: Channel Watermark Filtering
    **NEVER use channel watermark names as capper names.** These are NOT actual cappers:
    - "Free Cappers Picks", "FREE CAPPERS PICKS", "Free Cappers Picks | 🔮"
    - "The Capper", "Capper Picks", "Free Picks", "Daily Picks", "Best Bets"
    - "Pick Central", "Bet Tips", "Sports Picks", "Winners Only", "Pro Picks", "Capper Network"

    If the `capper_name` is one of these watermark names, extract the **actual capper name** from the first line of the raw text. If no actual capper name exists, set `capper_name` to `null`.

    ### 1. Standardized `league` Column Values
    Use one of these: `NFL`, `NCAAF`, `NBA`, `NCAAB`, `WNBA`, `MLB`, `NHL`, `EPL`, `MLS`, `UCL`, `UFC`, `PFL`, `TENNIS`, `PGA`, `F1`, `Other`. 'Other' is for parlays with multiple leagues or unknown leagues.

    ### 2. Standardized `bet_type` Column Values
    Use one of these: `Moneyline`, `Spread`, `Total`, `Player Prop`, `Team Prop`, `Game Prop`, `Period`, `Parlay`, `Teaser`, `Future`, `Unknown`.

    ### 3. Core Formatting Rules
    - **League Inference:** If the league is not explicitly mentioned, you **MUST** infer it from a well-known team name (e.g., 'Los Angeles Lakers' implies 'NBA', 'New York Yankees' implies 'MLB', 'Manchester United' implies 'EPL'). If the team is ambiguous or unknown, use 'Other'.
    - **Pick vs. Odds:** The `pick_value` describes *what* is being bet on. The odds (e.g., -110, +150) must **only** be stored in the `odds_american` column.
    - **Number Formatting:** Omit trailing `.0` decimals. Use `48` not `48.0`.
    - **Unknown Type Handling:** If `bet_type` is `Unknown`, `pick_value` MUST be the **ENTIRE, ORIGINAL, UNFORMATTED TEXT**.

    ### 4. `pick_value` Format by `bet_type`

    #### `Moneyline`
    *   **Format:** `Team or Competitor Name ML`
    *   **Example:** `Los Angeles Lakers ML`

    #### `Spread`
    *   **Format:** `Team Name [space] Point Spread`
    *   **Example:** `Green Bay Packers -7.5`

    #### `Total`
    *   **Format:** `Team A vs Team B Over/Under Number`
    *   **Example:** `Lakers vs Celtics Over 215.5`

    #### `Player Prop`
    *   **Format:** `Player Name: Stat Over/Under/Value`
    *   **Example:** `LeBron James: Pts Over 25.5`

    #### `Team Prop`
    *   **Format:** `Team Name: Stat Over/Under/Value`
    *   **Example:** `Dallas Cowboys: Total Points Over 27.5`

    #### `Game Prop`
    *   **Format:** `Description of Prop: Value`
    *   **Example:** `Fight to go the Distance: No`
    *   **CRITICAL RULE:** For ambiguous props like "team to score first", the `pick_value` must be the original descriptive text. Example: If raw text is "I like the Mets to score first", the `pick_value` is `I like the Mets to score first.`.

    #### `Parlay` / `Teaser`
    *   **Format:** `(Leg 1 League) Details / (Leg 2 League) Details / ...`
    *   **League Prefix:** Prefixing each leg with its league in parentheses is **mandatory**.
    *   **Example:** `(NFL) Dallas Cowboys -10.5 / (NBA) Lakers ML`
    
    #### Full Pick Object Structure
    Each pick MUST be a JSON object with these keys: `raw_pick_id` (Integer), `capper_name` (String|Null), `league` (String), `bet_type` (String), `pick_value` (String), `unit` (Number), `odds_american` (Number|Null).

    ### CRITICAL: Return ONLY a single valid JSON array `[...]`. Do not include any text, markdown, or commentary outside the JSON array.
    """
    # --- END OF PROMPT ---

    prompt = f"""
    You are an expert sports data standardization bot. Your task is to analyze raw text messages and reformat EVERY valid pick *exactly* according to the provided formatting guide. A single raw text block may contain MULTIPLE picks.

    **Formatting Guide:**
    {formatting_guide}

    Raw picks to parse:
    {json.dumps(raw_picks, indent=2)}
    """
    
    retries = 3
    delay = 5
    for attempt in range(retries):
        try:
            logging.info(f"Sending batch of {len(raw_picks)} items to AI model '{AI_PARSER_MODEL}' for parsing...")
            chat_completion = ai_client.chat.completions.create(
                model=AI_PARSER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=8192,
            )
            response_text = chat_completion.choices[0].message.content
            
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            
            if json_match:
                return json.loads(json_match.group(0))
            else:
                logging.error(f"AI did not return a valid JSON array. Response: {response_text}")
                return []

        except (openai.APIError, openai.APIConnectionError, openai.RateLimitError) as e:
            logging.warning(f"AI API call failed on attempt {attempt + 1}/{retries}. Error: {e}. Retrying in {delay}s...")
            time.sleep(delay)
        
        except Exception as e:
            logging.error(f"An unexpected error occurred during AI parsing: {e}")
            return []

    logging.error("AI call failed after all retries.")
    return []