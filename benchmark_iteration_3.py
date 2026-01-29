import logging
import os
import sys
import time

# Setup
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("Benchmark03")

try:
    from src.extraction_pipeline import ExtractionPipeline
except ImportError:
    logger.error("Could not import src modules. Ensure running from root.")
    sys.exit(1)

# Mock Data (Same as Iteration 2 for Comparison)
TEST_MESSAGES = [
    {
        "id": 101,
        "text": "### 101 [T] NBA\nLakers -5.5\nOdds: -110\n1U",
        "date": "2024-01-28",
    },
    {
        "id": 102,
        "text": "### 102 [T] PARLAY (3 Picks)\n1. Chiefs -3.5\n2. Ravens ML\n3. Over 45.5 (KC/BUF)\nOdds: +600\n0.5U",
        "date": "2024-01-28",
    },
    {
        "id": 103,
        "text": "### 103 [T] NFL Prop\nTravis Kelce Over 6.5 Receptions (-120)\n2 Units",
        "date": "2024-01-28",
    },
    {
        "id": 104,
        "text": "### 104 [T] max play alert!!!!\ngoing big on knicks ml tonight... brunson is back baby.\nplay: nyk moneyline\nodds: -130",
        "date": "2024-01-28",
    },
    {
        "id": 105,
        "text": "### 105 [T] Djokovic vs Sinner\nSinner ML +110",
        "date": "2024-01-28",
    },
]


def run_benchmark():
    logger.info("Starting Ralph Wiggum Loop - Iteration 3 (Optimization: Round Robin Strategy)...")
    logger.info(f"Test Set: {len(TEST_MESSAGES)} messages")
    logger.info("Testing Strategy: Round Robin (Mixed Providers, Max Parallelism)")

    start_global = time.time()

    # Run Pipeline
    try:
        # Use strategy="round_robin" to test the 25-worker pool
        picks = ExtractionPipeline.run(
            TEST_MESSAGES,
            target_date="2024-01-28",
            batch_size=5,
            strategy="round_robin",
        )
        success = True
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        picks = []
        success = False

    end_global = time.time()
    total_time = end_global - start_global
    avg_latency = total_time / len(TEST_MESSAGES)

    successful_picks = len(picks)

    logger.info("=" * 40)
    logger.info("BENCHMARK RESULTS (ITERATION 3)")
    logger.info("=" * 40)
    logger.info(f"Total Time:     {total_time:.2f}s")
    logger.info(f"Avg Latency:    {avg_latency:.2f}s")
    logger.info(f"Total Picks:    {successful_picks}")
    logger.info("=" * 40)

    # Save Stats
    with open("iteration_3_stats.txt", "w") as f:
        f.write(f"Total Requests: {len(TEST_MESSAGES)}\n")
        f.write(f"Avg Latency: {avg_latency:.4f}\n")
        f.write(f"Total Picks: {successful_picks}\n")


if __name__ == "__main__":
    run_benchmark()
