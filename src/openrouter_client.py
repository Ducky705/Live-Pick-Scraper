import os
import requests
import json
import logging
import time
import base64
from pathlib import Path

# Model fallback list (ordered by reliability)
DEFAULT_MODELS = [
    "tngtech/deepseek-r1t2-chimera:free",
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/devstral-2512:free",
    "google/gemma-3-27b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "z-ai/glm-4.5-air:free",
]

def openrouter_completion(prompt, model=None, images=None, timeout=180, max_cycles=2):
    """
    Calls OpenRouter API with retry logic and model fallback.
    
    Args:
        prompt: The prompt to send
        model: Primary model to use (will be first in fallback list)
        images: Optional list of image paths (str or Path) to include in the request
        timeout: Timeout in seconds per request (default 3 minutes)
        max_cycles: Number of times to cycle through all models before giving up
    
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
            
            # Construct Content
            content_payload = [{"type": "text", "text": prompt}]
            
            if images:
                for img_path in images:
                    try:
                        with open(img_path, "rb") as f:
                            b64_img = base64.b64encode(f.read()).decode("utf-8")
                            content_payload.append({
                                "type": "image_url", 
                                "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                            })
                    except Exception as e:
                        logging.error(f"[OpenRouter] Failed to load image {img_path}: {e}")

            # If only text, simplify structure for compatibility? 
            # Most Vision capable models support array content.
            # But non-vision models might prefer string content.
            # Let's check if we have images.
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
                    timeout=timeout  # 3 minute timeout
                )
                response.raise_for_status()
                
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    
                    # Clean DeepSeek R1 thinking blocks (they wrap reasoning in <think>...</think>)
                    import re
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                    
                    # Clean markdown code blocks if present
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    
                    # Fallback: Find JSON object/array if there's extra text
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

