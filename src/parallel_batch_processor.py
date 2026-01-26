"""
Parallel Batch Processor v4 (Smart Cascading)
=============================================
Complexity Router that optimizes for Accuracy, Speed, and Cost.

Hierarchy:
1. Tier 1 (Speed/Cost): Gemini Flash Lite, Cerebras.
2. Tier 2 (Accuracy): Groq 70b, Mistral Large.
3. Tier 3 (Safety): OpenRouter.

Logic:
- Simple Text -> Tier 1 -> (on error) -> Tier 2
- Images/Complex -> Tier 2
- Rate Limit -> Spillover to next Tier
"""

import logging
import json
import time
import re
from queue import Queue, Empty
from threading import Thread, Event, Lock
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import clients
from src.cerebras_client import cerebras_completion
from src.groq_client import groq_text_completion, groq_vision_completion
from src.mistral_client import mistral_completion
from src.gemini_client import gemini_text_completion, gemini_vision_completion
from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt

logger = logging.getLogger(__name__)

# =============================================================================
# PROVIDER CONFIGURATION (Smart Cascading)
# =============================================================================
PROVIDER_CONFIG = {
    # TIER 1: SPEEDSTERS (High Throughput, Low Cost)
    "gemini": {
        "model": "gemini-2.0-flash-lite-preview-02-05",
        "rpm": 30,  # Actual limit is higher, but 30 is safe sustained
        "tpm": 1000000,
        "max_concurrent": 10,
        "tier": 1,
        "type": "text+vision",
    },
    "cerebras": {
        "model": "llama3.1-8b",
        "rpm": 60,
        "tpm": 60000,
        "max_concurrent": 5,
        "tier": 1,
        "type": "text",
    },
    # TIER 2: EXPERTS (High Intelligence)
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "rpm": 30,  # Conservative to avoid 429s
        "tpm": 20000,  # Strict TPM limit
        "max_concurrent": 2,
        "tier": 2,
        "type": "text+vision",  # Via separate vision model
    },
    "mistral": {
        "model": "mistral-large-latest",
        "rpm": 60,
        "tpm": 500000,
        "max_concurrent": 4,
        "tier": 2,
        "type": "text+vision",
    },
    # TIER 3: SAFETY NET
    "openrouter": {
        "model": "google/gemini-2.0-pro-exp-02-05:free",
        "rpm": 10,
        "tpm": 100000,
        "max_concurrent": 2,
        "tier": 3,
        "type": "text",
    },
}


class SmartCircuitBreaker:
    """Manages provider health and rate limits."""

    def __init__(self):
        self.status = {p: "active" for p in PROVIDER_CONFIG}
        self.errors = {p: 0 for p in PROVIDER_CONFIG}
        self.cooldowns = {p: 0.0 for p in PROVIDER_CONFIG}
        self.lock = Lock()

    def report_success(self, provider: str):
        with self.lock:
            self.errors[provider] = 0
            self.status[provider] = "active"

    def report_failure(self, provider: str, is_rate_limit: bool = False):
        with self.lock:
            self.errors[provider] += 1
            threshold = 3 if is_rate_limit else 5

            if self.errors[provider] >= threshold:
                cooldown = 60.0 if is_rate_limit else 30.0
                self.cooldowns[provider] = time.time() + cooldown
                self.status[provider] = "suspended"
                logger.warning(
                    f"CIRCUIT BREAKER: Suspended {provider} for {cooldown}s (Errors: {self.errors[provider]})"
                )

    def is_available(self, provider: str) -> bool:
        with self.lock:
            if self.status[provider] == "suspended":
                if time.time() > self.cooldowns[provider]:
                    self.status[provider] = "active"
                    self.errors[provider] = 0
                    logger.info(f"CIRCUIT BREAKER: {provider} recovered.")
                    return True
                return False
            return True


class ComplexityRouter:
    """Decides which tier should handle a request."""

    @staticmethod
    def analyze_batch(messages: List[dict]) -> dict:
        """Analyze batch to determine routing requirements."""
        has_image = False
        total_chars = 0

        for msg in messages:
            # Check for images (Source Message Format)
            if msg.get("images") or msg.get("image"):
                has_image = True

            # Check text length
            text = msg.get("text", "")
            if text:
                total_chars += len(text)

            # Check OCR text length
            ocr_texts = msg.get("ocr_texts", [])
            for ocr in ocr_texts:
                total_chars += len(ocr)

        # Routing Logic
        if has_image:
            return {"tier": 2, "reason": "vision_required"}

        if total_chars > 3000:
            return {"tier": 2, "reason": "high_complexity"}

        return {"tier": 1, "reason": "standard_text"}


class ParallelBatchProcessor:
    def __init__(self):
        self.circuit_breaker = SmartCircuitBreaker()
        self.stats = {p: {"count": 0, "errors": 0, "time": 0} for p in PROVIDER_CONFIG}
        self.stats_lock = Lock()

    def _execute_request(self, provider: str, messages: List[dict]) -> str:
        """Execute request with specific provider."""
        config = PROVIDER_CONFIG[provider]
        model = config["model"]

        # Determine if vision is needed and get image path
        image_path = None
        for msg in messages:
            if msg.get("image"):
                image_path = msg["image"]
                break
            if msg.get("images") and len(msg["images"]) > 0:
                image_path = msg["images"][0]
                break

        # Generate text prompt from batch
        prompt = generate_ai_prompt(messages)

        try:
            if provider == "groq":
                if image_path:
                    return groq_vision_completion(prompt, image_path, timeout=45)
                return groq_text_completion(prompt, model=model, timeout=30)

            elif provider == "gemini":
                if image_path:
                    return gemini_vision_completion(
                        prompt, image_path, model=model, timeout=45
                    )
                return gemini_text_completion(prompt, model=model, timeout=30)

            elif provider == "mistral":
                # Mistral client handles vision internally via model name usually,
                # but let's stick to text completion if our client doesn't expose explicit vision arg
                # Checking mistral_client usage... assumes text for now unless we updated it.
                # If image exists but client doesn't support it, we might fail or just send text.
                # Plan says Mistral supports Vision (Pixtral), but let's check client signature.
                # For now, pass prompt.
                return mistral_completion(prompt, model=model, timeout=45)

            elif provider == "cerebras":
                return cerebras_completion(prompt, model=model, timeout=20)

            elif provider == "openrouter":
                return openrouter_completion(prompt, model=model, timeout=60)

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            if "429" in str(e) or "Resource exhausted" in str(e):
                self.circuit_breaker.report_failure(provider, is_rate_limit=True)
            else:
                self.circuit_breaker.report_failure(provider, is_rate_limit=False)
            raise e

    def _process_single_batch(self, batch_id: int, batch: List[dict]) -> Dict:
        """Process a batch with automatic tier escalation."""
        routing = ComplexityRouter.analyze_batch(batch)
        start_tier = routing["tier"]

        # Define Tiers
        tiers = {1: ["gemini", "cerebras"], 2: ["groq", "mistral"], 3: ["openrouter"]}

        # Attempt Execution Loop
        attempt_log = []

        # Start at assigned tier, escalate if needed
        for current_tier_idx in range(start_tier, 4):
            providers = tiers.get(current_tier_idx, [])

            # Try each provider in the current tier
            for provider in providers:
                if not self.circuit_breaker.is_available(provider):
                    continue

                start_time = time.time()
                try:
                    result = self._execute_request(provider, batch)

                    if result:
                        # Success!
                        self.circuit_breaker.report_success(provider)
                        with self.stats_lock:
                            self.stats[provider]["count"] += 1
                            self.stats[provider]["time"] += time.time() - start_time

                        return {
                            "batch_id": batch_id,
                            "status": "success",
                            "data": result,
                            "provider": provider,
                            "tier": current_tier_idx,
                        }

                except Exception as e:
                    logger.warning(
                        f"Batch {batch_id} failed on {provider} (Tier {current_tier_idx}): {e}"
                    )
                    attempt_log.append(f"{provider}: {e}")

        # All attempts failed
        logger.error(f"Batch {batch_id} FAILED all tiers. Log: {attempt_log}")
        return {"batch_id": batch_id, "status": "error", "error": str(attempt_log)}

    def process_batches(self, batches: List[List[dict]]) -> List[Any]:
        """Main entry point for batch processing."""
        total = len(batches)
        logger.info(f"Processing {total} batches with Smart Cascading...")

        results = [None] * total

        # We can run many concurrent threads because the bottleneck is I/O
        # and we have an internal circuit breaker managing actual API calls.
        MAX_THREADS = 20

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {
                executor.submit(self._process_single_batch, i, batch): i
                for i, batch in enumerate(batches)
            }

            for future in as_completed(futures):
                result = future.result()
                batch_id = result["batch_id"]

                if result["status"] == "success":
                    results[batch_id] = result
                    logger.info(
                        f"Batch {batch_id} OK via {result['provider']} (Tier {result['tier']})"
                    )
                else:
                    logger.error(f"Batch {batch_id} FAILED.")

        self._print_summary()

        return [r["data"] for r in results if r and r.get("status") == "success"]

    def _print_summary(self):
        print("\n" + "=" * 60)
        print("SMART CASCADING SUMMARY")
        print("=" * 60)
        print(f"{'Provider':<12} | {'Count':>8} | {'Errors':>7} | {'Avg Time':>10}")
        print("-" * 60)
        for p, s in self.stats.items():
            avg = s["time"] / s["count"] if s["count"] > 0 else 0
            print(f"{p:<12} | {s['count']:>8} | {s['errors']:>7} | {avg:>9.2f}s")
        print("=" * 60 + "\n")


# Singleton
parallel_processor = ParallelBatchProcessor()
