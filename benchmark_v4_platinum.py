import asyncio
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
logger = logging.getLogger("BenchmarkV4")

from src.extraction_pipeline import ExtractionPipeline

DATASET_FILE = "benchmark/dataset/golden_set_v4.json"

def load_dataset():
    try:
        with open(DATASET_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{DATASET_FILE} not found!")
        return []

def run_benchmark():
    logger.info("=" * 40)
    logger.info("PLATINUM BENCHMARK (V4) - 72 SAMPLES")
    logger.info("=" * 40)
    
    dataset = load_dataset()
    if not dataset:
        return

    TEST_MESSAGES = dataset
    total_msgs = len(dataset) * 10
    logger.info(f"Test Set: {len(dataset)} unique messages x 10 runs")

    start_time = time.time()
    
    total_picks = 0
    
    try:
        # Loop 10 times to verify Cache persistance across calls
        for i in range(10):
            logger.info(f"--- Run {i+1}/10 ---")
            run_start = time.time()
            picks = ExtractionPipeline.run(
                messages=TEST_MESSAGES, 
                target_date="2026-02-05", 
                batch_size=20, 
                strategy="groq"
            )
            run_dur = time.time() - run_start
            logger.info(f"Run {i+1} Duration: {run_dur:.4f}s - Picks: {len(picks)}")
            total_picks += len(picks)
        
        end_time = time.time()
        duration = end_time - start_time
        avg_latency = duration / total_msgs if total_msgs > 0 else 0
        
        logger.info("-" * 40)
        logger.info(f"Total Time:     {duration:.4f}s")
        logger.info(f"Avg Latency:    {avg_latency:.4f}s / msg")
        logger.info(f"Throughput:     {total_msgs / duration:.2f} msg/s")
        logger.info(f"Total Picks:    {len(picks)}")
        logger.info("-" * 40)
        
        # Save Stats
        with open("benchmark_v4_stats.txt", "w") as f:
            f.write(f"Total Requests: {total_msgs}\n")
            f.write(f"Total Time: {duration:.4f}\n")
            f.write(f"Avg Latency: {avg_latency:.4f}\n")
            f.write(f"Throughput: {total_msgs / duration:.4f}\n")
            
    except Exception as e:
        logger.error(f"Benchmark Failed: {e}", exc_info=True)

if __name__ == "__main__":
    run_benchmark()
