"""
Parallel Batch Processor v4
===========================
EXTREME THROUGHPUT (US-011)
Global Concurrency: 32 workers
Target: > 5.0 msg/sec

Rate Limits (Updated 2026-01-22):
  - Groq:     500 RPM, 300K TPM - PRIMARY (16 workers)
  - Mistral:  60 RPM, 500K TPM - SECONDARY (8 workers, batched)
  - Cerebras: 30 RPM, 60K TPM - TERTIARY (5 workers)
  - Gemini:   15 RPM, 250K TPM - OVERFLOW (3 workers)
  - OpenRouter: FALLBACK ONLY

Strategy: Aggressive striping across all providers to maximize throughput.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Condition, Lock
from typing import Any

try:
    import requests
except ImportError:
    # Mock requests for simulation/offline mode
    class MockRequests:
        class Timeout(Exception): pass
    requests = MockRequests()

# Import clients
try:
    from src.cerebras_client import cerebras_completion
    from src.gemini_client import gemini_text_completion
    from src.groq_client import groq_text_completion
    from src.mistral_client import mistral_completion
    from src.openrouter_client import openrouter_completion
except ImportError:
    # Mock for simulation
    def cerebras_completion(*args, **kwargs): return "Mocked AI Response"
    def gemini_text_completion(*args, **kwargs): return "Mocked AI Response"
    def groq_text_completion(*args, **kwargs): return "Mocked AI Response"
    def mistral_completion(*args, **kwargs): return "Mocked AI Response"
    def openrouter_completion(*args, **kwargs): return "Mocked AI Response"
from src.prompt_builder import generate_ai_prompt

logger = logging.getLogger(__name__)

# =============================================================================
# RATE LIMIT & LATENCY CONFIGURATION
# =============================================================================

# US-011: Aggressive Timeouts for < 2.0s Avg Response
TIMEOUT_TIER_1_SOFT = 15.0  # Speed Target (Groq/Cerebras) - Aggressive Fail Fast (Increased to 15s for batches)
TIMEOUT_TIER_2_SOFT = 25.0  # Quality Target (Mistral/Gemini) - Increased for stability
TIMEOUT_GLOBAL_HARD = 60.0  # Hard Limit

PROVIDER_CONFIG = {
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "rpm": 500,
        "tpm": 18000,
        "batch_size": 10,
        "max_concurrent": 1,  # US-200: Minimized to avoid TPM limits/429s
        "min_delay": 0.2,
        "priority": 1,
        "tier": 1,
    },
    "openrouter": {
        "model": "stepfun/step-3.5-flash:free",
        "rpm": 10, # Reduced to 10 to minimize 429s on Free Tier
        "tpm": 100000,
        "max_concurrent": 5, # Increased for Step 3.5 which handles concurrency better or needs it for throughput
        "min_delay": 2.0, # Reduced delay
        "priority": 0, # US-002: HIGHEST PRIORITY (Supercedes Groq)
        "tier": 1,
    },
    "mistral": {
        "model": "open-mistral-nemo",
        "rpm": 60,
        "tpm": 500000,
        "max_concurrent": 8,
        "min_delay": 1.0,
        "batch_size": 20,
        "priority": 4,  # US-200: Lowest priority
        "tier": 2,
    },
    "cerebras": {
        "model": "llama3.1-8b",
        "rpm": 30,
        "tpm": 60000,
        "max_concurrent": 5,
        "min_delay": 2.0,
        "priority": 2,
        "tier": 1,
    },
    "gemini": {
        "model": "gemini-2.0-flash",
        "rpm": 15,
        "tpm": 250000,
        "max_concurrent": 3,
        "min_delay": 4.0,
        "priority": 2, # Promoted to Tier 1 equivalent
        "tier": 1,
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
                        # logger.debug(
                        #     f"Adaptive Concurrency: Backoff recovery - Limit increased to {self.limit}"
                        # )
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
                logger.warning(f"Backoff Warning: Concurrency dropped to {self.limit} (Active: {self.current_running})")


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
    def __init__(self, providers: list[str] | None = None):
        """
        Initialize processor with EXTREME SPEED configuration.
        """
        self.providers = providers or [
            "openrouter", # ACCURACY KING: Step 3.5 Flash (95% Recall) & Llama 3.3 70B (81%)
            # "mistral",    # DISABLED: Low Recall (<60%) - Fast but Inaccurate
            # "cerebras",   # DISABLED: Low Recall (<60%) - Fast but Inaccurate
            # "groq",     # DISABLED: 403 Forbidden
            # "gemini",   # DISABLED: 429 Rate Limited
        ]

        self.rate_limiters = {
            p: RateLimiter(PROVIDER_CONFIG[p]["min_delay"]) for p in self.providers if p in PROVIDER_CONFIG
        }
        self.stats = {p: {"count": 0, "errors": 0, "total_time": 0.0} for p in self.providers}
        self.stats_lock = Lock()
        self.provider_status: dict[str, Any] = {p: "active" for p in self.providers}
        self.consecutive_errors = {p: 0 for p in self.providers}
        self.status_lock = Lock()

        # Initialize Adaptive Limiters per Provider
        self.adaptive_limiters = {}
        for p in self.providers:
            config = PROVIDER_CONFIG.get(p, {})
            max_conc = config.get("max_concurrent", 5)
            self.adaptive_limiters[p] = AdaptiveConcurrencyLimiter(initial=max_conc, min_limit=1, max_limit=max_conc)

    def _execute_request(self, provider: str, messages: list[dict], **kwargs) -> str:
        """Execute a single request to a provider with rate limiting."""
        # Check fast-fail status
        with self.status_lock:
            status = self.provider_status.get(provider)
            if isinstance(status, (int, float)) and time.time() < status:
                raise Exception(f"Provider {provider} is rate limited (cooldown until {status})")

        config = PROVIDER_CONFIG.get(provider)
        if not config:
            raise ValueError(f"Unknown provider: {provider}")

        # Rate limit
        self.rate_limiters[provider].wait()

        # Build prompt
        schedule_context = kwargs.get("schedule_context")
        style_context = kwargs.get("style_context")
        prompt = generate_ai_prompt(messages, schedule_context=schedule_context, style_context=style_context)
        model = config["model"]

        # US-002: Determine Timeout based on Tier
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
            error_str = str(e).lower()
            if "timeout" in error_str or isinstance(e, requests.Timeout):
                logger.error(f"Timeout Failure: {provider} exceeded {timeout}s limit")
                with self.status_lock:
                    self.consecutive_errors[provider] += 1
                    backoff = min(60.0, 5.0 * (2 ** (self.consecutive_errors[provider] - 1)))
                    self.provider_status[provider] = time.time() + backoff
                raise e

            if "429" in str(e) or "403" in str(e):
                with self.status_lock:
                    self.consecutive_errors[provider] += 1
                    backoff = min(60.0, 5.0 * (2 ** (self.consecutive_errors[provider] - 1)))
                    self.provider_status[provider] = time.time() + backoff
                logger.warning(f"[{provider}] MARKED RATE LIMITED/BLOCKED (Backoff {backoff}s)")
            raise e

    def _process_batch(self, batch_id: int, messages: list[dict], provider: str, **kwargs) -> dict:
        """Process a single batch with a specific provider."""

        # Acquire adaptive concurrency slot
        limiter = self.adaptive_limiters.get(provider)
        if limiter:
            limiter.acquire()

        start = time.time()
        try:
            result = self._execute_request(provider, messages, **kwargs)
            duration = time.time() - start

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
            if limiter:
                limiter.release()

    def _retry_batch(
        self,
        batch_id: int,
        batch: list[dict],
        failed_provider: str,
        fallback_order: list[str],
        **kwargs,
    ) -> dict:
        """Retry a batch with fallback providers."""
        for provider in fallback_order:
            if provider == failed_provider:
                continue

            # Kwargs already contains context from the original submission if we did it right
            result = self._process_batch(batch_id, batch, provider, **kwargs)
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

    def process_batches(self, batches: list[list[dict]], allowed_providers: list[str] | None = None, **kwargs) -> list[Any]:
        """
        Process batches with EXTREME parallelism and AUTO-FALLBACK.
        """
        total = len(batches)
        logger.info(f"Processing {total} batches with EXTREME throughput...")

        workers = []
        target_providers = allowed_providers if allowed_providers else self.providers

        # Balanced Striping (Interleaved)
        # Instead of [A, A, B, B], create [A, B, A, B] to smooth load
        max_slots = max(
            (PROVIDER_CONFIG[p]["max_concurrent"] for p in target_providers if p in PROVIDER_CONFIG), default=1
        )

        for i in range(max_slots):
            for p in target_providers:
                if p in PROVIDER_CONFIG:
                    count = PROVIDER_CONFIG[p]["max_concurrent"]
                    if i < count:
                        workers.append(p)

        max_workers = len(workers)
        if max_workers == 0:
            logger.error("No workers available!")
            return [None] * total

        logger.info(f"Using {max_workers} workers across {len(target_providers)} providers")

        results: list[Any] = [None] * total
        failed_batches = []
        batch_queue = list(enumerate(batches))

        # Round-robin assignment
        def get_next_provider(idx: int) -> str:
            return workers[idx % len(workers)]

        # Phase 1: Initial pass
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for i, item in enumerate(batch_queue):
                # Check if item is (batch, context) tuple or just batch
                if isinstance(item[1], tuple):
                    batch_id, (batch, batch_context) = item
                    # Merge global kwargs with batch-specific context
                    # batch_context should override kwargs if keys collide
                    call_kwargs = kwargs.copy()
                    call_kwargs.update(batch_context)
                else:
                    batch_id, batch = item
                    call_kwargs = kwargs.copy()

                provider = get_next_provider(i)
                # Store call_kwargs in future map to reuse on retry
                future = executor.submit(self._process_batch, batch_id, batch, provider, **call_kwargs)
                futures[future] = (batch_id, batch, provider, call_kwargs)

            for future in as_completed(futures):
                batch_id, batch, provider, call_kwargs = futures[future]
                try:
                    result = future.result()

                    if result["status"] == "success":
                        results[batch_id] = result
                    else:
                        failed_batches.append((batch_id, batch, provider, call_kwargs))
                except Exception as e:
                     logger.error(f"Worker exception for Batch {batch_id}: {e}")
                     failed_batches.append((batch_id, batch, provider, call_kwargs))

                done = sum(1 for r in results if r is not None and r.get("status") == "success") # Only count successes? No, results is array.
                # Actually results contains Nones initially.
                # done = len([r for r in results if r is not None])
                
                if (i+1) % 10 == 0: # Approximate logging
                    pass # logger.info(...)

        # Phase 2: Retry
        if failed_batches:
            logger.warning(f"Retrying {len(failed_batches)} failed batches...")

            working_providers: set[str] = set()
            for r in results:
                if r and r.get("status") == "success":
                    working_providers.add(r.get("provider"))

            base_fallback_order = ["groq", "cerebras", "mistral", "gemini"]
            fallback_order = [p for p in base_fallback_order if p in target_providers]

            # Prioritize working, respecting configuration priority
            sorted_working = sorted(
                list(working_providers), key=lambda p: PROVIDER_CONFIG.get(p, {}).get("priority", 99)
            )

            # Insert in reverse order so highest priority ends up at index 0
            for wp in reversed(sorted_working):
                if wp in fallback_order:
                    fallback_order.remove(wp)
                    fallback_order.insert(0, wp)
            
            # Create safe fallback if empty
            if not fallback_order:
                fallback_order = ["mistral", "groq"] # Default safe bets

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures_retry = {}
                for batch_id, batch, failed_provider, call_kwargs in failed_batches:
                    # Pass the captured call_kwargs to retry
                    futures_retry[
                        executor.submit(self._retry_batch, batch_id, batch, failed_provider, fallback_order, **call_kwargs)
                    ] = batch_id

                for future in as_completed(futures_retry):
                    batch_id = futures_retry[future]
                    try:
                        result = future.result()
                        results[batch_id] = result
                    except Exception as e:
                        logger.error(f"Retry thread failed for Batch {batch_id}: {e}")

        self._print_summary()

        final_results: list[Any] = []
        for r in results:
            if r and r.get("status") == "success" and r.get("data"):
                final_results.append(r["data"])
            else:
                final_results.append(None)

        return final_results

    def process_batches_groq_priority(self, batches: list[list[dict]], **kwargs) -> list[Any]:
        """
        Legacy method mapped to hybrid strategy.
        """
        logger.info("Redirecting 'Groq Priority' to 'Hybrid Extreme Speed'")
        return self.process_batches(batches, **kwargs)

    def _print_summary(self) -> None:
        """Print execution stats."""
        logger.info("=" * 60)
        logger.info("EXTREME THROUGHPUT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"{'Provider':<12} | {'Batches':>8} | {'Errors':>7} | {'Avg Time':>10} | {'RPM':>10}")
        logger.info("-" * 60)

        for p in self.providers:
            s = self.stats.get(p, {"count": 0, "errors": 0, "total_time": 0})
            avg_time = s["total_time"] / s["count"] if s["count"] > 0 else 0
            rpm = PROVIDER_CONFIG.get(p, {}).get("rpm", 0)
            logger.info(f"{p:<12} | {s['count']:>8} | {s['errors']:>7} | {avg_time:>8.2f}s | {rpm:>10}")
        logger.info("=" * 60)


# Singleton instance
parallel_processor = ParallelBatchProcessor()
