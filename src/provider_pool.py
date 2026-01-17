
import os
import logging
import time
import random
import json
from threading import Lock, Semaphore
from typing import Optional, List, Dict, Any

from src.cerebras_client import cerebras_completion
from src.groq_client import groq_vision_completion
from src.mistral_client import mistral_completion

# --- CONFIGURATION ---

# Rate Limits (Conservative estimates for free tiers)
# We limit CONCURRENT requests to avoid 429s
LIMITS = {
    "cerebras": Semaphore(2), # 2 concurrent requests
    "groq": Semaphore(1),     # 1 concurrent request (very strict)
    "mistral": Semaphore(2),  # 2 concurrent requests
}

# Provider Availability Flags (can be toggled at runtime if 429s occur)
AVAILABILITY = {
    "cerebras": True,
    "groq": True,
    "mistral": True
}

# Backoff timers for when a provider hits 429
COOLDOWN = {
    "cerebras": 0,
    "groq": 0,
    "mistral": 0
}

PROVIDER_LOCK = Lock()

def _is_available(provider: str) -> bool:
    """Check if provider is marked available and cooldown has passed."""
    with PROVIDER_LOCK:
        if not AVAILABILITY.get(provider, False):
            return False
        if time.time() < COOLDOWN.get(provider, 0):
            return False
        return True

def _mark_rate_limited(provider: str, wait_seconds: int = 10):
    """Mark a provider as rate limited for a cooldown period."""
    with PROVIDER_LOCK:
        COOLDOWN[provider] = int(time.time() + wait_seconds)
        logging.warning(f"[ProviderPool] {provider} hit Rate Limit. Cooldown for {wait_seconds}s.")

def _get_provider_for_task(task_type: str = "text") -> List[str]:
    """
    Get list of available providers for a task, shuffled for load balancing.
    task_type: "text" or "vision"
    """
    candidates = []
    
    if task_type == "text":
        # Text Providers: Cerebras (Fast), Mistral (Reliable)
        if os.getenv("CEREBRAS_TOKEN") and _is_available("cerebras"):
            candidates.append("cerebras")
        if os.getenv("MISTRAL_TOKEN") and _is_available("mistral"):
            candidates.append("mistral")
        # Groq text could be added
        
    elif task_type == "vision":
        # Vision Providers: Mistral (Pixtral), Groq (Llama Vision)
        if os.getenv("MISTRAL_TOKEN") and _is_available("mistral"):
            candidates.append("mistral")
        if os.getenv("GROQ_TOKEN") and _is_available("groq"):
            candidates.append("groq")
            
    # Shuffle for Random Load Balancing (Round-Robin approximation)
    random.shuffle(candidates)
    
    return candidates

def _execute_request(provider: str, prompt: str, images: Optional[List[str]] = None, timeout: int = 60):
    """Execute the request against the specific provider client."""
    try:
        if provider == "cerebras":
            return cerebras_completion(prompt, timeout=timeout)
            
        elif provider == "mistral":
            # Mistral handles both text and vision
            # If images is list, take first one (Mistral client currently optimized for single image or list handling needs verification)
            # The mistral_client we wrote handles list of images? No, it handles `image_input`.
            # We need to adapt the interface.
            img_input = None
            if images:
                img_input = images[0] # Take first image
            return mistral_completion(prompt, image_input=img_input, timeout=timeout)
            
        elif provider == "groq":
            if images:
                # Vision
                img_input = images[0]
                # Groq client expects a specific JSON prompt structure sometimes?
                # The groq_client.py we read earlier takes `prompt` and `image_input`.
                return groq_vision_completion(prompt, img_input, timeout=timeout)
            else:
                # Text (Not yet implemented in groq_client but could be)
                return None
                
    except Exception as e:
        logging.error(f"[ProviderPool] Error executing {provider}: {e}")
        return None

def pooled_completion(prompt: str, images: Optional[List[str]] = None, timeout: int = 60) -> Optional[str]:
    """
    Main entry point. Dispatches to best available provider.
    Retries on other providers if one fails.
    """
    task_type = "vision" if images else "text"
    candidates = _get_provider_for_task(task_type)
    
    if not candidates:
        logging.warning(f"[ProviderPool] No local providers available for {task_type}. Returning None (Caller should fallback to OpenRouter).")
        return None
        
    # Try candidates in order
    for provider in candidates:
        # Acquire semaphore for this provider
        sem = LIMITS.get(provider)
        if not sem: continue
        
        acquired = sem.acquire(blocking=False)
        if not acquired:
            # Provider is busy, skip to next (Load Balancing by skipping busy ones)
            logging.info(f"[ProviderPool] {provider} is busy (Max Concurrent). Skipping.")
            continue
            
        try:
            logging.info(f"[ProviderPool] Dispatching {task_type} task to {provider}...")
            start_t = time.time()
            result = _execute_request(provider, prompt, images, timeout)
            duration = time.time() - start_t
            
            if result:
                logging.info(f"[ProviderPool] {provider} success in {duration:.2f}s")
                return result
            else:
                logging.warning(f"[ProviderPool] {provider} returned None/Failed.")
                # If it failed quickly, might be a 429 caught inside client?
                # The clients usually handle their own retries, so if they return None, it's a hard fail.
                pass
                
        except Exception as e:
            logging.error(f"[ProviderPool] Unexpected error with {provider}: {e}")
        finally:
            sem.release()
            
    logging.warning("[ProviderPool] All local providers failed or were busy.")
    return None

