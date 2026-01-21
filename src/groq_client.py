
import os
import requests
import json
import logging
import time
import base64
from threading import Lock

# Global Concurrency Limiter for Groq
GLOBAL_GROQ_LOCK = Lock()
LOCK_ACQUIRE_TIMEOUT = 300

# Groq Vision Models - Llama 4 Scout/Maverick (2025)
# See: https://console.groq.com/docs/vision
VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",    # Fast, good quality
    "meta-llama/llama-4-maverick-17b-128e-instruct", # Higher quality, slower
]
DEFAULT_MODEL = VISION_MODELS[0]  # Use Scout as default (faster)

def groq_vision_completion(prompt, image_input, model=DEFAULT_MODEL, timeout=60):
    """
    Calls Groq API (Directly) for Vision tasks.
    Args:
        image_input: Can be a file path (str) or base64 string.
    """
    api_key = os.getenv("GROQ_TOKEN")
    if not api_key:
        raise ValueError("GROQ_TOKEN not found in environment variables.")
 
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Encode image (supports file path or base64)
    try:
        if isinstance(image_input, str) and (len(image_input) < 1000 or os.path.exists(image_input)):
            # It's a file path or a very short string that looks like a path
            # (Base64 is usually much longer than 1000 chars)
            with open(image_input, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        else:
            # Assume it's already base64
            # Handle both string and bytes
            if isinstance(image_input, bytes):
                image_data = base64.b64encode(image_input).decode("utf-8")
            else:
                # It's a string, check if it looks like base64
                # If it's already b64, use it directly
                image_data = image_input if image_input else ""
    except Exception as e:
        logging.error(f"[Groq] Failed to process image input: {e}")
        return None

    # Construct Payload (OpenAI Compatible)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,
        # Groq supports JSON mode
        "response_format": {"type": "json_object"}
    }

    for attempt in range(3):
        try:
            if not GLOBAL_GROQ_LOCK.acquire(timeout=LOCK_ACQUIRE_TIMEOUT):
                logging.error("[Groq] Failed to acquire lock.")
                return None
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            finally:
                GLOBAL_GROQ_LOCK.release()

            if response.status_code == 200:
                data = response.json()
                try:
                    content = data['choices'][0]['message']['content']
                    return content
                except KeyError:
                    logging.error(f"[Groq] Unexpected response format: {data}")
                    return None
            
            elif response.status_code == 429:
                # Groq has strict rate limits on free tier
                retry_after = int(response.headers.get("Retry-After", 5))
                logging.warning(f"[Groq] Rate limit (429). Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            
            elif response.status_code == 503:
                # Service unavailable - Llama 4 models can be at capacity
                # Try fallback to Maverick if on Scout, or retry with backoff
                wait_time = 5 * (attempt + 1)
                logging.warning(f"[Groq] Service unavailable (503). Attempt {attempt+1}/3. Waiting {wait_time}s...")
                time.sleep(wait_time)
                
                # On second attempt, try the other model
                if attempt == 1 and model == VISION_MODELS[0] and len(VISION_MODELS) > 1:
                    logging.info(f"[Groq] Switching to fallback model: {VISION_MODELS[1]}")
                    payload["model"] = VISION_MODELS[1]
                continue
            
            else:
                logging.error(f"[Groq] Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logging.error(f"[Groq] Exception: {e}")
            return None
    
    return None
