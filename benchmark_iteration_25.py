import os
import sys
import json
import time
import logging
import asyncio
from typing import List, Dict

# Setup
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("Benchmark25")

from src.provider_pool import pooled_completion
from src.prompts.core import get_compact_extraction_prompt


# Load Real Data
def load_golden_set():
    try:
        with open("new_golden_set.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("new_golden_set.json not found!")
        return []


GOLDEN_SET = load_golden_set()
TEST_MESSAGES = [item["text"] for item in GOLDEN_SET] if GOLDEN_SET else []


async def process_message_controlled(
    i: int, raw_msg: str, sem: asyncio.Semaphore
) -> Dict:
    """Async wrapper with Semaphore for concurrency control."""
    async with sem:
        logger.info(
            f"Processing Msg {i + 1}/{len(TEST_MESSAGES)} (Acquired Semaphore)..."
        )

        prompt = get_compact_extraction_prompt(raw_data=raw_msg)
        start_t = time.time()

        loop = asyncio.get_running_loop()
        # Run blocking call in executor
        response = await loop.run_in_executor(
            None, lambda: pooled_completion(prompt, images=None, timeout=45)
        )

        duration = time.time() - start_t

        is_success = False
        if response:
            try:
                data = json.loads(response)
                if isinstance(data, (dict, list)):
                    is_success = True
            except:
                pass

        return {
            "id": i,
            "duration": duration,
            "success": is_success,
            "response_length": len(response) if response else 0,
        }


async def run_benchmark_async():
    # Iteration 25: Real World Load Test
    # Why: Verify Concurrency=4 holds up with complex/long real-world messages
    CONCURRENCY_LIMIT = 4
    logger.info(
        f"Starting Ralph Wiggum Loop - Iteration 25 (Real Data Load Test, Limit={CONCURRENCY_LIMIT})..."
    )

    if not TEST_MESSAGES:
        logger.error("No test messages loaded. Aborting.")
        return

    logger.info(f"Test Set: {len(TEST_MESSAGES)} REAL messages from Golden Set")

    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    start_global = time.time()

    tasks = [
        process_message_controlled(i, msg, sem) for i, msg in enumerate(TEST_MESSAGES)
    ]
    results = await asyncio.gather(*tasks)

    end_global = time.time()
    total_time = end_global - start_global
    avg_latency = total_time / len(TEST_MESSAGES)

    successful = sum(1 for r in results if r["success"])
    total_requests = len(TEST_MESSAGES)

    logger.info("=" * 40)
    logger.info("BENCHMARK RESULTS (ITERATION 25)")
    logger.info("=" * 40)
    logger.info(f"Total Requests: {total_requests}")
    logger.info(f"Total Time:     {total_time:.2f}s")
    logger.info(f"Avg Latency:    {avg_latency:.2f}s (Wall Clock / N)")
    logger.info(
        f"Success Rate:   {successful}/{len(TEST_MESSAGES)} ({successful / len(TEST_MESSAGES) * 100:.1f}%)"
    )
    logger.info("=" * 40)

    # Save Stats
    with open("iteration_25_stats.txt", "w") as f:
        f.write(f"Total Requests: {total_requests}\n")
        f.write(f"Total Time: {total_time:.4f}\n")
        f.write(f"Avg Latency: {avg_latency:.4f}\n")
        f.write(f"Success Rate: {successful / len(TEST_MESSAGES)}\n")


def run_benchmark():
    asyncio.run(run_benchmark_async())


if __name__ == "__main__":
    run_benchmark()
