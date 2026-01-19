
import os
import logging
import time
import random
import json
from threading import Lock, Semaphore
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any

from src.cerebras_client import cerebras_completion
from src.groq_client import groq_vision_completion
from src.mistral_client import mistral_completion, PIXTRAL_12B
from src.openrouter_client import openrouter_completion

# --- CONFIGURATION ---

# Rate Limits (Conservative estimates for free tiers)
LIMITS = {
    "cerebras": Semaphore(3),
    "groq": Semaphore(2),
    "mistral": Semaphore(3),
    "openrouter": Semaphore(10)  # OpenRouter handles its own limits too, allow high concurrency here
}

# Provider Availability Flags
AVAILABILITY = {
    "cerebras": True,
    "groq": True,
    "mistral": True,
    "openrouter": True
}

# Backoff timers
COOLDOWN = {
    "cerebras": 0,
    "groq": 0,
    "mistral": 0,
    "openrouter": 0
}

PROVIDER_LOCK = Lock()

def _is_available(provider: str) -> bool:
    with PROVIDER_LOCK:
        if not AVAILABILITY.get(provider, False):
            return False
        if time.time() < COOLDOWN.get(provider, 0):
            return False
        return True

def _mark_rate_limited(provider: str, wait_seconds: int = 10):
    with PROVIDER_LOCK:
        COOLDOWN[provider] = int(time.time() + wait_seconds)
        logging.warning(f"[ProviderPool] {provider} hit Rate Limit. Cooldown for {wait_seconds}s.")

def _get_providers_for_task(task_type: str = "text") -> List[str]:
    candidates = []
    
    # Always include OpenRouter as the robust baseline
    if _is_available("openrouter"):
        candidates.append("openrouter")

    if task_type == "text":
        if os.getenv("CEREBRAS_TOKEN") and _is_available("cerebras"):
            candidates.append("cerebras")
        if os.getenv("MISTRAL_TOKEN") and _is_available("mistral"):
            candidates.append("mistral")
        
    elif task_type == "vision":
        if os.getenv("MISTRAL_TOKEN") and _is_available("mistral"):
            candidates.append("mistral")
        # Groq Vision often fails or has limits, but we can try it if enabled
        if os.getenv("GROQ_TOKEN") and _is_available("groq"):
            candidates.append("groq")
            
    # Randomize order (though we race them, so order matters less, but helps distribution)
    random.shuffle(candidates)
    return candidates

def _execute_request_safe(provider: str, prompt: str, images: Optional[List[str]], timeout: int):
    """Executes request with semaphore acquisition."""
    sem = LIMITS.get(provider)
    if not sem: return None

    # Acquire semaphore
    if not sem.acquire(blocking=True, timeout=10): # Short timeout to wait for slot
        logging.warning(f"[ProviderPool] Could not acquire slot for {provider}")
        return None

    try:
        # Check availability again just in case
        if not _is_available(provider):
            return None

        logging.info(f"[ProviderPool] Starting {provider}...")
        start_t = time.time()
        
        result = None
        if provider == "cerebras":
            result = cerebras_completion(prompt, timeout=timeout)
        elif provider == "mistral":
            img_input = images[0] if images else None
            if img_input:
                # Use Pixtral for vision tasks
                result = mistral_completion(prompt, model=PIXTRAL_12B, image_input=img_input, timeout=timeout)
            else:
                # Use default (Mistral Small/Large) for text
                result = mistral_completion(prompt, image_input=None, timeout=timeout)
        elif provider == "groq":
            if images:
                result = groq_vision_completion(prompt, images[0], timeout=timeout)
            else:
                return None # Groq text not impl here
        elif provider == "openrouter":
            result = openrouter_completion(prompt, images=images, timeout=timeout)
            
        duration = time.time() - start_t
        if result:
            logging.info(f"[ProviderPool] {provider} SUCCEEDED in {duration:.2f}s")
            return result
        else:
            logging.warning(f"[ProviderPool] {provider} returned empty/failed")
            return None

    except Exception as e:
        logging.error(f"[ProviderPool] Error in {provider}: {e}")
        return None
    finally:
        sem.release()

def pooled_completion(prompt: str, images: Optional[List[str]] = None, timeout: int = 60) -> Optional[str]:
    """
    Race multiple providers in parallel. Return the first successful result.
    """
    task_type = "vision" if images else "text"
    candidates = _get_providers_for_task(task_type)
    
    if not candidates:
        logging.warning(f"[ProviderPool] No providers available for {task_type}")
        return None
        
    logging.info(f"[ProviderPool] Racing providers: {', '.join(candidates)}")
    
    with ThreadPoolExecutor(max_workers=len(candidates)) as executor:
        futures = {
            executor.submit(_execute_request_safe, p, prompt, images, timeout): p 
            for p in candidates
        }
        
        # Wait for FIRST_COMPLETED success
        # We iterate as they complete. If one succeeds, we return immediately.
        for future in as_completed(futures):
            provider = futures[future]
            try:
                result = future.result()
                if result:
                    # We got a winner!
                    return result
            except Exception as e:
                logging.error(f"[ProviderPool] Top-level error for {provider}: {e}")
                
    logging.error("[ProviderPool] All providers failed.")
    return None
