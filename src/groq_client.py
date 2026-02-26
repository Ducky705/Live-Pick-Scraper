
# src/groq_client.py
import logging
import os
import time

from dotenv import load_dotenv

load_dotenv()

try:
    from config import GROQ_TOKEN as GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = os.getenv("GROQ_TOKEN")

# Use our URLLIB replacement if installed, else try standard requests (which might fail)
try:
    from src.utils_urllib import post
except ImportError:
    import requests
    def post(url, **kwargs):
        resp = requests.post(url, **kwargs)
        return resp

logger = logging.getLogger(__name__)

DEFAULT_TEXT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_VISION_MODEL = "llama-3.2-11b-vision-preview"


import random


def groq_text_completion(prompt, model=DEFAULT_TEXT_MODEL, timeout=10, max_retries=3):
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set.")
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    for attempt in range(max_retries + 1):
        try:
            # Randomize timeout slightly to prevent thundering herd
            current_timeout = timeout + random.uniform(0, 2)
            response = post(url, json=payload, headers=headers, timeout=current_timeout)

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]

            elif response.status_code == 429:
                # Rate limit - exponential backoff
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Groq 429 Rate Limit. Retrying in {wait:.2f}s...")
                time.sleep(wait)
                continue

            elif response.status_code >= 500:
                # Server error - strict backoff
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Groq {response.status_code} Error. Retrying in {wait:.2f}s...")
                time.sleep(wait)
                continue

            else:
                logger.error(f"Groq Text API Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Groq Text Request Failed (Attempt {attempt+1}): {e}")
            if attempt < max_retries:
                 time.sleep(1 + attempt)
            else:
                 return None

    return None


def groq_vision_completion(prompt, image_input, model=DEFAULT_VISION_MODEL, timeout=30):
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set.")
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Handle image input (URL or Base64)
    image_url_obj = {}
    if str(image_input).startswith("http"):
         image_url_obj = {"url": image_input}
    # Assume base64 or file path (if file path, we need to read it)
    # For simplicity, if it's not http, assume it's base64 or path.
    # If path, read and strict base64.
    elif os.path.exists(str(image_input)):
        try:
            import base64
            with open(image_input, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                image_url_obj = {"url": f"data:image/jpeg;base64,{b64}"}
        except:
            logger.error(f"Failed to read image file {image_input}")
            return None
    else:
        # Assume already base64
        prefix = "data:image/jpeg;base64," if "data:" not in str(image_input) else ""
        image_url_obj = {"url": f"{prefix}{image_input}"}

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": image_url_obj}
                ]
            }
        ],
        "temperature": 0.1
    }

    try:
        response = post(url, json=payload, headers=headers, timeout=timeout)

        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            logger.error(f"Groq Vision API Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Groq Vision Request Failed: {e}")
        return None
