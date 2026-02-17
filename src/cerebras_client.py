import json
import logging
import os
import random
import time
from threading import Semaphore

import requests
from dotenv import load_dotenv

load_dotenv()

# MAXIMUM SPEED: Cerebras allows 30 RPM = 2 concurrent requests
# Replace Lock with Semaphore for parallel execution
CEREBRAS_CONCURRENCY_LIMIT = 2
GLOBAL_CEREBRAS_SEMAPHORE = Semaphore(CEREBRAS_CONCURRENCY_LIMIT)
LOCK_ACQUIRE_TIMEOUT = 30  # Reduced for faster failure

# Model Configuration - User-specified high-performance model
DEFAULT_TEXT_MODEL = "llama3.1-70b"

# Available models with rate limits (30 RPM, 60K TPM each)
CEREBRAS_MODELS = {
    "llama3.1-70b": {"rpm": 30, "tpm": 60000},
    "llama3.1-8b": {"rpm": 30, "tpm": 60000},
    "qwen-2.5-72b-instruct": {"rpm": 30, "tpm": 60000},  # Updated Qwen
    "gpt-oss-120b": {"rpm": 30, "tpm": 60000},
}

RETRY_CONFIG = {
    "max_cycles": 5,  # Cerebras is usually reliable, so fewer retries needed
    "base_delay": 1,
    "cycle_delay": 2,
    "max_delay": 10,
    "jitter": 0.1,
}


def _get_backoff_delay(attempt, base=1, max_delay=10, jitter=0.1):
    delay = min(base * (2**attempt), max_delay)
    jitter_range = delay * jitter
    delay += random.uniform(-jitter_range, jitter_range)
    return max(0.5, delay)


def _extract_valid_json(text):
    """
    Robustly extracts the first valid JSON object or array from a string.
    Same helper as in openrouter_client.
    """
    text = text.strip()
    idx = 0
    decoder = json.JSONDecoder()

    while idx < len(text):
        next_open = -1
        for i, c in enumerate(text[idx:]):
            if c in "{[":
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


def cerebras_completion(
    prompt,
    model=DEFAULT_TEXT_MODEL,
    images=None,
    timeout=60,
    max_cycles=None,
    validate_json=True,
):
    """
    Calls Cerebras API.
    Note: Cerebras currently supports text-only for these models.
    If images are provided, this function will raise an error or should fallback (handled by caller).
    """
    if images:
        logging.warning(
            "[Cerebras] Images provided but Cerebras models are text-only (mostly). Ignoring images or falling back."
        )
        # For now, we'll proceed with text only if images are ignored, or raise?
        # The prompt usually contains the text.
        # If the prompt DEPENDS on the image, this will fail to produce good results.
        # But let's assume the caller handles fallback if they really need vision.
        pass

    if max_cycles is None:
        max_cycles = RETRY_CONFIG["max_cycles"]

    api_key = os.getenv("CEREBRAS_TOKEN")
    if not api_key:
        raise ValueError("CEREBRAS_TOKEN not found in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Cerebras payload
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        # Cerebras supports response_format={"type": "json_object"} for Llama 3 models usually
        "response_format": {"type": "json_object"},
    }

    last_error = None

    for cycle in range(max_cycles):
        try:
            # Use Semaphore for 2 concurrent requests (30 RPM = 0.5/sec)
            if not GLOBAL_CEREBRAS_SEMAPHORE.acquire(timeout=LOCK_ACQUIRE_TIMEOUT):
                logging.error("[Cerebras] Failed to acquire semaphore slot. Skipping.")
                continue

            try:
                response = requests.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
            finally:
                GLOBAL_CEREBRAS_SEMAPHORE.release()

            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]

                    if validate_json:
                        extracted = _extract_valid_json(content)
                        if extracted:
                            return extracted
                        else:
                            logging.warning(f"[Cerebras] Invalid JSON from {model}. Retrying.")
                            last_error = "Invalid JSON"
                            # Loop will retry
                    else:
                        return content.strip()
                else:
                    logging.warning("[Cerebras] No choices returned.")
            elif response.status_code == 429:
                logging.warning("[Cerebras] Rate limit (429). Failing fast.")
                raise Exception("Cerebras Rate limit 429")
            else:
                logging.error(f"[Cerebras] Error {response.status_code}: {response.text}")
                last_error = f"Error {response.status_code}"

        except Exception as e:
            if "429" in str(e):
                raise e
            # US-002: Raise Timeout
            if "timeout" in str(e).lower() or isinstance(e, requests.Timeout):
                raise e
            logging.error(f"[Cerebras] Exception: {e}")
            last_error = str(e)

        # Wait before retry
        wait_time = _get_backoff_delay(cycle, RETRY_CONFIG["cycle_delay"], RETRY_CONFIG["max_delay"])
        time.sleep(wait_time)

    raise Exception(f"[Cerebras] Failed after {max_cycles} cycles. Last error: {last_error}")
