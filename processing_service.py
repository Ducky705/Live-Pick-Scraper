import os
import logging
import json
import re
from dotenv import load_dotenv
from supabase import create_client, Client
import openai

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# *** FIX: AI model is now fully configurable via environment variable ***
AI_PARSER_MODEL = os.getenv("AI_PARSER_MODEL", "google/gemini-2.0-flash-exp:free")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    ai_client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
except Exception as e:
    logging.error(f"Initialization failed: {e}")
    supabase = None
    ai_client = None

def get_or_create_capper(capper_name: str) -> int:
    try:
        normalized_name = ' '.join(capper_name.strip().split()).title()
        res = supabase.table('capper_directory').select('id').eq('canonical_name', normalized_name).limit(1).execute()
        if res.data:
            return res.data[0]['id']
        else:
            logging.info(f"Creating new capper in directory: {normalized_name}")
            res = supabase.table('capper_directory').insert({'canonical_name': normalized_name}).execute()
            return res.data[0]['id']
    except Exception as e:
        logging.error(f"Error getting/creating capper '{capper_name}': {e}")
        return None

def clean_unit_value(unit_input: any) -> float:
    default_unit = 1.0
    if isinstance(unit_input, (int, float)):
        return float(unit_input)
    
    if not isinstance(unit_input, str) or not unit_input:
        return default_unit

    match = re.search(r'(\d+\.?\d*)', unit_input.strip())
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return default_unit
    
    return default_unit

def parse_with_ai(raw_picks: list) -> list:
    if not ai_client:
        logging.error("AI client not configured. Cannot parse picks.")
        return []

    prompt = f"""
    You are an expert sports data standardization bot. Your task is to analyze raw text messages and reformat EVERY valid pick *exactly* according to the provided formatting guide. A single raw text block may contain MULTIPLE picks.
    
    --- FORMATTING GUIDE ---
    1. Standard `league` values: NFL, NCAAF, NBA, NCAAB, WNBA, MLB, NHL, EPL, MLS, UCL, UFC, PFL, TENNIS, PGA, F1. For multi-league parlays, use "Other". If unknown, also use "Other".
    2. Standard `type` values: Moneyline, Spread, Total, Player Prop, Team Prop, Game Prop, Period, Parlay, Teaser, Future, Unknown.
    3. `pick_value` format depends on `type`.
       - Moneyline: `Team Name ML`
       - Spread: `Team Name +/-Line`
       - Total: `Team A vs Team B Over/Under Line`
       - Parlay/Teaser: Each leg MUST be prefixed with its league, e.g., `(NFL) Dallas Cowboys -10.5 / (NBA) Lakers ML`. If a parlay contains multiple leagues, set the main `league` field to "Other".
    
    CRITICAL INSTRUCTIONS:
    - Your response MUST be a single valid JSON array of objects. Do not include any other text.
    - Each object in the array represents ONE pick.
    - Each object MUST have: "raw_pick_id", "capper_name", "league", "pick_value", "bet_type", "unit", "odds_american".
    - `capper_name` is often the first line. Apply it to all picks from the same raw_pick_id.
    - The `unit` field MUST be a JSON number (e.g., 1, 1.5), not a string (e.g., "1U"). If no unit is specified in the text, use the number 1.0 as the default.

    Raw picks to parse:
    {json.dumps(raw_picks, indent=2)}
    """
    try:
        logging.info(f"Sending batch of {len(raw_picks)} items to AI model '{AI_PARSER_MODEL}' for parsing...")
        chat_completion = ai_client.chat.completions.create(
            model=AI_PARSER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4000,
        )
        response_text = chat_completion.choices[0].message.content
        
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            logging.error(f"AI did not return a valid JSON array. Response: {response_text}")
            return []
            
    except Exception as e:
        logging.error(f"Error during AI parsing: {e}")
        return []

def run_processor():
    if not supabase: return

    logging.info("Starting processing service run...")
    response = supabase.table('raw_picks').select('*').eq('status', 'pending').limit(25).execute()
    if not response.data:
        logging.info("No pending raw picks to process.")
        return

    raw_picks = response.data
    raw_picks_for_ai = [{"raw_pick_id": p['id'], "text": p['raw_text']} for p in raw_picks]
    
    parsed_picks = parse_with_ai(raw_picks_for_ai)

    if not parsed_picks:
        logging.error("AI parsing returned no data. Marking as failed to prevent retries.")
        failed_ids = [p['id'] for p in raw_picks]
        supabase.table('raw_picks').update({'status': 'failed'}).in_('id', failed_ids).execute()
        return

    picks_to_insert = []
    processed_ids = set()

    for parsed_pick in parsed_picks:
        raw_pick_id = parsed_pick.get('raw_pick_id')
        original_pick = next((p for p in raw_picks if p['id'] == raw_pick_id), None)
        if not original_pick: continue

        capper_name_from_ai = parsed_pick.get('capper_name') or original_pick.get('capper_name')
        if not capper_name_from_ai:
            logging.warning(f"No capper name found for raw_pick_id {raw_pick_id}. Skipping.")
            continue
            
        capper_id = get_or_create_capper(capper_name_from_ai)
        if capper_id:
            raw_unit_value = parsed_pick.get('unit')
            clean_unit = clean_unit_value(raw_unit_value)

            picks_to_insert.append({
                'capper_id': capper_id,
                'pick_date': original_pick['pick_date'],
                'league': parsed_pick.get('league'),
                'pick_value': parsed_pick.get('pick_value'),
                'bet_type': parsed_pick.get('bet_type'),
                'unit': clean_unit,
                'odds_american': parsed_pick.get('odds_american'),
            })
        processed_ids.add(raw_pick_id)
        
    if picks_to_insert:
        supabase.table('live_picks').insert(picks_to_insert).execute()
        logging.info(f"Inserted {len(picks_to_insert)} new structured picks into 'live_picks'.")

    if processed_ids:
        supabase.table('raw_picks').update({'status': 'processed'}).in_('id', list(processed_ids)).execute()

    logging.info("Processing service run finished.")

if __name__ == "__main__":
    logging.info("Running processing_service.py directly for testing...")
    run_processor()