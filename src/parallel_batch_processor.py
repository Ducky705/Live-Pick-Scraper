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
from threading import Thread, Event, Lock
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import clients
from src.cerebras_client import cerebras_completion
from src.groq_client import groq_text_completion
from src.mistral_client import mistral_completion
from src.gemini_client import gemini_text_completion
from src.prompt_builder import generate_ai_prompt

logger = logging.getLogger(__name__)

# =============================================================================
# RATE LIMIT CONFIGURATION - MAXIMUM SPEED
# =============================================================================
PROVIDER_CONFIG = {
    "groq": {
        "model": "llama-3.3-70b-versatile",  # User's choice - best quality
        "rpm": 1000,                          # 1000 requests per minute
        "tpm": 300000,                        # 300K tokens per minute
        "max_concurrent": 16,                 # 1000 RPM / 60s = 16.7/sec
        "min_delay": 0.06,                    # 60ms between requests
        "priority": 1,                        # PRIMARY provider
    },
    "mistral": {
        "model": "codestral-latest",          # 100% F1
        "rpm": 60,                            # 60 requests per minute
        "tpm": 500000,                        # 500K TPM - can batch heavily!
        "max_concurrent": 4,                  # 60 RPM = 1/sec, 4 concurrent staggered
        "min_delay": 1.0,                     # 1 req/sec
        "batch_size": 10,                     # Bundle 10 messages per call
        "priority": 2,
    },
    "gemini": {
        "model": "gemini-2.5-flash-lite",     # Highest RPM on Gemini
        "rpm": 15,                            # 15 requests per minute
        "tpm": 250000,                        # 250K TPM
        "max_concurrent": 3,                  # 15 RPM / 60 = 0.25/sec
        "min_delay": 4.0,                     # 4s between requests
        "batch_size": 5,                      # Bundle 5 messages per call
        "priority": 3,
    },
    "cerebras": {
        "model": "llama3.1-8b",               # Fast
        "rpm": 30,                            # 30 requests per minute
        "tpm": 60000,                         # 60K TPM (lower)
        "max_concurrent": 2,                  # 30 RPM = 0.5/sec
        "min_delay": 2.0,                     # 2s between requests
        "priority": 4,
    },
}


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
        self.providers = providers or ["groq", "mistral", "gemini", "cerebras"]
        self.rate_limiters = {
            p: RateLimiter(PROVIDER_CONFIG[p]["min_delay"]) 
            for p in self.providers if p in PROVIDER_CONFIG
        }
        self.stats = {p: {"count": 0, "errors": 0, "total_time": 0.0} for p in self.providers}
        self.stats_lock = Lock()

    def _execute_request(self, provider: str, messages: List[dict]) -> str:
        """Execute a single request to a provider with rate limiting."""
        config = PROVIDER_CONFIG.get(provider)
        if not config:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Rate limit
        self.rate_limiters[provider].wait()
        
        # Build prompt
        prompt = generate_ai_prompt(messages)
        model = config["model"]
        
        # Execute
        if provider == "groq":
            return groq_text_completion(prompt, model=model, timeout=30)
        elif provider == "mistral":
            return mistral_completion(prompt, model=model, timeout=30)
        elif provider == "cerebras":
            return cerebras_completion(prompt, model=model, timeout=30)
        elif provider == "gemini":
            return gemini_text_completion(prompt, model=model, timeout=60)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _process_batch(self, batch_id: int, messages: List[dict], provider: str) -> Dict:
        """Process a single batch with a specific provider."""
        start = time.time()
        try:
            result = self._execute_request(provider, messages)
            duration = time.time() - start
            
            with self.stats_lock:
                self.stats[provider]["count"] += 1
                self.stats[provider]["total_time"] += duration
            
            logger.info(f"[{provider}] Batch {batch_id} done in {duration:.2f}s")
            return {"batch_id": batch_id, "status": "success", "data": result, "provider": provider}
        
        except Exception as e:
            duration = time.time() - start
            with self.stats_lock:
                self.stats[provider]["errors"] += 1
            
            logger.error(f"[{provider}] Batch {batch_id} failed: {e}")
            return {"batch_id": batch_id, "status": "error", "error": str(e), "provider": provider}

    def process_batches(self, batches: List[List[dict]]) -> List[Any]:
        """
        Process batches with MAXIMUM parallelism based on rate limits.
        
        Strategy (25 total workers):
        - Groq: 16 workers (64%) - PRIMARY
        - Mistral: 4 workers (16%) - SECONDARY
        - Gemini: 3 workers (12%) - TERTIARY
        - Cerebras: 2 workers (8%) - OVERFLOW
        """
        total = len(batches)
        logger.info(f"Processing {total} batches with MAXIMUM SPEED (25 workers)...")
        
        # Calculate worker allocation: Groq(16) + Mistral(4) + Gemini(3) + Cerebras(2) = 25
        workers = []
        for p in self.providers:
            if p in PROVIDER_CONFIG:
                workers.extend([p] * PROVIDER_CONFIG[p]["max_concurrent"])
        
        max_workers = len(workers)
        logger.info(f"Using {max_workers} workers: {workers}")
        
        results = []
        batch_queue = list(enumerate(batches))  # [(id, batch), ...]
        
        # Round-robin assignment with preference for Groq
        def get_next_provider(idx: int) -> str:
            return workers[idx % len(workers)]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            for i, (batch_id, batch) in enumerate(batch_queue):
                provider = get_next_provider(i)
                future = executor.submit(self._process_batch, batch_id, batch, provider)
                futures[future] = batch_id
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                # Progress
                done = len(results)
                if done % 5 == 0 or done == total:
                    logger.info(f"Progress: {done}/{total} batches complete")
        
        # Sort by batch_id
        results.sort(key=lambda x: x["batch_id"])
        
        self._print_summary()
        
        # Return successful results only
        return [r["data"] for r in results if r["status"] == "success"]

    def process_batches_groq_priority(self, batches: List[List[dict]]) -> List[Any]:
        """
        Groq-first strategy: Blast all requests to Groq (16 concurrent), use others as fallback.
        MAXIMUM SPEED mode - Groq handles 1000 RPM, so we can push 16 concurrent easily.
        """
        total = len(batches)
        logger.info(f"Processing {total} batches (GROQ-PRIORITY, 16 concurrent)...")
        
        results = [None] * total
        failed_batches = []
        
        # Phase 1: Blast through with Groq (16 concurrent workers)
        groq_config = PROVIDER_CONFIG["groq"]
        with ThreadPoolExecutor(max_workers=groq_config["max_concurrent"]) as executor:
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
        
        # Phase 2: Retry failures with fallback providers (Mistral > Gemini > Cerebras)
        if failed_batches:
            logger.info(f"Retrying {len(failed_batches)} failed batches with fallbacks...")
            fallback_providers = ["mistral", "gemini", "cerebras"]
            
            for batch_id, batch in failed_batches:
                for provider in fallback_providers:
                    result = self._process_batch(batch_id, batch, provider)
                    if result["status"] == "success":
                        results[batch_id] = result
                        break
                else:
                    results[batch_id] = {"batch_id": batch_id, "status": "error", "data": None}
        
        self._print_summary()
        return [r["data"] for r in results if r and r.get("status") == "success"]

    def _print_summary(self):
        """Print execution stats."""
        print("\n" + "=" * 60)
        print("PARALLEL BATCH PROCESSING SUMMARY")
        print("=" * 60)
        print(f"{'Provider':<12} | {'Batches':>8} | {'Errors':>7} | {'Avg Time':>10} | {'RPM Used':>10}")
        print("-" * 60)
        
        for p in self.providers:
            s = self.stats.get(p, {"count": 0, "errors": 0, "total_time": 0})
            avg_time = s["total_time"] / s["count"] if s["count"] > 0 else 0
            rpm = PROVIDER_CONFIG.get(p, {}).get("rpm", 0)
            print(f"{p:<12} | {s['count']:>8} | {s['errors']:>7} | {avg_time:>8.2f}s | {rpm:>10}")
        print("=" * 60 + "\n")


# Singleton instance
parallel_processor = ParallelBatchProcessor()
