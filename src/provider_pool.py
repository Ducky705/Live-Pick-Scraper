"""
Hybrid Provider Pool - MAXIMUM SPEED Strategy

This module orchestrates API calls across multiple providers:
- Tier 1 (PRIMARY): Groq - 1000 RPM, 16 concurrent workers
- Tier 2 (SECONDARY): Mistral - 60 RPM, 4 workers, batch 10 msgs/call
- Tier 3 (TERTIARY): Gemini - 15 RPM, 3 workers, batch 5 msgs/call
- Tier 4 (OVERFLOW): Cerebras - 30 RPM, 2 workers
- Tier 5 (FALLBACK ONLY): OpenRouter - 3-120s latency, NOT recommended

Logic:
1. Route 80%+ of load to Groq (fastest, highest RPM)
2. Use Mistral/Gemini/Cerebras for overflow
3. OpenRouter ONLY if ALL fast providers fail
"""

import os
import logging
import time
import random
import json
from threading import Lock, Semaphore
from concurrent.futures import ThreadPoolExecutor, as_completed, FIRST_COMPLETED, wait
from typing import Optional, List, Dict, Any

from src.cerebras_client import (
    cerebras_completion,
    DEFAULT_TEXT_MODEL as CEREBRAS_MODEL,
)
from src.groq_client import (
    groq_vision_completion,
    groq_text_completion,
    DEFAULT_TEXT_MODEL as GROQ_TEXT_MODEL,
    DEFAULT_VISION_MODEL as GROQ_VISION_MODEL,
)
from src.mistral_client import (
    mistral_completion,
    DEFAULT_TEXT_MODEL as MISTRAL_TEXT_MODEL,
    DEFAULT_VISION_MODEL as MISTRAL_VISION_MODEL,
)
from src.prompts.decoder import expand_compact_pick

# --- CONFIGURATION ---

# Strong fallback model (OpenRouter) - ONLY used when all fast providers fail
# Switched to Llama 3.3 70b Free for better reliability (Gemini was throwing 400s)
STRONG_FALLBACK_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

# Rate Limits - MAXIMUM SPEED configuration (Updated 2026-01-22)
# Based on actual provider rate limits from user data
LIMITS = {
    "groq": Semaphore(1),  # Stricter limit (1 concurrent) to prevent 429s
    "mistral": Semaphore(2),
    "gemini": Semaphore(1),
    "cerebras": Semaphore(1),
}

# Provider Availability Flags
AVAILABILITY = {
    "groq": True,  # PRIMARY - 1000 RPM
    "mistral": True,  # SECONDARY - 60 RPM
    "gemini": True,  # TERTIARY - 15 RPM
    "cerebras": True,  # OVERFLOW - 30 RPM
}

# Backoff timers for when a provider hits 429
COOLDOWN = {
    "groq": 0,
    "mistral": 0,
    "gemini": 0,
    "cerebras": 0,
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
        logging.warning(
            f"[HybridPool] {provider} hit rate limit. Cooldown for {wait_seconds}s."
        )


def _validate_json_response(response: str) -> bool:
    """Check if response is valid JSON."""
    if not response:
        return False
    try:
        parsed = json.loads(response)
        # Check for meaningful content (not just empty object/array)
        if isinstance(parsed, dict):
            return len(parsed) > 0 or "picks" in parsed
        if isinstance(parsed, list):
            return True  # Even empty list is valid (no picks found)
        return False
    except json.JSONDecodeError:
        return False


def _calculate_quality_score(response: str) -> tuple[float, list[str]]:
    """
    Calculate quality score for a parsed response.

    Returns:
        (score: 0.0-1.0, issues: list of problem descriptions)

    Quality checks:
    1. Missing/Unknown capper names
    2. Missing/Unknown leagues
    3. Missing/Unknown pick values
    4. Missing odds (acceptable but tracked)
    5. Suspicious patterns (marketing text, watermarks)
    """
    issues = []

    if not response:
        return 0.0, ["Empty response"]

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return 0.0, ["Invalid JSON"]

    # Extract picks array
    picks = []
    if isinstance(parsed, dict):
        picks = parsed.get("picks", [])
    elif isinstance(parsed, list):
        picks = parsed

    if not picks:
        return 1.0, []  # Empty picks is valid (no picks found in message)

    total_picks = len(picks)
    quality_issues = {
        "unknown_capper": 0,
        "unknown_league": 0,
        "unknown_pick": 0,
        "missing_odds": 0,
        "suspicious_capper": 0,
        "invalid_type": 0,
    }

    # Suspicious patterns for capper names
    SUSPICIOUS_CAPPERS = [
        "unknown",
        "n/a",
        "na",
        "none",
        "cappersfree",
        "@cappersfree",
        "whale plays",
        "vip",
        "free play",
        "potd",
        "lock",
    ]

    VALID_TYPES = [
        "moneyline",
        "spread",
        "total",
        "player prop",
        "team prop",
        "game prop",
        "period",
        "parlay",
        "teaser",
        "future",
        "unknown",
    ]

    for pick in picks:
        # Expand compact keys (c->capper_name, etc.) for validation
        full_pick = expand_compact_pick(pick)

        # Check capper name (capper_name)
        cn = str(full_pick.get("capper_name", "") or "").strip().lower()
        if not cn or cn in ["unknown", "n/a", "none", ""]:
            quality_issues["unknown_capper"] += 1
        elif cn in SUSPICIOUS_CAPPERS:
            quality_issues["suspicious_capper"] += 1

        # Check league (league)
        lg = str(full_pick.get("league", "") or "").strip().lower()
        if not lg or lg in ["unknown", "n/a", "none", "", "other"]:
            quality_issues["unknown_league"] += 1

        # Check pick value (pick)
        p = str(full_pick.get("pick", "") or "").strip().lower()
        if not p or p in ["unknown", "n/a", "none", ""]:
            quality_issues["unknown_pick"] += 1

        # Check type (type)
        ty = str(full_pick.get("type", "") or "").strip().lower()
        if ty and ty not in VALID_TYPES:
            # Check if it matches abbreviations (though expand_compact_pick handles this)
            quality_issues["invalid_type"] += 1

        # Track missing odds (not penalized heavily)
        if full_pick.get("odds") is None:
            quality_issues["missing_odds"] += 1

    # Calculate score (weighted)
    # Critical fields: capper, pick (heavy penalty)
    # Important fields: league, type (medium penalty)
    # Optional fields: odds (light penalty)

    critical_failures = (
        quality_issues["unknown_capper"]
        + quality_issues["unknown_pick"]
        + quality_issues["suspicious_capper"]
    )
    important_failures = (
        quality_issues["unknown_league"] + quality_issues["invalid_type"]
    )

    # Score calculation
    critical_penalty = (critical_failures / total_picks) * 0.5  # Up to 50% penalty
    important_penalty = (important_failures / total_picks) * 0.3  # Up to 30% penalty

    score = max(0.0, 1.0 - critical_penalty - important_penalty)

    # Build issue descriptions
    if quality_issues["unknown_capper"] > 0:
        issues.append(
            f"{quality_issues['unknown_capper']}/{total_picks} picks have unknown capper"
        )
    if quality_issues["suspicious_capper"] > 0:
        issues.append(
            f"{quality_issues['suspicious_capper']}/{total_picks} picks have suspicious capper (watermark?)"
        )
    if quality_issues["unknown_pick"] > 0:
        issues.append(
            f"{quality_issues['unknown_pick']}/{total_picks} picks have unknown pick value"
        )
    if quality_issues["unknown_league"] > 0:
        issues.append(
            f"{quality_issues['unknown_league']}/{total_picks} picks have unknown league"
        )
    if quality_issues["invalid_type"] > 0:
        issues.append(
            f"{quality_issues['invalid_type']}/{total_picks} picks have invalid type"
        )

    return score, issues


# Quality threshold for triggering fallback
QUALITY_THRESHOLD = 0.7  # If score < 70%, trigger fallback


def _get_fast_providers(task_type: str = "text") -> List[Dict[str, Any]]:
    """
    Get list of available fast providers for a task.
    PRIORITY ORDER: Groq (PRIMARY) > Mistral > Cerebras (text only)
    Returns list of dicts with provider name and model.
    """
    candidates = []

    if task_type == "text":
        # Text Providers: Groq FIRST (1000 RPM), then Cerebras (Faster/Better), then Mistral
        if os.getenv("GROQ_TOKEN") and _is_available("groq"):
            candidates.append({"name": "groq", "model": GROQ_TEXT_MODEL, "priority": 1})
        if os.getenv("CEREBRAS_TOKEN") and _is_available("cerebras"):
            candidates.append(
                {"name": "cerebras", "model": CEREBRAS_MODEL, "priority": 2}
            )
        if os.getenv("MISTRAL_TOKEN") and _is_available("mistral"):
            candidates.append(
                {"name": "mistral", "model": MISTRAL_TEXT_MODEL, "priority": 3}
            )

    elif task_type == "vision":
        # Vision Providers: Groq, Mistral (Cerebras is text-only)
        if os.getenv("GROQ_TOKEN") and _is_available("groq"):
            candidates.append(
                {"name": "groq", "model": GROQ_VISION_MODEL, "priority": 1}
            )
        if os.getenv("MISTRAL_TOKEN") and _is_available("mistral"):
            candidates.append(
                {"name": "mistral", "model": MISTRAL_VISION_MODEL, "priority": 2}
            )

    # Sort by priority (Groq first), NO random shuffle for MAXIMUM SPEED
    candidates.sort(key=lambda x: x.get("priority", 99))

    return candidates


def _execute_fast_request(
    provider: str, prompt: str, images: Optional[List[str]] = None, timeout: int = 60
) -> Optional[str]:
    """Execute the request against a specific fast provider."""
    try:
        if provider == "cerebras":
            return cerebras_completion(prompt, timeout=timeout)

        elif provider == "groq":
            if images:
                img_input = images[0] if isinstance(images, list) else images
                return groq_vision_completion(prompt, img_input, timeout=timeout)
            else:
                return groq_text_completion(prompt, timeout=timeout)

        elif provider == "mistral":
            img_input = None
            if images:
                img_input = images[0] if isinstance(images, list) else images
            return mistral_completion(prompt, image_input=img_input, timeout=timeout)

    except Exception as e:
        if "429" in str(e):
            raise e  # Propagate rate limit to caller
        logging.error(f"[HybridPool] Error executing {provider}: {e}")
        return None

    return None


def _attempt_provider_execution(
    provider_name: str,
    model: str,
    prompt: str,
    images: Optional[List[str]],
    timeout: int,
) -> tuple[Optional[str], float]:
    """
    Helper to execute a provider request with semaphore handling.
    Returns: (result_string_or_None, quality_score)
    """
    if not _is_available(provider_name):
        return None, 0.0

    sem = LIMITS.get(provider_name)
    if not sem:
        return None, 0.0

    if not sem.acquire(blocking=False):
        return None, 0.0

    try:
        # Double check
        if not _is_available(provider_name):
            return None, 0.0

        logging.info(f"[HybridPool] Trying {provider_name} ({model})...")
        start_t = time.time()
        result = _execute_fast_request(provider_name, prompt, images, timeout)
        duration = time.time() - start_t

        if result:
            if not _validate_json_response(result):
                logging.warning(f"[HybridPool] {provider_name} invalid JSON.")
                return None, 0.0

            score, issues = _calculate_quality_score(result)
            if score >= QUALITY_THRESHOLD:
                logging.info(
                    f"[HybridPool] {provider_name} success in {duration:.2f}s (quality: {score:.0%})"
                )
                return result, score
            else:
                logging.warning(
                    f"[HybridPool] {provider_name} low quality ({score:.0%}). Issues: {issues}"
                )
                return result, score  # Return as fallback candidate
        else:
            return None, 0.0

    except Exception as e:
        if "429" in str(e):
            _mark_rate_limited(provider_name, wait_seconds=30)
        logging.error(f"[HybridPool] Error with {provider_name}: {e}")
        return None, 0.0
    finally:
        sem.release()


def pooled_completion(
    prompt: str,
    images: Optional[List[str]] = None,
    timeout: int = 60,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    require_accuracy: bool = False,
) -> Optional[str]:
    """
    Main entry point for Hybrid Provider Pool.

    Strategy:
    1. If `model` is specified, route directly to OpenRouter (bypass pool)
    2. If `provider` is specified, force that specific provider
    3. Otherwise, try Fast providers first, then fallback to OpenRouter

    Args:
        prompt: The prompt to send
        images: Optional list of image paths or base64 strings
        timeout: Request timeout in seconds
        model: Specific OpenRouter model to use (bypasses pool)
        provider: Force a specific local provider
        require_accuracy: If True, skip fast tier and go directly to OpenRouter

    Returns:
        Response string or None if all attempts fail
    """
    task_type = "vision" if images else "text"

    # --- BYPASS: Specific model requested ---
    if model:
        try:
            from src.openrouter_client import openrouter_completion

            logging.info(f"[HybridPool] Bypassing pool for specific model: {model}")
            return openrouter_completion(
                prompt, model=model, images=images, timeout=timeout
            )
        except Exception as e:
            logging.error(f"[HybridPool] OpenRouter failed for model {model}: {e}")
            return None

    # --- BYPASS: Accuracy mode (skip fast tier) ---
    if require_accuracy:
        logging.info(f"[HybridPool] Accuracy mode: Routing directly to DeepSeek R1")
        try:
            from src.openrouter_client import openrouter_completion

            return openrouter_completion(
                prompt, model=STRONG_FALLBACK_MODEL, images=images, timeout=timeout
            )
        except Exception as e:
            logging.error(f"[HybridPool] OpenRouter (accuracy mode) failed: {e}")
            return None

    # --- FORCE PROVIDER ---
    if provider:
        if provider not in LIMITS:
            logging.error(f"[HybridPool] Unknown provider: {provider}")
            return None

        logging.info(f"[HybridPool] Forcing execution on {provider}...")

        sem = LIMITS[provider]
        acquired = sem.acquire(timeout=5)
        if not acquired:
            logging.warning(f"[HybridPool] Provider {provider} is busy (timeout).")
            return None

        try:
            return _execute_fast_request(provider, prompt, images, timeout)
        finally:
            sem.release()

    # --- HYBRID STRATEGY: Fast First, Then Fallback ---
    candidates = _get_fast_providers(task_type)
    _last_fast_result = None  # Store best fast result in case OpenRouter fails

    if not candidates:
        logging.warning(
            f"[HybridPool] No fast providers available for {task_type}. Going to OpenRouter."
        )
    else:
        # --- ITERATION 17: PARALLEL SPECULATION ---
        # Try top 2 providers simultaneously to minimize latency.

        speculative_batch = candidates[:2]
        remaining_candidates = candidates[2:]

        # 1. Speculative Phase (Top 2)
        if speculative_batch:
            logging.info(
                f"[HybridPool] Speculative execution: {[p['name'] for p in speculative_batch]}"
            )

            with ThreadPoolExecutor(max_workers=len(speculative_batch)) as executor:
                futures = {
                    executor.submit(
                        _attempt_provider_execution,
                        p["name"],
                        p["model"],
                        prompt,
                        images,
                        timeout,
                    ): p["name"]
                    for p in speculative_batch
                }

                # Wait for FIRST completion
                done, not_done = wait(futures.keys(), return_when=FIRST_COMPLETED)

                # Check if the first one was successful
                for f in done:
                    res, score = f.result()
                    if res and score >= QUALITY_THRESHOLD:
                        logging.info(f"[HybridPool] Speculative WINNER: {futures[f]}")
                        return res
                    if res:
                        _last_fast_result = res

                # If first one failed, wait for the rest (gracefully)
                if not_done:
                    logging.info(
                        "[HybridPool] First speculative failed, waiting for others..."
                    )
                    done2, _ = wait(not_done, timeout=timeout)
                    for f in done2:
                        res, score = f.result()
                        if res and score >= QUALITY_THRESHOLD:
                            logging.info(
                                f"[HybridPool] Speculative RECOVERY: {futures[f]}"
                            )
                            return res
                        if res:
                            _last_fast_result = res

        # 2. Sequential Phase (Remaining)
        if remaining_candidates:
            logging.info(
                "[HybridPool] Speculative phase failed. Trying remaining providers sequentially..."
            )
            for provider_info in remaining_candidates:
                res, score = _attempt_provider_execution(
                    provider_info["name"],
                    provider_info["model"],
                    prompt,
                    images,
                    timeout,
                )
                if res and score >= QUALITY_THRESHOLD:
                    return res
                if res:
                    _last_fast_result = res

    # --- FALLBACK: OpenRouter (DeepSeek R1) ---
    logging.info(
        f"[HybridPool] Fast tier failed/low-quality. Falling back to OpenRouter (DeepSeek R1)..."
    )

    try:
        from src.openrouter_client import openrouter_completion

        result = openrouter_completion(
            prompt, model=STRONG_FALLBACK_MODEL, images=images, timeout=timeout
        )

        if result and _validate_json_response(result):
            # Check quality of OpenRouter response too
            or_quality, or_issues = _calculate_quality_score(result)
            logging.info(
                f"[HybridPool] OpenRouter fallback success (quality: {or_quality:.0%})."
            )
            return result
        else:
            logging.error(
                f"[HybridPool] OpenRouter fallback returned invalid response."
            )
            # Return the best fast result we had, if any
            if _last_fast_result:
                logging.info(
                    f"[HybridPool] Returning last fast-tier result as fallback."
                )
                return _last_fast_result
            return result  # Return anyway, let caller handle

    except Exception as e:
        logging.error(f"[HybridPool] OpenRouter fallback failed: {e}")
        return None
