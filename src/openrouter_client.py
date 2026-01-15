import os
import requests
import json
import logging
import time
import base64
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Model fallback list (ordered by reliability)
# Updated with faster, high-performance models for competitive racing
DEFAULT_MODELS = [
    "google/gemini-2.0-flash-exp:free",      # Fast & High Rate Limits (Primary)
    "google/gemini-2.0-pro-exp-02-05:free",  # High Quality Fallback
    "meta-llama/llama-3.3-70b-instruct:free", # Reliable
    "mistralai/mistral-small-24b-instruct-2501:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]

# Models specifically for "Racing" (Parallel Text Parsing)
FAST_PARSING_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "google/gemini-2.0-pro-exp-02-05:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

# Vision-capable models for OCR
# Removed unstable/404/400 models
VISION_MODELS = [
    "google/gemini-2.0-flash-exp:free",      # Primary workhorse (Huge Context)
    "google/gemini-2.0-pro-exp-02-05:free",  # Secondary
    "google/gemma-3-12b-it:free",            # Fallback
    "qwen/qwen-2-vl-7b-instruct:free",       # Good alternative
]

# Retry configuration for free-tier resilience
RETRY_CONFIG = {
    "max_cycles": 15,          # "Retry until it gets it" - significantly increased
    "base_delay": 1,           # Faster retry
    "cycle_delay": 2,          # Faster cycling
    "max_delay": 15,           
    "jitter": 0.1,             
}

def _get_backoff_delay(attempt, base=3, max_delay=60, jitter=0.3):
    """Calculate exponential backoff with jitter"""
    delay = min(base * (2 ** attempt), max_delay)
    jitter_range = delay * jitter
    delay += random.uniform(-jitter_range, jitter_range)
    return max(1, delay)


def openrouter_completion(prompt, model=None, images=None, timeout=180, max_cycles=None):
    """
    Calls OpenRouter API with aggressive retry logic for free-tier resilience.
    Implements a "Circuit Breaker" to temporarily avoid failing models.
    """
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
                "response_format": {"type": "json_object"}
            }

            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                
                # --- ERROR HANDLING & CIRCUIT BREAKER ---
                
                # 1. Critical Client Errors (400 Bad Request, 404 Not Found)
                # These imply the model name is invalid or query is bad -> Blacklist immediately
                if response.status_code in (400, 404):
                    logging.error(f"[OpenRouter] {current_model} returned {response.status_code} (Client Error). Blacklisting model.")
                    blacklisted_models.add(current_model)
                    last_error = Exception(f"Model {current_model} error {response.status_code}")
                    continue

                # 2. Rate Limits (429) -> Retry same model carefully
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 0))
                    backoff = _get_backoff_delay(cycle, RETRY_CONFIG["base_delay"], RETRY_CONFIG["max_delay"])
                    wait_time = max(retry_after, backoff)
                    logging.warning(f"[OpenRouter] 429 Rate Limit from {current_model}. Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    
                    # One immediate retry for 429
                    try:
                        response = requests.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers=headers,
                            json=payload,
                            timeout=timeout
                        )
                    except Exception:
                        pass # Fail through to standard check
                
                # 3. Server Errors (500, 502, 503) -> Count failure
                if response.status_code >= 500:
                    model_failures[current_model] += 1
                    logging.warning(f"[OpenRouter] {current_model} Server Error {response.status_code}. Failures: {model_failures[current_model]}")
                
                # Check for success
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        
                        # Clean DeepSeek R1 thinking blocks
                        import re
                        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                        
                        # Clean markdown
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
                        
                        # Verify JSON structure loosely
                        content = content.strip()
                        if content and content[0] not in '{[':
                             # Try to find JSON block manually
                            json_start = None
                            for i, c in enumerate(content):
                                if c == '{' or c == '[':
                                    json_start = i
                                    break
                            if json_start is not None:
                                content = content[json_start:]
                        
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
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
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

