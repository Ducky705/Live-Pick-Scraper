import logging
import os
import time

import requests

DEFAULT_MODELS = [
    "stepfun/step-3.5-flash:free",            # PRIMARY: The "Unicorn" (95.3% Recall @ BS=5)
    "meta-llama/llama-3.3-70b-instruct:free", # SECONDARY: Reliable Baseline (81% Recall)
    "nvidia/llama-3.1-nemotron-70b-instruct:free", # TERTIARY: Last resort (57% Recall)
]




def openrouter_completion(prompt, model=None, timeout=180, max_cycles=2, images=None, validate_json=False):
    """
    Calls OpenRouter API with retry logic and model fallback.
    Supports Vision (images) if the model supports it.

    Args:
        prompt: The prompt to send
        model: Primary model to use (will be first in fallback list)
        timeout: Timeout in seconds per request (default 3 minutes)
        max_cycles: Number of times to cycle through all models before giving up
        images: List of base64 encoded image strings (optional)
        validate_json: Unused param for compatibility with other clients

    Returns:
        The JSON content string or raises an Exception after all retries fail.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram-scraper.local",
        "X-Title": "CapperSuite",
    }

    # Build model list
    models = []
    if model:
        # BENCHMARK MODE: If a specific model is requested, try ONLY that model first.
        # If max_cycles > 1, we could fallback, but for benchmarking we usually want strict adherence.
        # However, to be robust, we treat 'model' as the PRIMARY preference.
        models.append(model)
        
        # If the user specifically asks for a model not in our default list, 
        # we strictly prioritize it. But should we fallback?
        # Current logic: yes, fallback to defaults if primary fails.
    
    # Add defaults unique only if we haven't locked to a specific model for benchmarking
    # Strategy: If provided model fails, do we want to fallback? 
    # For production: YES. For benchmarking: NO.
    # Let's keep fallback behavior but ensure the requested model is ALWAYS first.
    for m in DEFAULT_MODELS:
        if m not in models:
            models.append(m)
            
    # CRITICAL CHANGE: If 'validate_json' is passed (used as a flag for "Strict Mode" in benchmarking),
    # or if we detect this is a benchmark run, we might want to disable fallback.
    # For now, we rely on the log to see which model actually responded.

    last_error = None

    for cycle in range(max_cycles):
        for current_model in models:
            # Inner Retry Loop for Rate Limits
            for attempt in range(3): # Try up to 3 times per model if 429s occur
                logging.info(f"[OpenRouter] Cycle {cycle + 1}/{max_cycles}, Model: {current_model} (Attempt {attempt + 1})")
    
                # Construct message content
                if images:
                    content_parts = [{"type": "text", "text": prompt}]
                    for b64_img in images:
                        url = f"data:image/jpeg;base64,{b64_img}" if not b64_img.startswith("data:") else b64_img
                        content_parts.append({"type": "image_url", "image_url": {"url": url}})
                    messages = [{"role": "user", "content": content_parts}]
                else:
                    messages = [{"role": "user", "content": prompt}]
    
                payload = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": 0.1,
                    # "response_format": {"type": "json_object"},
                }
    
                try:
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=timeout,  # 3 minute timeout
                    )
                    response.raise_for_status()
    
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        # Clean markdown code blocks if present
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
    
                        logging.info(f"[OpenRouter] Success with {current_model}")
                        return content.strip()
                    else:
                        last_error = Exception("No choices in response")
                        logging.warning(f"[OpenRouter] No choices from {current_model}")
                        break # Don't retry empty choices, move to next model
    
                except requests.exceptions.Timeout:
                    # US-002: Fail fast on timeout
                    raise requests.exceptions.Timeout(f"Timeout after {timeout}s with {current_model}")
    
                except requests.exceptions.RequestException as e:
                    # Log full error body if available
                    if hasattr(e, "response") and e.response is not None:
                        error_msg = e.response.text
                        status_code = e.response.status_code
                        
                        # Handle 429 Too Many Requests explicitly with "Patient Mode"
                        if status_code == 429:
                            logging.warning(f"[OpenRouter] Hit Rate Limit (429) on {current_model}.")
                            # PATIENT MODE: Wait and Retry THIS model
                            sleep_time = 60
                            logging.warning(f"[OpenRouter] Backing off for {sleep_time}s to let rate limit clear...")
                            time.sleep(sleep_time)
                            continue # Retry loop (attempt)
                        else:
                            logging.warning(f"[OpenRouter] Request error with {current_model}: {status_code} - {error_msg}")
                    else:
                        logging.warning(f"[OpenRouter] Request error with {current_model}: {e}")
    
                    last_error = e
                    # For non-429 errors, maybe we shouldn't retry? 
                    # Let's retry only on 429. For others, break to next model.
                    break 
    
                except Exception as e:
                    last_error = e
                    logging.error(f"[OpenRouter] Unexpected error with {current_model}: {e}")
                    break # Break to next model
            
            # If we returned, great. If we broke, we go to next model.

        # If we completed a cycle without success, log it
        if cycle < max_cycles - 1:
            logging.info(f"[OpenRouter] Cycle {cycle + 1} complete, retrying from beginning...")
            time.sleep(2)  # Brief pause before retrying

    # All cycles exhausted
    logging.error(f"[OpenRouter] All {max_cycles} cycles failed. Last error: {last_error}")
    raise last_error if last_error else Exception("All API attempts failed")
