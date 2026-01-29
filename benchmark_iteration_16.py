import json
import logging
import os
import sys
import time

# Setup
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("Benchmark16")

from src.prompts.core import get_compact_extraction_prompt
from src.provider_pool import pooled_completion

# Mock Data (Representative of typical inputs)
TEST_MESSAGES = [
    # 1. Simple Straight Bet
    "### 101 [T] NBA\nLakers -5.5\nOdds: -110\n1U",
    # 2. Parlay (Complex)
    "### 102 [T] PARLAY (3 Picks)\n1. Chiefs -3.5\n2. Ravens ML\n3. Over 45.5 (KC/BUF)\nOdds: +600\n0.5U",
    # 3. Prop Bet
    "### 103 [T] NFL Prop\nTravis Kelce Over 6.5 Receptions (-120)\n2 Units",
    # 4. Messy / Unstructured
    "### 104 [T] max play alert!!!!\ngoing big on knicks ml tonight... brunson is back baby.\nplay: nyk moneyline\nodds: -130",
    # 5. Tennis (League Inference)
    "### 105 [T] Djokovic vs Sinner\nSinner ML +110",
    # 6. Soccer
    "### 106 [T] Premier League\nMan City/Arsenal Draw +250",
    # 7. Multiple Picks
    "### 107 [T] Picks for today:\n1. Heat -4\n2. Bulls +10\n3. Warriors ML",
    # 8. Late Night
    "### 108 [T] UFC 300\nPereira by KO/TKO +150",
    # 9. Typo Heavy
    "### 109 [T] NFl pik: 49ers -7 (-110) 5u",
    # 10. No Odds
    "### 110 [T] Celtics -2.5",
]


def run_benchmark():
    logger.info("Starting Benchmark Iteration 16...")
    logger.info(f"Test Set: {len(TEST_MESSAGES)} messages")

    results = []
    start_global = time.time()

    total_requests = 0
    successful = 0

    for i, raw_msg in enumerate(TEST_MESSAGES):
        logger.info(f"Processing Msg {i + 1}/{len(TEST_MESSAGES)}...")

        # Construct the prompt using the proper builder
        prompt = get_compact_extraction_prompt(raw_data=raw_msg)

        start_t = time.time()
        # Call Provider Pool
        # We don't have images in this text-only test
        response = pooled_completion(prompt, images=None, timeout=30)
        duration = time.time() - start_t

        total_requests += 1  # This is a simplification. pooled_completion might make multiple internally.

        is_success = False
        if response:
            try:
                data = json.loads(response)
                if isinstance(data, (dict, list)):
                    is_success = True
                    successful += 1
            except:
                pass

        results.append(
            {
                "id": i,
                "duration": duration,
                "success": is_success,
                "response_length": len(response) if response else 0,
            }
        )

    end_global = time.time()
    total_time = end_global - start_global
    avg_latency = total_time / len(TEST_MESSAGES)

    logger.info("=" * 40)
    logger.info("BENCHMARK RESULTS (BASELINE)")
    logger.info("=" * 40)
    logger.info(f"Total Requests: {total_requests}")  # External calls
    logger.info(f"Total Time:     {total_time:.2f}s")
    logger.info(f"Avg Latency:    {avg_latency:.2f}s")
    logger.info(f"Success Rate:   {successful}/{len(TEST_MESSAGES)} ({successful / len(TEST_MESSAGES) * 100:.1f}%)")
    logger.info("=" * 40)

    # Save Baseline
    with open("baseline_stats.txt", "w") as f:
        f.write(f"Total Requests: {total_requests}\n")
        f.write(f"Avg Latency: {avg_latency:.4f}\n")
        f.write(f"Success Rate: {successful / len(TEST_MESSAGES)}\n")


if __name__ == "__main__":
    run_benchmark()
