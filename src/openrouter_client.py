import os
import requests
import json
import logging
import time
import base64

# Model fallback list (ordered by reliability)
# NOTE: OpenRouter is FALLBACK ONLY (3-120s latency, not recommended for speed)
DEFAULT_MODELS = [
    'mistralai/devstral-2512:free',
    'tngtech/deepseek-r1t2-chimera:free'
]

def openrouter_completion(prompt, model=None, images=None, timeout=180, max_cycles=2, validate_json=True):
    """
    Calls OpenRouter API with retry logic and model fallback.
    WARNING: OpenRouter has 3-120s latency - use as FALLBACK ONLY.
    
    Args:
        prompt: The prompt to send
        model: Primary model to use (will be first in fallback list)
        images: Optional list of image paths or base64 strings for vision
        timeout: Timeout in seconds per request (default 3 minutes)
        max_cycles: Number of times to cycle through all models before giving up
        validate_json: Whether to validate JSON response
    
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
        "X-Title": "CapperSuite"
    }

    # Build model list: specified model first, then fallbacks
    models = []
    if model:
        models.append(model)
    for m in DEFAULT_MODELS:
        if m not in models:
            models.append(m)

    last_error = None
    
    for cycle in range(max_cycles):
        for current_model in models:
            logging.info(f"[OpenRouter] Cycle {cycle+1}/{max_cycles}, Model: {current_model}")
            
            # Build message content (text or multimodal)
            if images:
                # Multimodal request with images
                content_parts = [{"type": "text", "text": prompt}]
                for img in images:
                    # Check if it's a file path or base64
                    if isinstance(img, str) and (len(img) < 1000 or os.path.exists(img)):
                        try:
                            with open(img, "rb") as f:
                                img_data = base64.b64encode(f.read()).decode("utf-8")
                        except Exception as e:
                            logging.error(f"[OpenRouter] Failed to read image: {e}")
                            continue
                    else:
                        img_data = img
                    
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                    })
                
                messages = [{"role": "user", "content": content_parts}]
            else:
                # Text-only request
                messages = [{"role": "user", "content": prompt}]
            
            payload = {
                "model": current_model,
                "messages": messages,
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }

            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout  # 3 minute timeout
                )
                response.raise_for_status()
                
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
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
                    
            except requests.exceptions.Timeout:
                last_error = Exception(f"Timeout after {timeout}s with {current_model}")
                logging.warning(f"[OpenRouter] Timeout with {current_model}, cycling to next...")
                continue
                
            except requests.exceptions.RequestException as e:
                last_error = e
                logging.warning(f"[OpenRouter] Request error with {current_model}: {e}")
                continue
                
            except Exception as e:
                last_error = e
                logging.error(f"[OpenRouter] Unexpected error with {current_model}: {e}")
                continue
        
        # If we completed a cycle without success, log it
        if cycle < max_cycles - 1:
            logging.info(f"[OpenRouter] Cycle {cycle+1} complete, retrying from beginning...")
            time.sleep(2)  # Brief pause before retrying
    
    # All cycles exhausted
    logging.error(f"[OpenRouter] All {max_cycles} cycles failed. Last error: {last_error}")
    raise last_error if last_error else Exception("All API attempts failed")

