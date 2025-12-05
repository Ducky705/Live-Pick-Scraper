import logging
import json
import re
from typing import List
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import OPENROUTER_API_KEY, AI_PARSER_MODEL
from models import ParsedPick, RawPick

logger = logging.getLogger(__name__)

client = None
if OPENROUTER_API_KEY:
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1", 
        api_key=OPENROUTER_API_KEY,
        default_headers={"HTTP-Referer": "http://localhost:3000"},
        max_retries=0
    )

PROMPT_TEMPLATE = """
You are a sports betting data extractor. 
Your job is to find valid picks hidden in messy Telegram messages and OCR text.

### RULES
1. **IGNORE HYPE**: Words like "Banger", "Whale", "Lock" are noise.
2. **FIND THE LINES**: Look for Team Names followed by a spread (+5, -3.5) or Moneyline.
3. **OCR IS MESSY**: "Cow boy +5" -> "Cowboys +5".
4. **IMPORTANT**: You MUST include the "raw_pick_id" from the input in your output object.

### EXAMPLES
Input: {{"raw_pick_id": 123, "text": "Lakers -5"}}
Output: [{{"raw_pick_id": 123, "pick_value": "Lakers -5", "bet_type": "Spread", "unit": null, "odds_american": null, "league": "NBA"}}]

### DATA TO PROCESS
{data_json}
"""

def _repair_json(text: str) -> str:
    text = re.sub(r'```json', '', text, flags=re.I)
    text = re.sub(r'```', '', text)
    text = text.strip()
    end = text.rfind(']')
    if end == -1: return "[]"
    starts = [m.start() for m in re.finditer(r'\[', text)]
    for start in reversed(starts):
        if start >= end: continue
        candidate = text[start:end+1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue
    return "[]"

def parse_with_ai(raw_picks: List[RawPick]) -> List[ParsedPick]:
    if not client or not raw_picks: return []

    # --- DEBUG: PRINT MODEL BEING USED ---
    print(f"🤖 AI PARSER: Using Model -> {AI_PARSER_MODEL}")
    # -------------------------------------

    input_data = []
    for p in raw_picks:
        input_data.append({"raw_pick_id": p.id, "text": p.raw_text[:1000]})
    
    try:
        completion = client.chat.completions.create(
            model=AI_PARSER_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(data_json=json.dumps(input_data))}],
            temperature=0.0
        )
        
        content = completion.choices[0].message.content
        
        clean_json = _repair_json(content)
        
        try:
            parsed_data = json.loads(clean_json)
        except json.JSONDecodeError:
            objects = re.findall(r'\{[^{}]+\}', clean_json)
            parsed_data = [json.loads(o) for o in objects]

        results = []
        for item in parsed_data:
            if 'raw_pick_id' not in item and len(raw_picks) == 1:
                item['raw_pick_id'] = raw_picks[0].id

            if 'raw_pick_id' in item:
                try:
                    if item.get('league') is None: item['league'] = "Unknown"
                    if item.get('pick_value') is None: continue
                    if len(item['pick_value']) > 3:
                        results.append(ParsedPick(**item))
                except Exception as e:
                    pass
        
        return results

    except Exception as e:
        logger.error(f"AI Error: {e}")
        raise
