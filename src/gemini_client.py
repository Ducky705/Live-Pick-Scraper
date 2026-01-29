import base64
import logging
import os
from threading import Semaphore

import requests

# MAXIMUM SPEED: Gemini model-specific rate limits
# gemini-2.5-flash-lite: 15 RPM = 3 concurrent
# gemini-2.5-flash: 10 RPM = 2 concurrent
# gemini-2.0-flash: 10 RPM = 2 concurrent
GEMINI_CONCURRENCY_LIMIT = 3
GLOBAL_GEMINI_SEMAPHORE = Semaphore(GEMINI_CONCURRENCY_LIMIT)
LOCK_ACQUIRE_TIMEOUT = 30  # Reduced for faster failure

# Model-specific rate limits
GEMINI_RATE_LIMITS = {
    "gemini-2.5-flash-lite": {"rpm": 15, "tpm": 250000, "min_delay": 4.0},
    "gemini-2.5-flash": {"rpm": 10, "tpm": 250000, "min_delay": 6.0},
    "gemini-2.0-flash": {"rpm": 10, "tpm": 250000, "min_delay": 6.0},
    "gemini-2.0-flash-exp": {"rpm": 10, "tpm": 250000, "min_delay": 6.0},
    "gemini-1.5-flash": {"rpm": 15, "tpm": 250000, "min_delay": 4.0},
}

# Recommended Free Tier Model (highest RPM)
DEFAULT_MODEL = "gemini-2.0-flash-exp"


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

    headers = {"Content-Type": "application/json"}

    # Encode image (supports file path or base64)
    try:
        if isinstance(image_input, str) and (len(image_input) < 1000 or os.path.exists(image_input)):
            # It's a file path
            with open(image_input, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        # Assume it's already base64
        elif isinstance(image_input, bytes):
            image_data = base64.b64encode(image_input).decode("utf-8")
        else:
            image_data = image_input if image_input else ""
    except Exception as e:
        logging.error(f"[Gemini] Failed to process image input: {e}")
        return None

    # Construct Payload (Google Format)
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            # Force JSON if possible, though strict JSON mode in Gemini 1.5 Flash
            # sometimes requires schema. We'll stick to text prompt instruction for now
            # or use response_mime_type if supported by the specific model version.
            "response_mime_type": "application/json",
        },
    }

    for attempt in range(3):
        try:
            # Use Semaphore for 3 concurrent requests (15 RPM)
            if not GLOBAL_GEMINI_SEMAPHORE.acquire(timeout=LOCK_ACQUIRE_TIMEOUT):
                logging.error("[Gemini] Failed to acquire semaphore slot.")
                return None

            try:
                # Model-specific delay (removed hardcoded 4s, now handled by rate limiter)
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            finally:
                GLOBAL_GEMINI_SEMAPHORE.release()

            if response.status_code == 200:
                data = response.json()
                try:
                    # Parse Google Response
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return content
                except KeyError:
                    logging.error(f"[Gemini] Unexpected response format: {data}")
                    return None

            elif response.status_code == 429:
                logging.warning("[Gemini] Rate limit (429). Failing fast.")
                raise Exception("Gemini Rate limit 429")
            else:
                logging.error(f"[Gemini] Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            if "429" in str(e):
                raise e
            # US-002: Raise Timeout
            if "timeout" in str(e).lower() or isinstance(e, requests.Timeout):
                raise e
            logging.error(f"[Gemini] Exception: {e}")
            return None

    return None


def gemini_text_completion(prompt, model=DEFAULT_MODEL, timeout=60):
    """
    Calls Google Gemini API (Directly) for Text tasks.
    MAXIMUM SPEED: 3 concurrent requests (15 RPM for flash-lite).
    """
    api_key = os.getenv("GEMINI_TOKEN")
    if not api_key:
        raise ValueError("GEMINI_TOKEN not found in environment variables.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}

    # Construct Payload (Google Format)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json",
        },
    }

    for attempt in range(3):
        try:
            # Use Semaphore for 3 concurrent requests (15 RPM)
            if not GLOBAL_GEMINI_SEMAPHORE.acquire(timeout=LOCK_ACQUIRE_TIMEOUT):
                logging.error("[Gemini] Failed to acquire semaphore slot.")
                return None

            try:
                # Model-specific delay (removed hardcoded 4s, now handled by rate limiter)
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            finally:
                GLOBAL_GEMINI_SEMAPHORE.release()

            if response.status_code == 200:
                data = response.json()
                try:
                    # Parse Google Response
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return content
                except KeyError:
                    logging.error(f"[Gemini] Unexpected response format: {data}")
                    return None

            elif response.status_code == 429:
                logging.warning("[Gemini] Rate limit (429). Failing fast.")
                raise Exception("Gemini Rate limit 429")
            else:
                logging.error(f"[Gemini] Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            if "429" in str(e):
                raise e
            # US-002: Raise Timeout
            if "timeout" in str(e).lower() or isinstance(e, requests.Timeout):
                raise e
            logging.error(f"[Gemini] Exception: {e}")
            return None

    return None
