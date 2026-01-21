import os
import requests
import json
import logging
import time
import base64
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from threading import Semaphore, Lock

# Global Concurrency Limiter ("Traffic Cop")
# FULLY SEQUENTIAL: Free tier is extremely rate-limited (~2 req/min for Gemini)
# Using Lock instead of Semaphore - simpler and no blocking issues
# We wrap requests in a timeout to prevent infinite hangs
GLOBAL_REQUEST_LOCK = Lock()

# Maximum time to wait for the lock (seconds)
LOCK_ACQUIRE_TIMEOUT = 300  # 5 minutes max wait

# Model fallback list (ordered by reliability)
# VERIFIED WORKING FREE LIST - Only models confirmed via API to exist
# Note: Many "free" models are text-only or have limited availability
DEFAULT_MODELS = [
    "google/gemini-2.0-flash-exp:free",      # Primary
    "google/gemini-2.0-pro-exp-02-05:free",  # Backup
    "meta-llama/llama-3.3-70b-instruct:free", # Backup Text
]

# Models specifically for "Racing" (Parallel Text Parsing) - TEXT ONLY
FAST_PARSING_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

# Vision-capable models for OCR - VERIFIED VISION SUPPORT
# Most free models are text-only. Gemini Flash is the only reliable free vision model.
VISION_MODELS = [
    "google/gemini-2.0-flash-exp:free",      # Primary - 1M context, confirmed vision
    "qwen/qwen-2.5-vl-7b-instruct:free",     # Backup vision (Qwen VL)
    "nvidia/nemotron-nano-12b-v2-vl:free",   # Backup vision (Nvidia)
    "allenai/molmo-2-8b:free",               # Backup vision (AllenAI)
]

# Retry configuration for free-tier resilience
RETRY_CONFIG = {
    "max_cycles": 15,          # "Retry until it gets it" - significantly increased
    "base_delay": 2,           # Increased from 1 - give API time to recover
    "cycle_delay": 5,          # Increased from 2 - longer wait between full cycles
    "max_delay": 30,           # Increased from 15 - allow longer waits when hammered
    "jitter": 0.2,             # Slightly more jitter for randomization
}

def _get_backoff_delay(attempt, base=3, max_delay=60, jitter=0.3):
    """Calculate exponential backoff with jitter"""
    delay = min(base * (2 ** attempt), max_delay)
    jitter_range = delay * jitter
    delay += random.uniform(-jitter_range, jitter_range)
    return max(1, delay)


def _extract_valid_json(text):
    """
    Robustly extracts the first valid JSON object or array from a string.
    Ignores leading/trailing fluff and non-JSON blocks (like code snippets).
    """
    text = text.strip()
    idx = 0
    decoder = json.JSONDecoder()
    
    while idx < len(text):
        # Find next opening character
        next_open = -1
        # Simple scan for next { or [
        for i, c in enumerate(text[idx:]):
            if c in '{[':
                next_open = idx + i
                break
        
        if next_open == -1:
            return None # No JSON found
            
        try:
            # Attempt to parse from this point
            obj, end_pos = decoder.raw_decode(text[next_open:])
            # Return the exact substring that formed valid JSON
            return text[next_open : next_open + end_pos]
        except json.JSONDecodeError:
            # Not valid JSON starting here (e.g. "function() { ...")
            # Advance index past this opening char to keep searching
            idx = next_open + 1
            
    return None


from src.gemini_client import gemini_vision_completion

def openrouter_completion(prompt, model=None, images=None, timeout=180, max_cycles=None, validate_json=True):
    """
    Calls OpenRouter API with aggressive retry logic for free-tier resilience.
    Implements a "Circuit Breaker" to temporarily avoid failing models.
    
    Update: 
    1. Routes text-only requests to Cerebras (Llama 3.3) if CEREBRAS_TOKEN is present.
    2. Routes vision requests to Gemini Direct (Flash) if GEMINI_TOKEN is present.
    """
    # --- CEREBRAS ROUTING REMOVED ---
    # Hybrid routing is now handled by provider_pool.py
    # This client should ONLY talk to OpenRouter API

    # --- VISION ROUTING ---
    # Priority: Gemini Direct -> OpenRouter
    # Note: Groq routing removed - handled by provider_pool.py for hybrid logic
    if images and os.getenv("GEMINI_TOKEN"):
        try:
            img_input = None
            if isinstance(images, list) and len(images) > 0:
                img_input = images[0] # Base64 string or path
            
            if img_input:
                logging.info(f"[Router] Routing vision request to Gemini (2.5 Flash Lite)")
                result = gemini_vision_completion("Extract all text from this image.", img_input)
                if result:
                    return result
                else:
                    logging.warning("[Router] Gemini returned None. Falling back.")
        except Exception as e:
            logging.error(f"[Router] Gemini Direct failed: {e}. Falling back.")
            pass

    if max_cycles is None:
        max_cycles = RETRY_CONFIG["max_cycles"]
        
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram-scraper.local",
        "X-Title": "CapperSuite"
    }

    # Build model list: specified model first, then fallbacks
    models = []
    if model:
        models.append(model)
    for m in DEFAULT_MODELS:
        if m not in models:
            models.append(m)

    # State tracking
    model_failures = {m: 0 for m in models}
    blacklisted_models = set()
    last_error = None
    
    for cycle in range(max_cycles):
        # Filter available models (excluding blacklisted ones)
        available_models = [m for m in models if m not in blacklisted_models]
        
        # If all models are blacklisted/exhausted, reset to give them another chance
        if not available_models:
            logging.warning(f"[OpenRouter] All models exhausted. Resetting blacklist for Cycle {cycle+1}.")
            blacklisted_models.clear()
            available_models = list(models)
            time.sleep(RETRY_CONFIG["max_delay"]) # Longer wait before resetting

        for current_model in available_models:
            # Double check in case it got blacklisted inside the loop (unlikely but safe)
            if current_model in blacklisted_models: continue

            logging.info(f"[OpenRouter] Cycle {cycle+1}/{max_cycles}, Model: {current_model}")
            
            # Construct Content
            content_payload = [{"type": "text", "text": prompt}]
            
            if images:
                for img_item in images:
                    try:
                        # Support both file paths and base64 strings
                        if isinstance(img_item, str) and (os.path.exists(img_item) or len(img_item) < 1000):
                            # It's a file path
                            with open(img_item, "rb") as f:
                                b64_img = base64.b64encode(f.read()).decode("utf-8")
                        else:
                            # Assume it's already base64 string or bytes
                            b64_img = img_item if isinstance(img_item, str) else base64.b64encode(img_item).decode("utf-8")
                            
                        content_payload.append({
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                        })
                    except Exception as e:
                        logging.error(f"[OpenRouter] Failed to process image: {e}")

            if not images:
                final_content = prompt
            else:
                final_content = content_payload

            payload = {
                "model": current_model,
                "messages": [
                    {"role": "user", "content": final_content}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "provider": {
                    "sort": "throughput"  # Route to fastest available provider
                }
            }

            try:
                # TRAFFIC COP: Acquire lock with timeout to prevent deadlocks
                lock_acquired = GLOBAL_REQUEST_LOCK.acquire(timeout=LOCK_ACQUIRE_TIMEOUT)
                if not lock_acquired:
                    logging.error(f"[OpenRouter] Failed to acquire lock after {LOCK_ACQUIRE_TIMEOUT}s. Skipping request.")
                    model_failures[current_model] += 1
                    continue
                
                try:
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=timeout
                    )
                finally:
                    GLOBAL_REQUEST_LOCK.release()
                
                # --- ERROR HANDLING & CIRCUIT BREAKER ---
                
                # 1. Critical Client Errors (400 Bad Request, 404 Not Found)
                # These imply the model name is invalid or query is bad -> Blacklist immediately
                if response.status_code in (400, 404):
                    logging.error(f"[OpenRouter] {current_model} returned {response.status_code} (Client Error). Blacklisting model.")
                    blacklisted_models.add(current_model)
                    last_error = Exception(f"Model {current_model} error {response.status_code}")
                    continue

                # 2. Rate Limits (429) -> Switch models immediately (Load Balancing)
                if response.status_code == 429:
                    logging.warning(f"[OpenRouter] 429 Rate Limit from {current_model}. Waiting 10s then switching...")
                    
                    # FREE TIER FIX: Wait longer before retry (10s instead of 2s)
                    time.sleep(10)
                    try:
                        lock_acquired = GLOBAL_REQUEST_LOCK.acquire(timeout=60)
                        if lock_acquired:
                            try:
                                response = requests.post(
                                    "https://openrouter.ai/api/v1/chat/completions",
                                    headers=headers,
                                    json=payload,
                                    timeout=timeout
                                )
                            finally:
                                GLOBAL_REQUEST_LOCK.release()
                    except: pass
                    
                    if response.status_code == 429:
                        logging.warning(f"[OpenRouter] {current_model} still 429 after 10s. Blacklisting for this cycle.")
                        blacklisted_models.add(current_model)
                        # Add extra delay before trying next model
                        time.sleep(5)
                        continue # Skip to next model immediately
                
                # 3. Server Errors (500, 502, 503) -> Count failure
                if response.status_code >= 500:
                    model_failures[current_model] += 1
                    logging.warning(f"[OpenRouter] {current_model} Server Error {response.status_code}. Failures: {model_failures[current_model]}")
                
                # Check for success
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        
                        # Check for truncated response
                        finish_reason = data['choices'][0].get('finish_reason', '')
                        if finish_reason == 'length':
                            logging.warning(f"[OpenRouter] Response truncated due to length limit. Some picks may be missing!")
                        
                        # Clean DeepSeek R1 thinking blocks
                        import re
                        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                        
                        # Clean markdown
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
                        
                        
                        # --- BAD OUTPUT CIRCUIT BREAKER ---
                        if validate_json:
                            # Use robust extractor to find JSON amidst fluff
                            extracted_json = _extract_valid_json(content)
                            
                            if extracted_json:
                                content = extracted_json # Replace content with clean JSON
                            else:
                                logging.warning(f"[OpenRouter] Model {current_model} output contained no valid JSON. Treating as failure.")
                                model_failures[current_model] += 1
                                continue # Skip to next model

                        # Reset failures on success
                        model_failures[current_model] = 0
                        logging.info(f"[OpenRouter] Success with {current_model}")
                        return content.strip()
                    else:
                        logging.warning(f"[OpenRouter] No choices from {current_model}")
                        model_failures[current_model] += 1

                else:
                    # Non-200 status (and not handled above)
                    pass

            except requests.exceptions.Timeout:
                logging.warning(f"[OpenRouter] Timeout with {current_model}")
                model_failures[current_model] += 1
                
            except requests.exceptions.RequestException as e:
                logging.warning(f"[OpenRouter] Request error with {current_model}: {e}")
                model_failures[current_model] += 1
                
            except Exception as e:
                logging.error(f"[OpenRouter] Unexpected error with {current_model}: {e}")
                model_failures[current_model] += 1
            
            # --- CIRCUIT BREAKER CHECK ---
            # If model failed too many times (e.g., 3), blacklist it for this run
            if model_failures[current_model] >= 3:
                logging.warning(f"[OpenRouter] {current_model} reached failure threshold (3). Blacklisting temporarily.")
                blacklisted_models.add(current_model)
        
        # If we completed a cycle without success, wait with exponential backoff
        if cycle < max_cycles - 1:
            wait_time = _get_backoff_delay(cycle, RETRY_CONFIG["cycle_delay"], RETRY_CONFIG["max_delay"])
            logging.info(f"[OpenRouter] Cycle {cycle+1} complete, waiting {wait_time:.1f}s before retry...")
            time.sleep(wait_time)
    
    # All cycles exhausted
    logging.error(f"[OpenRouter] All {max_cycles} cycles failed.")
    raise Exception("All API attempts failed after exhaustively retrying models.")


def _single_model_request(model, prompt, images, headers, timeout):
    """
    Make a single request to one model. Used for parallel execution.
    Returns (model, result, error).
    """
    content_payload = [{"type": "text", "text": prompt}]
    
    if images:
        for img_item in images:
            try:
                # Support both file paths and base64 strings
                if isinstance(img_item, str) and (os.path.exists(img_item) or len(img_item) < 1000):
                    # It's a file path
                    with open(img_item, "rb") as f:
                        b64_img = base64.b64encode(f.read()).decode("utf-8")
                else:
                    # Assume it's already base64 string
                    b64_img = img_item
                    
                content_payload.append({
                    "type": "image_url", 
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                })
            except Exception as e:
                logging.error(f"[OpenRouter] Failed to load image: {e}")
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "provider": {
            "sort": "throughput"  # Route to fastest available provider
        }
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 429:
            # Quick retry loop for rate limits
            for retry_attempt in range(3):
                retry_after = int(response.headers.get("Retry-After", 0))
                wait_time = max(retry_after, 2 ** (retry_attempt + 1))
                time.sleep(wait_time)
                try:
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=timeout
                    )
                    if response.status_code != 429:
                        break
                except Exception:
                    break

        if response.status_code == 429:
            return (model, None, "rate_limited")
        
        if response.status_code in (503, 502, 500):
            return (model, None, f"server_error_{response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        if 'choices' in data and len(data['choices']) > 0:
            content = data['choices'][0]['message']['content']
            
            # Clean DeepSeek R1 thinking blocks
            import re
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            
            # Clean markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            content = content.strip()
            if content and content[0] not in '{[':
                for i, c in enumerate(content):
                    if c == '{' or c == '[':
                        content = content[i:]
                        break
            
            return (model, content.strip(), None)
        else:
            return (model, None, "no_choices")
            
    except requests.exceptions.Timeout:
        return (model, None, "timeout")
    except Exception as e:
        return (model, None, str(e))


def openrouter_parallel_completion(prompt, models=None, timeout=120):
    """
    SEQUENTIAL (Optimized) text completion.
    Replaced wasteful "Race" logic with smart sequential retry.
    This saves requests while maintaining reliability.
    
    Args:
        prompt: The prompt to send
        models: List of models to try in order (default: FAST_PARSING_MODELS)
        timeout: Timeout per request
    
    Returns:
        The JSON content string from the first successful model.
    """
    if models is None:
        models = FAST_PARSING_MODELS
    
    # Just use standard completion which handles retries and fallbacks
    # But force the specific list of models we want for parsing
    return openrouter_completion(prompt, model=models[0], timeout=timeout)


def openrouter_parallel_vision(prompt, images, models=None, timeout=120):
    """
    SEQUENTIAL (Optimized) vision API call.
    Replaced wasteful "Race" logic with smart sequential retry.
    
    Args:
        prompt: The prompt to send
        images: List of image paths
        models: List of vision models to try (default: VISION_MODELS)
        timeout: Timeout per request
    
    Returns:
        The JSON content string from the first successful model.
    """
    if models is None:
        models = VISION_MODELS
    
    # Just use standard completion which handles retries and fallbacks
    # But force the specific list of models we want for vision
    return openrouter_completion(prompt, model=models[0], images=images, timeout=timeout)

