import os
import requests
import json
import logging
import time
import base64
from threading import Semaphore

# MAXIMUM SPEED: Groq allows 1000 RPM = 16 concurrent requests
# Replace single Lock with Semaphore for parallel execution
GROQ_CONCURRENCY_LIMIT = 16
GLOBAL_GROQ_SEMAPHORE = Semaphore(GROQ_CONCURRENCY_LIMIT)
LOCK_ACQUIRE_TIMEOUT = 30  # Reduced from 300s for faster failure

# Model Configuration - User-specified high-performance models
DEFAULT_TEXT_MODEL = "llama-3.3-70b-versatile"  # User's choice - best quality
DEFAULT_VISION_MODEL = (
    "meta-llama/llama-4-scout-17b-16e-instruct"  # Updated to Llama 4 Scout (Preview)
)

# Available models with rate limits (1000 RPM each)
GROQ_MODELS = {
    "llama-3.1-8b-instant": {"rpm": 1000, "tpm": 250000, "speed": 560},
    "llama-3.3-70b-versatile": {"rpm": 1000, "tpm": 300000, "speed": 280},
    "openai/gpt-oss-120b": {"rpm": 1000, "tpm": 250000, "speed": 500},
    "openai/gpt-oss-20b": {"rpm": 1000, "tpm": 250000, "speed": 1000},
}


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

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Encode image (supports file path or base64)
    try:
        if isinstance(image_input, str) and (
            len(image_input) < 1000 or os.path.exists(image_input)
        ):
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
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(3):
        try:
            # Use Semaphore for 16 concurrent requests (not Lock which blocks all)
            if not GLOBAL_GROQ_SEMAPHORE.acquire(timeout=LOCK_ACQUIRE_TIMEOUT):
                logging.error("[Groq] Failed to acquire semaphore slot.")
                return None

            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=timeout
                )
            finally:
                GLOBAL_GROQ_SEMAPHORE.release()

            if response.status_code == 200:
                data = response.json()
                try:
                    content = data["choices"][0]["message"]["content"]
                    return content
                except KeyError:
                    logging.error(f"[Groq] Unexpected response format: {data}")
                    return None
            elif response.status_code == 429:
                # Log Rate Limit Details
                remaining_tokens = response.headers.get("x-ratelimit-remaining-tokens")
                remaining_reqs = response.headers.get("x-ratelimit-remaining-requests")
                reset_time = response.headers.get("x-ratelimit-reset-tokens")

                logging.warning(
                    f"[Groq-Vision] Rate limit (429). Headers: "
                    f"Tokens Rem={remaining_tokens}, Reqs Rem={remaining_reqs}, Reset={reset_time}"
                )
                raise Exception("Groq Rate limit 429")
            else:
                logging.error(f"[Groq] Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            if "429" in str(e):
                raise e
            logging.error(f"[Groq] Exception: {e}")
            return None

    return None


def groq_text_completion(
    prompt, model=DEFAULT_TEXT_MODEL, timeout=60, validate_json=True
):
    """
    Calls Groq API for text-only tasks (parsing).
    MAXIMUM SPEED: 16 concurrent requests allowed (1000 RPM).
    """
    api_key = os.getenv("GROQ_TOKEN")
    if not api_key:
        raise ValueError("GROQ_TOKEN not found in environment variables.")

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    # Auto-detect DSL mode
    if "OUTPUT:TEXT" in prompt:
        validate_json = False

    if validate_json:
        payload["response_format"] = {"type": "json_object"}

    for attempt in range(3):
        try:
            # Use Semaphore for 16 concurrent requests (not Lock which blocks all)
            if not GLOBAL_GROQ_SEMAPHORE.acquire(timeout=LOCK_ACQUIRE_TIMEOUT):
                logging.error("[Groq] Failed to acquire semaphore slot.")
                return None

            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=timeout
                )
            finally:
                GLOBAL_GROQ_SEMAPHORE.release()

            if response.status_code == 200:
                data = response.json()
                try:
                    content = data["choices"][0]["message"]["content"]
                    if validate_json:
                        try:
                            json.loads(content)
                            return content
                        except json.JSONDecodeError:
                            logging.warning(
                                f"[Groq] Invalid JSON response. Retrying..."
                            )
                            continue
                    return content
                except KeyError:
                    logging.error(f"[Groq] Unexpected response format: {data}")
                    return None
            elif response.status_code == 429:
                # Log Rate Limit Details
                remaining_tokens = response.headers.get("x-ratelimit-remaining-tokens")
                remaining_reqs = response.headers.get("x-ratelimit-remaining-requests")
                reset_time = response.headers.get("x-ratelimit-reset-tokens")

                logging.warning(
                    f"[Groq-Text] Rate limit (429). Headers: "
                    f"Tokens Rem={remaining_tokens}, Reqs Rem={remaining_reqs}, Reset={reset_time}"
                )
                raise Exception("Groq Rate limit 429")
            else:
                logging.error(f"[Groq] Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            if "429" in str(e):
                raise e
            logging.error(f"[Groq] Exception: {e}")
            return None

    return None
