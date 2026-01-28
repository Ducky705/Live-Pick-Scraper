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
logger = logging.getLogger("Benchmark21")

from src.provider_pool import pooled_completion
from src.prompts.core import get_compact_extraction_prompt

# Mock Data (Expanded to 20 messages for better concurrency test)
TEST_MESSAGES = [
    "### 101 [T] NBA\nLakers -5.5\nOdds: -110\n1U",
    "### 102 [T] PARLAY (3 Picks)\n1. Chiefs -3.5\n2. Ravens ML\n3. Over 45.5 (KC/BUF)\nOdds: +600\n0.5U",
    "### 103 [T] NFL Prop\nTravis Kelce Over 6.5 Receptions (-120)\n2 Units",
    "### 104 [T] max play alert!!!!\ngoing big on knicks ml tonight... brunson is back baby.\nplay: nyk moneyline\nodds: -130",
    "### 105 [T] Djokovic vs Sinner\nSinner ML +110",
    "### 106 [T] Premier League\nMan City/Arsenal Draw +250",
    "### 107 [T] Picks for today:\n1. Heat -4\n2. Bulls +10\n3. Warriors ML",
    "### 108 [T] UFC 300\nPereira by KO/TKO +150",
    "### 109 [T] NFl pik: 49ers -7 (-110) 5u",
    "### 110 [T] Celtics -2.5",
    "### 111 [T] MLB\nYankees -1.5 (+110)",
    "### 112 [T] NHL\nBruins ML (-150)",
    "### 113 [T] Tennis\nAlcaraz 2-0 (-200)",
    "### 114 [T] Soccer\nReal Madrid ML (-120)",
    "### 115 [T] NFL\nEagles -3 (-110)",
    "### 116 [T] NBA\nWarriors Over 235.5",
    "### 117 [T] UFC\nO'Malley by Decision (+250)",
    "### 118 [T] NCAA\nPurdue -12.5",
    "### 119 [T] NFL Prop\nMahomes Over 280.5 Yards",
    "### 120 [T] NBA Prop\nLeBron Over 25.5 Points",
]


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
            None, lambda: pooled_completion(prompt, images=None, timeout=30)
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
    # Iteration 21: High Concurrency Stress Test
    # Why: Unlock Groq parallelism (if safe)
    CONCURRENCY_LIMIT = 4  # Safe limit found in Iteration 21
    logger.info(
        f"Starting Ralph Wiggum Loop - Iteration 21 (High Concurrency={CONCURRENCY_LIMIT})..."
    )
    logger.info(f"Test Set: {len(TEST_MESSAGES)} messages")

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
    logger.info("BENCHMARK RESULTS (ITERATION 21)")
    logger.info("=" * 40)
    logger.info(f"Total Requests: {total_requests}")
    logger.info(f"Total Time:     {total_time:.2f}s")
    logger.info(f"Avg Latency:    {avg_latency:.2f}s (Wall Clock / N)")
    logger.info(
        f"Success Rate:   {successful}/{len(TEST_MESSAGES)} ({successful / len(TEST_MESSAGES) * 100:.1f}%)"
    )
    logger.info("=" * 40)

    with open("iteration_21_stats.txt", "w") as f:
        f.write(f"Total Requests: {total_requests}\n")
        f.write(f"Total Time: {total_time:.4f}\n")
        f.write(f"Avg Latency: {avg_latency:.4f}\n")
        f.write(f"Success Rate: {successful / len(TEST_MESSAGES)}\n")


def run_benchmark():
    asyncio.run(run_benchmark_async())


if __name__ == "__main__":
    run_benchmark()
