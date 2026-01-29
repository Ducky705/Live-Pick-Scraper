"""
Parallel Batch Processor v3
===========================
MAXIMUM SPEED rate-limit-aware load balancer across providers.

Rate Limits (Updated 2026-01-22 from user-provided data):
  - Groq:     1000 RPM, 300K TPM - PRIMARY (16 workers)
  - Mistral:  60 RPM, 500K TPM - SECONDARY (4 workers, batched)
  - Cerebras: 30 RPM, 60K TPM - TERTIARY (2 workers)
  - Gemini:   15 RPM, 250K TPM - OVERFLOW (3 workers)
  - OpenRouter: FALLBACK ONLY (3-120s latency, not recommended)

Strategy: Groq-first (80%+ load), others as overflow, OpenRouter emergency only.
Total: 25 concurrent workers for MAXIMUM THROUGHPUT.
"""

import logging
import json
import time
from queue import Queue, Empty
from threading import Thread, Event, Lock, Condition
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import clients
from src.cerebras_client import cerebras_completion
from src.groq_client import groq_text_completion
from src.mistral_client import mistral_completion
from src.gemini_client import gemini_text_completion
from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt
import requests  # Import requests to catch Timeout

logger = logging.getLogger(__name__)

# =============================================================================
# RATE LIMIT & LATENCY CONFIGURATION
# =============================================================================

# US-002: Latency Budget Enforcement
TIMEOUT_TIER_1_SOFT = 15.0  # Speed Target (Groq/Cerebras) - Increased from 5.0
TIMEOUT_TIER_2_SOFT = 30.0  # Quality Target (Mistral/Gemini) - Increased from 20.0
TIMEOUT_GLOBAL_HARD = 45.0  # Hard Limit (Backstop) - Increased from 25.0

PROVIDER_CONFIG = {
    "groq": {
        "model": "llama-3.1-8b-instant",  # Iteration 3: Switch to 8b for speed/limits
        "rpm": 500,  # Much higher limits for 8b
        "tpm": 18000,  # CRITICAL: Lowered to 18k to match observed Free Tier limits (avoid 429s)
        "max_concurrent": 1,  # REDUCED to 1 (Low Bandwidth, Fast Latency)
        "min_delay": 1.0,  # 1s delay to be safe
        "priority": 1,  # PRIMARY provider
        "tier": 1,  # US-002: Speed Tier
    },

    "mistral": {
        "model": "mistral-large-latest",  # Updated model name
        "rpm": 60,  # 60 requests per minute
        "tpm": 500000,  # 500K TPM - can batch heavily!
        "max_concurrent": 20,  # INCREASED to 20 (High Bandwidth, Slow Latency)
        "min_delay": 0.5,  # 2 req/sec
        "batch_size": 10,  # Bundle 10 messages per call
        "priority": 2,  # PROMOTED to 2 (High Bandwidth)
        "tier": 2,  # US-002: Quality Tier
    },
    "openrouter": {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "rpm": 100,
        "tpm": 100000,
        "max_concurrent": 5, # Moderate
        "min_delay": 1.0,
        "priority": 5,  # TERTIARY (Fallback)
        "tier": 2,  # US-002: Quality Tier
    },
    "gemini": {
        "model": "gemini-1.5-flash",  # Reverted to stable model that definitely exists
        "rpm": 15,  # 15 requests per minute
        "tpm": 250000,  # 250K TPM
        "max_concurrent": 10,  # INCREASED to 10 (High Bandwidth)
        "min_delay": 4.0,  # 4s between requests (15 RPM)
        "batch_size": 5,  # Bundle 5 messages per call
        "priority": 3,  # PROMOTED to 3
        "tier": 2,  # US-002: Quality Tier
    },
    "cerebras": {
        "model": "llama3.1-8b",  # Fast
        "rpm": 30,  # 30 requests per minute
        "tpm": 60000,  # 60K TPM (lower)
        "max_concurrent": 2,  # Limited by TPM
        "min_delay": 2.0,  # 2s between requests
        "priority": 4,  # Reordered
        "tier": 1,  # US-002: Speed Tier
    },
}


class AdaptiveConcurrencyLimiter:
    """
    US-001: Adaptive Concurrency Control
    Prevents "Death Spirals" by throttling workers on 429 errors.
    """

    def __init__(self, initial=4, min_limit=1, max_limit=25):
        self.limit = initial
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.current_running = 0
        self.condition = Condition()
        self.success_streak = 0

    def acquire(self):
        """Block until a slot is available based on current dynamic limit."""
        with self.condition:
            while self.current_running >= self.limit:
                # Add timeout to prevent infinite deadlocks if notify is missed
                self.condition.wait(timeout=1.0)
            self.current_running += 1

    def release(self):
        """Release a slot and notify waiting threads."""
        with self.condition:
            self.current_running -= 1
            self.condition.notify()

    def record_success(self):
        """Record success and potentially increase concurrency."""
        with self.condition:
            self.success_streak += 1
            # After 10 consecutive successes, increment by 1 (up to MAX)
            if self.success_streak >= 10:
                if self.limit < self.max_limit:
                    old_limit = self.limit
                    self.limit = min(self.limit + 1, self.max_limit)
                    self.success_streak = 0
                    if self.limit > old_limit:
                        logger.info(
                            f"Adaptive Concurrency: Backoff recovery - Limit increased to {self.limit}"
                        )
                        self.condition.notify()  # Wake up a thread if we have room now

    def record_429(self):
        """Record 429 error and trigger backoff."""
        with self.condition:
            old_limit = self.limit
            # Upon receiving a 429 error, concurrency immediately drops by 50% (min 1)
            new_limit = max(self.min_limit, int(self.limit * 0.5))

            if new_limit < old_limit:
                self.limit = new_limit
                self.success_streak = 0  # Reset streak
                logger.warning(
                    f"Backoff Warning: Concurrency dropped to {self.limit} (Active: {self.current_running})"
                )


class RateLimiter:
    """Thread-safe rate limiter per provider."""

    def __init__(self, min_delay: float):
        self.min_delay = min_delay
        self.last_request = 0.0
        self.lock = Lock()

    def wait(self):
        """Wait until we can make the next request."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
            self.last_request = time.time()


class ParallelBatchProcessor:
    def __init__(self, providers: List[str] = None):
        """
        Initialize processor with MAXIMUM SPEED configuration.
        Priority: Groq (16) > Mistral (4) > Gemini (3) > Cerebras (2) = 25 workers
        """
        self.providers = providers or [
            "groq",
            "cerebras",
            "mistral",
            # "gemini",  # Disabled due to 404s/Auth issues
            # "openrouter", # Disabled due to slowness
        ]

        self.rate_limiters = {
            p: RateLimiter(PROVIDER_CONFIG[p]["min_delay"])
            for p in self.providers
            if p in PROVIDER_CONFIG
        }
        self.stats = {
            p: {"count": 0, "errors": 0, "total_time": 0.0} for p in self.providers
        }
        self.stats_lock = Lock()
        self.provider_status = {p: "active" for p in self.providers}
        self.consecutive_errors = {p: 0 for p in self.providers}
        self.status_lock = Lock()

        # Initialize Adaptive Limiters per Provider
        # US-002: Per-provider adaptive concurrency to prevent one flaky provider from throttling others
        self.adaptive_limiters = {}
        for p in self.providers:
            config = PROVIDER_CONFIG.get(p, {})
            max_conc = config.get("max_concurrent", 5)
            # Start at max to be aggressive, or half max? Start at max but drop fast.
            # Actually US-001 said start at 4. Let's start at max_concurrent for that provider.
            self.adaptive_limiters[p] = AdaptiveConcurrencyLimiter(
                initial=max_conc, min_limit=1, max_limit=max_conc
            )

    def _execute_request(self, provider: str, messages: List[dict]) -> str:
        """Execute a single request to a provider with rate limiting."""
        # Check fast-fail status
        with self.status_lock:
            status = self.provider_status.get(provider)
            if isinstance(status, (int, float)) and time.time() < status:
                raise Exception(
                    f"Provider {provider} is rate limited (cooldown until {status})"
                )

        config = PROVIDER_CONFIG.get(provider)
        if not config:
            raise ValueError(f"Unknown provider: {provider}")

        # Rate limit
        self.rate_limiters[provider].wait()

        # Build prompt
        prompt = generate_ai_prompt(messages)
        model = config["model"]

        # US-002: Determine Timeout based on Tier
        # Tier 1: 5s, Tier 2: 20s. Hard Cap: 25s
        tier = config.get("tier", 2)
        if tier == 1:
            timeout = TIMEOUT_TIER_1_SOFT
        else:
            timeout = TIMEOUT_TIER_2_SOFT

        # Ensure we never exceed global hard limit
        timeout = int(min(timeout, TIMEOUT_GLOBAL_HARD))

        try:
            # Execute
            if provider == "groq":
                result = groq_text_completion(prompt, model=model, timeout=timeout)
            elif provider == "openrouter":
                result = openrouter_completion(prompt, model=model, timeout=timeout)
            elif provider == "mistral":
                result = mistral_completion(prompt, model=model, timeout=timeout)
            elif provider == "cerebras":
                result = cerebras_completion(prompt, model=model, timeout=timeout)
            elif provider == "gemini":
                result = gemini_text_completion(prompt, model=model, timeout=timeout)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            if result is None:
                raise Exception(f"Provider {provider} returned None (possible timeout/error)")

            # Success - reset consecutive errors
            with self.status_lock:
                self.consecutive_errors[provider] = 0

            return result

        except Exception as e:
            # US-002: Catch timeouts explicitly
            # Note: Clients currently swallow RequestException and return None (except 429)
            # We need to catch 'Timeout' if it bubbles up, or 'ReadTimeout', etc.
            # If clients return None on timeout, we might miss the specific log.
            # However, we will modify clients to bubble up timeouts.

            error_str = str(e).lower()
            if "timeout" in error_str or isinstance(e, requests.Timeout):
                logger.error(f"Timeout Failure: {provider} exceeded {timeout}s limit")
                # Trigger backoff for timeouts too
                with self.status_lock:
                    self.consecutive_errors[provider] += 1
                    backoff = min(60.0, 5.0 * (2 ** (self.consecutive_errors[provider] - 1)))
                    self.provider_status[provider] = time.time() + backoff
                raise e  # Re-raise to be handled by caller as error

            if "429" in str(e):
                with self.status_lock:
                    self.consecutive_errors[provider] += 1
                    # Exponential Backoff: 5s, 10s, 20s, 40s, 60s (max)
                    backoff = min(60.0, 5.0 * (2 ** (self.consecutive_errors[provider] - 1)))
                    self.provider_status[provider] = time.time() + backoff
                logger.warning(
                    f"[{provider}] MARKED RATE LIMITED (Backoff {backoff}s)"
                )
            raise e

    def _process_batch(
        self, batch_id: int, messages: List[dict], provider: str
    ) -> Dict:
        """Process a single batch with a specific provider."""

        # Acquire adaptive concurrency slot (US-001/US-002: Per Provider)
        limiter = self.adaptive_limiters.get(provider)
        if limiter:
            limiter.acquire()

        start = time.time()
        try:
            result = self._execute_request(provider, messages)
            duration = time.time() - start

            # CRITICAL: Treat None result as an error (API returned nothing)
            if result is None:
                with self.stats_lock:
                    self.stats[provider]["errors"] += 1
                logger.error(f"[{provider}] Batch {batch_id} returned None (API error)")
                return {
                    "batch_id": batch_id,
                    "status": "error",
                    "error": "API returned None",
                    "provider": provider,
                }

            with self.stats_lock:
                self.stats[provider]["count"] += 1
                self.stats[provider]["total_time"] += duration

            logger.info(f"[{provider}] Batch {batch_id} done in {duration:.2f}s")

            # Record success for adaptive concurrency (US-001)
            if limiter:
                limiter.record_success()

            return {
                "batch_id": batch_id,
                "status": "success",
                "data": result,
                "provider": provider,
            }

        except Exception as e:
            duration = time.time() - start
            with self.stats_lock:
                self.stats[provider]["errors"] += 1

            # Check for 429 and trigger backoff (US-001)
            if "429" in str(e) and limiter:
                limiter.record_429()

            logger.error(f"[{provider}] Batch {batch_id} failed: {e}")
            return {
                "batch_id": batch_id,
                "status": "error",
                "error": str(e),
                "provider": provider,
            }
        finally:
            # Release slot (US-001)
            if limiter:
                limiter.release()

    def _retry_batch(
        self,
        batch_id: int,
        batch: List[dict],
        failed_provider: str,
        fallback_order: List[str],
    ) -> Dict:
        """Retry a batch with fallback providers."""
        for provider in fallback_order:
            if provider == failed_provider:
                continue

            result = self._process_batch(batch_id, batch, provider)
            if result["status"] == "success":
                logger.info(f"Batch {batch_id} recovered via {provider}")
                return result

        logger.error(f"Batch {batch_id} failed on all providers")
        return {
            "batch_id": batch_id,
            "status": "error",
            "data": None,
            "provider": "all_failed",
        }

    def process_batches(self, batches: List[List[dict]]) -> List[Any]:
        """
        Process batches with MAXIMUM parallelism and AUTO-FALLBACK.

        Strategy:
        1. Round-robin across all providers based on their capacity
        2. Retry failed batches with fallback providers
        """
        total = len(batches)
        logger.info(f"Processing {total} batches with auto-fallback enabled...")

        # Calculate worker allocation: Groq(16) + Mistral(4) + Gemini(3) + Cerebras(2) = 25
        workers = []
        for p in self.providers:
            if p in PROVIDER_CONFIG:
                workers.extend([p] * PROVIDER_CONFIG[p]["max_concurrent"])

        max_workers = len(workers)
        logger.info(f"Using {max_workers} workers: {list(set(workers))}")

        results = [None] * total  # Use list for indexed access
        failed_batches = []
        batch_queue = list(enumerate(batches))  # [(id, batch), ...]

        # Round-robin assignment
        def get_next_provider(idx: int) -> str:
            return workers[idx % len(workers)]

        # Phase 1: Initial pass with round-robin
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for i, (batch_id, batch) in enumerate(batch_queue):
                provider = get_next_provider(i)
                future = executor.submit(self._process_batch, batch_id, batch, provider)
                futures[future] = (batch_id, batch, provider)

            # Collect results
            for future in as_completed(futures):
                batch_id, batch, provider = futures[future]
                result = future.result()

                if result["status"] == "success":
                    results[batch_id] = result
                else:
                    failed_batches.append((batch_id, batch, provider))

                # Progress
                done = sum(1 for r in results if r is not None)
                if done % 5 == 0 or done == total:
                    logger.info(f"Progress: {done}/{total} batches complete")

        # Phase 2: Retry failed batches with fallback providers
        if failed_batches:
            logger.warning(
                f"Retrying {len(failed_batches)} failed batches with fallback providers..."
            )

            # Get list of providers that worked (have successful results)
            working_providers = set()
            for r in results:
                if r and r.get("status") == "success":
                    working_providers.add(r.get("provider"))

            # Determine fallback order (prioritize working providers)
            # CRITICAL OPTIMIZATION: Deprioritize OpenRouter (Slow)
            base_fallback_order = [
                "cerebras",
                "mistral",
                "groq",
            ]


            fallback_order = [
                p for p in base_fallback_order if p in self.providers and p != "groq"
            ]  # Groq already failed

            # Add working providers to front
            for wp in working_providers:
                if wp in fallback_order:
                    fallback_order.remove(wp)
                    fallback_order.insert(0, wp)

            logger.info(f"Fallback order: {fallback_order}")

            # US-002: Parallelize Phase 2 Retries
            # Use max_workers to speed up recovery
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures_retry = {
                    executor.submit(
                        self._retry_batch, batch_id, batch, failed_provider, fallback_order
                    ): batch_id
                    for batch_id, batch, failed_provider in failed_batches
                }

                for future in as_completed(futures_retry):
                    batch_id = futures_retry[future]
                    try:
                        result = future.result()
                        results[batch_id] = result
                    except Exception as e:
                        logger.error(f"Retry thread failed for Batch {batch_id}: {e}")
                        results[batch_id] = {
                            "batch_id": batch_id,
                            "status": "error",
                            "data": None,
                        }

        self._print_summary()

        # Return results in order (preserve None for failures to maintain batch mapping)
        final_results = []
        for r in results:
            if r and r.get("status") == "success" and r.get("data"):
                final_results.append(r["data"])
            else:
                final_results.append(None)
        
        return final_results

    def process_batches_groq_priority(self, batches: List[List[dict]]) -> List[Any]:
        """
        Groq-first strategy: Blast all requests to Groq (Configured concurrent), use others as fallback.
        MAXIMUM SPEED mode - Groq handles 1000 RPM, so we can push high concurrency if limits allow.
        """
        total = len(batches)

        results = [None] * total
        failed_batches = []

        # Phase 1: Blast through with Groq (Using Configured Concurrency)
        groq_config = PROVIDER_CONFIG["groq"]
        concurrency = groq_config.get("max_concurrent", 2)
        logger.info(f"Processing {total} batches (GROQ-PRIORITY, {concurrency} concurrent)...")

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(self._process_batch, i, batch, "groq"): i
                for i, batch in enumerate(batches)
            }

            for future in as_completed(futures):
                batch_id = futures[future]
                result = future.result()

                if result["status"] == "success":
                    results[batch_id] = result
                else:
                    failed_batches.append((batch_id, batches[batch_id]))

        # Phase 2: Retry failures with fallback providers (Cerebras > Mistral)
        if failed_batches:
            logger.info(
                f"Retrying {len(failed_batches)} failed batches with fallbacks..."
            )
            fallback_providers = ["cerebras", "mistral"]

            # US-002: Parallelize Phase 2 Retries
            with ThreadPoolExecutor(max_workers=len(fallback_providers) * 2) as executor:
                futures_retry = {
                    executor.submit(
                        self._retry_batch, batch_id, batch, "groq", fallback_providers
                    ): batch_id
                    for batch_id, batch in failed_batches
                }

                for future in as_completed(futures_retry):
                    batch_id = futures_retry[future]
                    try:
                        result = future.result()
                        results[batch_id] = result
                    except Exception as e:
                        logger.error(f"Retry thread failed for Batch {batch_id}: {e}")
                        results[batch_id] = {
                            "batch_id": batch_id,
                            "status": "error",
                            "data": None,
                        }

        self._print_summary()
        
        # Return results in order (preserve None for failures)
        final_results = []
        for r in results:
            if r and r.get("status") == "success" and r.get("data"):
                final_results.append(r["data"])
            else:
                final_results.append(None)
                
        return final_results

    def _print_summary(self):
        """Print execution stats."""
        print("\n" + "=" * 60)
        print("PARALLEL BATCH PROCESSING SUMMARY")
        print("=" * 60)
        print(
            f"{'Provider':<12} | {'Batches':>8} | {'Errors':>7} | {'Avg Time':>10} | {'RPM Used':>10}"
        )
        print("-" * 60)

        for p in self.providers:
            s = self.stats.get(p, {"count": 0, "errors": 0, "total_time": 0})
            avg_time = s["total_time"] / s["count"] if s["count"] > 0 else 0
            rpm = PROVIDER_CONFIG.get(p, {}).get("rpm", 0)
            print(
                f"{p:<12} | {s['count']:>8} | {s['errors']:>7} | {avg_time:>8.2f}s | {rpm:>10}"
            )
        print("=" * 60 + "\n")


# Singleton instance
parallel_processor = ParallelBatchProcessor()
