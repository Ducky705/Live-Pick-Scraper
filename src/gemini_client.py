
import os
import requests
import json
import logging
import time
import base64
from threading import Lock

# Global Concurrency Limiter for Gemini
# Google Free Tier limits: 15 RPM (Requests Per Minute), 1500 RPD
# We need to be careful.
GLOBAL_GEMINI_LOCK = Lock()
LOCK_ACQUIRE_TIMEOUT = 300

# Recommended Free Tier Model
# gemini-2.5-flash-lite is the current best free vision model
DEFAULT_MODEL = "gemini-2.5-flash-lite"

def gemini_vision_completion(prompt, image_input, model=DEFAULT_MODEL, timeout=60):
    """
    Calls Google Gemini API (Directly) for Vision tasks.
    Args:
        image_input: Can be a file path (str) or base64 string.
    """
    api_key = os.getenv("GEMINI_TOKEN")
    if not api_key:
        raise ValueError("GEMINI_TOKEN not found in environment variables.")
 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }

    # Encode image (supports file path or base64)
    try:
        if isinstance(image_input, str) and (len(image_input) < 1000 or os.path.exists(image_input)):
            # It's a file path
            with open(image_input, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        else:
            # Assume it's already base64
            if isinstance(image_input, bytes):
                image_data = base64.b64encode(image_input).decode("utf-8")
            else:
                image_data = image_input if image_input else ""
    except Exception as e:
        logging.error(f"[Gemini] Failed to process image input: {e}")
        return None

    # Construct Payload (Google Format)
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_data
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            # Force JSON if possible, though strict JSON mode in Gemini 1.5 Flash 
            # sometimes requires schema. We'll stick to text prompt instruction for now
            # or use response_mime_type if supported by the specific model version.
            "response_mime_type": "application/json"
        }
    }

    for attempt in range(3):
        try:
            # Simple rate limit handling
            if not GLOBAL_GEMINI_LOCK.acquire(timeout=LOCK_ACQUIRE_TIMEOUT):
                logging.error("[Gemini] Failed to acquire lock.")
                return None
            
            try:
                # Add a small delay to respect the 15 RPM (4s per request ideally)
                # We enforces a 4s wait to be safe on the free tier
                time.sleep(4)
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            finally:
                GLOBAL_GEMINI_LOCK.release()

            if response.status_code == 200:
                data = response.json()
                try:
                    # Parse Google Response
                    content = data['candidates'][0]['content']['parts'][0]['text']
                    return content
                except KeyError:
                    logging.error(f"[Gemini] Unexpected response format: {data}")
                    return None
            
            elif response.status_code == 429:
                logging.warning("[Gemini] Rate limit (429). Waiting 5s...")
                time.sleep(5)
                continue
            else:
                logging.error(f"[Gemini] Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logging.error(f"[Gemini] Exception: {e}")
            return None
    
    return None
