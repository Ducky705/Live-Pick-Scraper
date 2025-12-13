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
You are a specialized sports betting data extraction API.
You will be given unstructured Telegram messages containing betting picks.
Your ONLY task is to extract the picks into a valid JSON array.

### INPUT DATA
{data_json}

### RULES
1. **Output ONLY JSON**. Do not write "Here is the JSON" or markdown ticks. Just the array.
2. **IGNORE HYPE**: Ignore words like "Whale", "Lock", "Banger", "Max Bet".
3. **EXTRACT LINES**: Look for Team Names followed by spreads (-5, +3.5), Moneyline (ML), or Totals (Over/Under).
4. **MANDATORY**: You MUST include the "raw_pick_id" from the input in your output object.
5. **NULLS**: If unit or odds are not found, set them to null.
6. **NO PICKS?**: If the text contains no valid picks, return an empty array [].

### OUTPUT FORMAT
[
  {{"raw_pick_id": 123, "pick_value": "Lakers -5", "bet_type": "Spread", "unit": 2.0, "odds_american": -110, "league": "NBA"}}
]
"""

def _repair_json(text: str) -> str:
    # Remove markdown code blocks
    text = re.sub(r'```json', '', text, flags=re.I)
    text = re.sub(r'```', '', text)
    text = text.strip()
    
    # Attempt to find the array brackets
    start = text.find('[')
    end = text.rfind(']')
    
    if start != -1 and end != -1:
        return text[start:end+1]
    return "[]"

def parse_with_ai(raw_picks: List[RawPick]) -> List[ParsedPick]:
    if not client or not raw_picks: return []

    print(f"🤖 AI PARSER: Using Model -> {AI_PARSER_MODEL}")

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
            # Fallback: regex search for objects if array parsing fails
            objects = re.findall(r'\{[^{}]+\}', clean_json)
            parsed_data = [json.loads(o) for o in objects]

        results = []
        for item in parsed_data:
            # Safety: Ensure ID linkage
            if 'raw_pick_id' not in item and len(raw_picks) == 1:
                item['raw_pick_id'] = raw_picks[0].id

            if 'raw_pick_id' in item:
                try:
                    if item.get('league') is None: item['league'] = "Unknown"
                    if item.get('pick_value') is None: continue
                    # Sanity check length to filter hallucinations
                    if 3 < len(str(item['pick_value'])) < 50:
                        results.append(ParsedPick(**item))
                except Exception:
                    pass
        
        return results

    except Exception as e:
        logger.error(f"AI Error: {e}")
        # Don't raise, just return empty so flow continues (main loop handles retry logic)
        return []
