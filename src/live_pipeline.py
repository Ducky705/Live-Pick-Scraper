import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from PIL import Image

from src.supabase_client import get_or_create_capper_id
from src.utils_urllib import post

logger = logging.getLogger(__name__)

# Fallback models in case OpenRouter is used
DEFAULT_MODEL = "stepfun/step-3.5-flash:free"
FALLBACK_MODEL = "mistralai/mistral-small-3.1-24b-instruct:free"

SYSTEM_PROMPT = """
You are an expert sports betting analyst. Your task is to process a single message from a sports handicapper.
First, classify the message into one of these categories:
- PICK: Contains an upcoming prediction with a specific team/player to bet on.
- PROMO: VIP offers, sign-up bonuses, ads.
- RECAP: Reviewing past performance, showing winning slips, checkmarks.
- NOISE: Conversational chatter, off-topic, not a prediction.

If the classification is PICK, extract the predictions into a JSON array of objects.
Each object must have exactly these keys:
- "capper_name": The name of the person giving the pick (if unknown, use "Unknown"). Use context or channel name.
- "league": The sports league (e.g., NBA, NFL, MLB, NHL, Tennis, Soccer, etc.).
- "pick_value": The specific team, player, or total being bet on (e.g., "Lakers -5.5", "LeBron James Over 25.5 Pts").
- "bet_type": E.g., "Moneyline", "Spread", "Total", "Prop", "Parlay".
- "unit": The confidence or amount wagered as a float (e.g., 1.0, 2.0). If omitted, default to 1.0.
- "odds_american": The odds in American format (e.g., -110, +150). If omitted, use null.

IMPORTANT INSTRUCTIONS:
- You must return ONLY a raw JSON object with two keys: "classification" (string) and "picks" (array).
- Do not use markdown blocks like ```json ... ```. Just return the raw JSON text.
- If classification is NOT PICK, the "picks" array should be empty [].

JSON format example:
{
  "classification": "PICK",
  "picks": [
    {
      "capper_name": "VIP Sports",
      "league": "NBA",
      "pick_value": "Celtics -4.5",
      "bet_type": "Spread",
      "unit": 2.0,
      "odds_american": -110
    }
  ]
}
"""

def clean_json_response(text: str) -> str:
    """Clean markdown formatting from LLM response."""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return text.strip()

def encode_image(image_path: str) -> str:
    """Encode an image as a base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {e}")
        return ""

def call_openrouter(message_text: str, image_paths: List[str], channel_name: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("OPENROUTER_API_KEY is not set.")
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/cappersuite",
        "X-Title": "CapperSuite Live"
    }
    
    content_list = [{"type": "text", "text": f"Channel Name context: {channel_name}\n\nMessage Text:\n{message_text}"}]
    
    for img_path in image_paths:
        base64_img = encode_image(img_path)
        if base64_img:
            ext = img_path.split('.')[-1].lower()
            mime = f"image/{ext}" if ext in ["jpeg", "png", "webp", "gif"] else "image/jpeg"
            content_list.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{base64_img}"}
            })
            
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content_list}
        ],
        "temperature": 0.0,
    }
    
    resp = post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code == 403 or resp.status_code == 429:
        raise Exception(f"OpenRouter Rate/Token limit hit ({resp.status_code}): {resp.text}")
    elif resp.status_code == 404:
        logger.warning(f"OpenRouter Model {DEFAULT_MODEL} not found. Fallback to {FALLBACK_MODEL}.")
        payload["model"] = FALLBACK_MODEL
        resp = post(url, headers=headers, json=payload, timeout=60)

    if resp.status_code != 200:
        raise Exception(f"OpenRouter returned {resp.status_code}: {resp.text}")
        
    data = resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")

def call_gemini(message_text: str, image_paths: List[str], channel_name: str) -> str:
    api_key = os.getenv("GEMINI_TOKEN")
    if not api_key:
        raise Exception("GEMINI_TOKEN is not set in .env.")
        
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=api_key)
    
    contents = [f"Channel Name context: {channel_name}\n\nMessage Text:\n{message_text or 'No text provided.'}"]
    
    if image_paths:
        for path in image_paths:
            try:
                img = Image.open(path)
                contents.append(img)
            except Exception as e:
                logger.error(f"Failed to load image for Gemini: {e}")

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            response_mime_type="application/json",
        )
    )
    return response.text

def call_mistral(message_text: str, image_paths: List[str], channel_name: str) -> str:
    api_key = os.getenv("MISTRAL_TOKEN")
    if not api_key:
        raise Exception("MISTRAL_TOKEN is not set.")
        
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    content_list = [{"type": "text", "text": f"Channel Name context: {channel_name}\n\nMessage Text:\n{message_text}"}]
    
    has_images = False
    for img_path in image_paths:
        base64_img = encode_image(img_path)
        if base64_img:
            has_images = True
            ext = img_path.split('.')[-1].lower()
            mime = f"image/{ext}" if ext in ["jpeg", "png", "webp", "gif"] else "image/jpeg"
            content_list.append({
                "type": "image_url",
                "image_url": f"data:{mime};base64,{base64_img}"
            })
            
    payload = {
        "model": "pixtral-12b-2409" if has_images else "mistral-large-latest",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content_list}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    # If using mistral-large-latest without images, the content should be a string, not a list of dicts.
    if not has_images:
        payload["messages"][1]["content"] = content_list[0]["text"]
    
    resp = post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise Exception(f"Mistral returned {resp.status_code}: {resp.text}")
        
    data = resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")

def process_live_message(
    message_text: str, 
    image_paths: List[str], 
    channel_name: str, 
    source_url: str, 
    source_unique_id: str,
    pick_date: str
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Extracts structured picks. 
    For text-only: OpenRouter -> Gemini -> Mistral.
    For images: Gemini -> Mistral -> OpenRouter.
    Returns (classification_string, list_of_pick_dicts)
    """
    llm_text = None
    
    if not image_paths:
        # TEXT ONLY: OpenRouter -> Gemini -> Mistral
        try:
            logger.info(f"[{channel_name}] Text only. Trying OpenRouter API...")
            llm_text = call_openrouter(message_text, image_paths, channel_name)
        except Exception as e:
            logger.warning(f"[{channel_name}] OpenRouter Failed ({e}). Falling back to Gemini...")
            try:
                llm_text = call_gemini(message_text, image_paths, channel_name)
            except Exception as e2:
                logger.warning(f"[{channel_name}] Gemini Failed ({e2}). Falling back to Mistral...")
                try:
                    llm_text = call_mistral(message_text, image_paths, channel_name)
                except Exception as e3:
                    logger.error(f"[{channel_name}] All API providers failed! Final err: {e3}")
                    return "ERROR_API", []
    else:
        # IMAGES INCLUDED: Gemini -> Mistral -> OpenRouter
        try:
            logger.info(f"[{channel_name}] Images detected. Trying Direct Google Gemini API...")
            llm_text = call_gemini(message_text, image_paths, channel_name)
        except Exception as e:
            logger.warning(f"[{channel_name}] Gemini Failed ({e}). Falling back to Mistral...")
            
            try:
                llm_text = call_mistral(message_text, image_paths, channel_name)
            except Exception as e2:
                logger.warning(f"[{channel_name}] Mistral Failed ({e2}). Falling back to OpenRouter...")
                
                try:
                    llm_text = call_openrouter(message_text, image_paths, channel_name)
                except Exception as e3:
                    logger.error(f"[{channel_name}] All API providers failed! Final err: {e3}")
                    return "ERROR_API", []

    if not llm_text:
        return "ERROR_PARSE", []

    # Parse output
    try:
        cleaned_json = clean_json_response(llm_text)
        parsed = json.loads(cleaned_json)
        classification = parsed.get("classification", "UNKNOWN")
        raw_picks = parsed.get("picks", [])
        
        if classification != "PICK" or not raw_picks:
            return classification, []
            
        structured_picks = []
        for p in raw_picks:
            capper_str = p.get("capper_name")
            if not capper_str or capper_str.lower() == "unknown":
                capper_str = channel_name
                
            capper_id = get_or_create_capper_id(capper_str)
            
            structured_picks.append({
                "capper_id": capper_id,
                "pick_date": pick_date,
                "league": str(p.get("league", "Other"))[:50],
                "pick_value": p.get("pick_value", "Unknown"),
                "bet_type": p.get("bet_type", "Unknown"),
                "unit": float(p.get("unit", 1.0)) if p.get("unit") is not None else 1.0,
                "odds_american": int(p.get("odds_american")) if p.get("odds_american") is not None else None,
                "result": "pending",
                "source_unique_id": source_unique_id,
                "source_url": source_url
            })
            
        return classification, structured_picks

    except json.JSONDecodeError as je:
        logger.error(f"[{channel_name}] Failed to parse JSON response: {je}\nResponse was: {llm_text}")
        return "ERROR_JSON", []
    except Exception as e:
        logger.error(f"[{channel_name}] Final Extraction Error: {e}")
        return "ERROR_API", []
