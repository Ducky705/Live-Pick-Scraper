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

# Model Configuration - User-specified high-performance models
DEFAULT_TEXT_MODEL = "llama-3.3-70b-versatile"  # Best for complex JSON parsing
DEFAULT_VISION_MODEL = "llama-3.2-11b-vision-preview"  # Best vision model on Groq


def groq_vision_completion(prompt, image_input, model=DEFAULT_VISION_MODEL, timeout=60):
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
            with open(image_input, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        else:
            if isinstance(image_input, bytes):
                image_data = base64.b64encode(image_input).decode("utf-8")
            else:
                image_data = image_input if image_input else ""
    except Exception as e:
        logging.error(f"[Groq] Failed to process image input: {e}")
        return None

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
                retry_after = int(response.headers.get("Retry-After", 5))
                logging.warning(f"[Groq] Rate limit (429). Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            else:
                logging.error(f"[Groq] Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logging.error(f"[Groq] Exception: {e}")
            return None
    
    return None


def groq_text_completion(prompt, model=DEFAULT_TEXT_MODEL, timeout=60, validate_json=True):
    """
    Calls Groq API for text-only tasks (parsing).
    Uses the high-performance llama-3.3-70b-versatile model.
    """
    api_key = os.getenv("GROQ_TOKEN")
    if not api_key:
        raise ValueError("GROQ_TOKEN not found in environment variables.")
 
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
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
                    if validate_json:
                        try:
                            json.loads(content)
                            return content
                        except json.JSONDecodeError:
                            logging.warning(f"[Groq] Invalid JSON response. Retrying...")
                            continue
                    return content
                except KeyError:
                    logging.error(f"[Groq] Unexpected response format: {data}")
                    return None
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logging.warning(f"[Groq] Rate limit (429). Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            else:
                logging.error(f"[Groq] Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logging.error(f"[Groq] Exception: {e}")
            return None
    
    return None
