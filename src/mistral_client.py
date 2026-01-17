import os
import requests
import json
import logging
import time
import random
import base64
from threading import Lock
from dotenv import load_dotenv

load_dotenv()

# Global Concurrency Limiter for Mistral
GLOBAL_MISTRAL_LOCK = Lock()
LOCK_ACQUIRE_TIMEOUT = 300

# Models
# Text / Reasoning
MISTRAL_LARGE = "mistral-large-latest" 
MISTRAL_SMALL = "mistral-small-latest"
MISTRAL_NEMO = "open-mistral-nemo"
CODESTRAL = "codestral-latest"

# Vision
PIXTRAL_LARGE = "pixtral-large-latest"
PIXTRAL_12B = "pixtral-12b-2409"

RETRY_CONFIG = {
    "max_cycles": 5,
    "base_delay": 1,
    "cycle_delay": 2,
    "max_delay": 10,
    "jitter": 0.1,
}

def _get_backoff_delay(attempt, base=1, max_delay=10, jitter=0.1):
    delay = min(base * (2 ** attempt), max_delay)
    jitter_range = delay * jitter
    delay += random.uniform(-jitter_range, jitter_range)
    return max(0.5, delay)

def _extract_valid_json(text):
    text = text.strip()
    idx = 0
    decoder = json.JSONDecoder()
    
    while idx < len(text):
        next_open = -1
        for i, c in enumerate(text[idx:]):
            if c in '{[':
                next_open = idx + i
                break
        
        if next_open == -1:
            return None
            
        try:
            obj, end_pos = decoder.raw_decode(text[next_open:])
            return text[next_open : next_open + end_pos]
        except json.JSONDecodeError:
            idx = next_open + 1
            
    return None

def mistral_completion(prompt, model=MISTRAL_SMALL, image_input=None, timeout=60, max_cycles=None, validate_json=True):
    """
    Calls Mistral API.
    Supports both text and vision (if model supports it and image_input is provided).
    """
    if max_cycles is None:
        max_cycles = RETRY_CONFIG["max_cycles"]

    api_key = os.getenv("MISTRAL_TOKEN")
    if not api_key:
        raise ValueError("MISTRAL_TOKEN not found in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Prepare messages
    messages = []
    
    if image_input:
        # Vision Request
        # Check if model is a pixtral model
        if "pixtral" not in model.lower():
            logging.warning(f"[Mistral] Image provided but model {model} might not support vision. Proceeding anyway.")

        image_data = None
        if isinstance(image_input, str) and (len(image_input) < 1000 or os.path.exists(image_input)):
            # File path
            try:
                with open(image_input, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                logging.error(f"[Mistral] Failed to read image file: {e}")
                return None
        else:
            # Assume base64 string
            image_data = image_input

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{image_data}" 
                }
            ]
        })
    else:
        # Text Request
        messages.append({
            "role": "user",
            "content": prompt
        })

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "response_format": {"type": "json_object"} # Mistral supports this
    }

    last_error = None

    for cycle in range(max_cycles):
        try:
            # Acquire lock
            if not GLOBAL_MISTRAL_LOCK.acquire(timeout=LOCK_ACQUIRE_TIMEOUT):
                logging.error(f"[Mistral] Failed to acquire lock. Skipping.")
                continue

            try:
                response = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
            finally:
                GLOBAL_MISTRAL_LOCK.release()

            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    
                    if validate_json:
                        extracted = _extract_valid_json(content)
                        if extracted:
                            return extracted
                        else:
                            logging.warning(f"[Mistral] Invalid JSON from {model}. Retrying.")
                            last_error = "Invalid JSON"
                            # Loop will retry
                    else:
                        return content.strip()
                else:
                    logging.warning(f"[Mistral] No choices returned.")
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 2))
                logging.warning(f"[Mistral] Rate limit (429). Waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                logging.error(f"[Mistral] Error {response.status_code}: {response.text}")
                last_error = f"Error {response.status_code}: {response.text}"

        except Exception as e:
            logging.error(f"[Mistral] Exception: {e}")
            last_error = str(e)

        # Wait before retry
        wait_time = _get_backoff_delay(cycle, RETRY_CONFIG["cycle_delay"], RETRY_CONFIG["max_delay"])
        time.sleep(wait_time)

    # Only raise exception if all retries failed
    logging.error(f"[Mistral] Failed after {max_cycles} cycles. Last error: {last_error}")
    return None
