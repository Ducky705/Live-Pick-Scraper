import os
import sys
import json
import time
import logging
from typing import List, Dict

# Setup
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("Benchmark01")

try:
    from src.provider_pool import pooled_completion
    from src.prompts.core import get_compact_extraction_prompt
except ImportError:
    # Fallback for when running in an environment where src isn't perfectly set up or differing versions
    logger.error("Could not import src modules. Ensure running from root.")
    sys.exit(1)

# Mock Data (Baseline Set)
TEST_MESSAGES = [
    "### 101 [T] NBA\nLakers -5.5\nOdds: -110\n1U",
    "### 102 [T] PARLAY (3 Picks)\n1. Chiefs -3.5\n2. Ravens ML\n3. Over 45.5 (KC/BUF)\nOdds: +600\n0.5U",
    "### 103 [T] NFL Prop\nTravis Kelce Over 6.5 Receptions (-120)\n2 Units",
    "### 104 [T] max play alert!!!!\ngoing big on knicks ml tonight... brunson is back baby.\nplay: nyk moneyline\nodds: -130",
    "### 105 [T] Djokovic vs Sinner\nSinner ML +110",
]


def run_benchmark():
    logger.info("Starting Ralph Wiggum Loop - Iteration 1 (Baseline Initialization)...")
    logger.info(f"Test Set: {len(TEST_MESSAGES)} messages")

    results = []
    start_global = time.time()

    successful = 0

    for i, raw_msg in enumerate(TEST_MESSAGES):
        logger.info(f"Processing Msg {i + 1}/{len(TEST_MESSAGES)}...")

        prompt = get_compact_extraction_prompt(raw_data=raw_msg)

        start_t = time.time()
        # Basic synchronous call via the pool
        response = pooled_completion(prompt, images=None, timeout=30)
        duration = time.time() - start_t

        is_success = False
        if response:
            try:
                data = json.loads(response)
                if isinstance(data, (dict, list)):
                    is_success = True
                    successful += 1
            except:
                pass

        results.append({"id": i, "duration": duration, "success": is_success})

    end_global = time.time()
    total_time = end_global - start_global
    avg_latency = total_time / len(TEST_MESSAGES)

    logger.info("=" * 40)
    logger.info("BENCHMARK RESULTS (ITERATION 1)")
    logger.info("=" * 40)
    logger.info(f"Total Time:     {total_time:.2f}s")
    logger.info(f"Avg Latency:    {avg_latency:.2f}s")
    logger.info(
        f"Success Rate:   {successful}/{len(TEST_MESSAGES)} ({successful / len(TEST_MESSAGES) * 100:.1f}%)"
    )
    logger.info("=" * 40)

    # Save Stats
    with open("iteration_1_stats.txt", "w") as f:
        f.write(f"Total Requests: {len(TEST_MESSAGES)}\n")
        f.write(f"Avg Latency: {avg_latency:.4f}\n")
        f.write(f"Success Rate: {successful / len(TEST_MESSAGES)}\n")


if __name__ == "__main__":
    run_benchmark()
