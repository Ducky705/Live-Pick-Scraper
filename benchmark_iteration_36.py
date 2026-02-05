import asyncio
import json
import logging
import os
import sys
import time
from typing import Any

# Setup
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("Benchmark36")

# Import the PIPELINE, not just the provider
from src.extraction_pipeline import ExtractionPipeline
from src.rule_based_extractor import RuleBasedExtractor

# Load Real Data
def load_golden_set():
    try:
        with open("new_golden_set.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("new_golden_set.json not found!")
        return []

GOLDEN_SET = load_golden_set()
# Use 10x multiplier to simulate load
TEST_MESSAGES = GOLDEN_SET * 10 if GOLDEN_SET else []

def run_pipeline_benchmark():
    # Iteration 36: The Hybrid System Test
    # Goal: Measure latency/throughput improvement of Rule Engine + AI Fallback
    # compared to pure AI (Iteration 35).
    
    logger.info("=" * 40)
    logger.info("BENCHMARK ITERATION 36: HYBRID PIPELINE")
    logger.info("=" * 40)
    
    if not TEST_MESSAGES:
        logger.error("No test messages loaded.")
        return

    total_msgs = len(TEST_MESSAGES)
    logger.info(f"Test Set: {total_msgs} MESSAGES")

    # Format messages for pipeline (Pipeline expects dicts)
    # Using 'groq' strategy to enable the fast fallback path
    
    start_time = time.time()
    
    # We run the pipeline synchronously effectively, as ExtractionPipeline.run is blocking/manages its own async
    # But wait, ExtractionPipeline.run is synchronous wrapper around parallel_processor?
    # Let's check ExtractionPipeline source. Yes, it's a synchronous method.
    
    try:
        # Mocking target date
        target_date = "2026-02-05"
        
        # Run the full beast
        picks = ExtractionPipeline.run(
            messages=TEST_MESSAGES, 
            target_date=target_date, 
            batch_size=5, # Optimization from prev iterations
            strategy="groq"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        avg_latency = duration / total_msgs if total_msgs > 0 else 0
        
        # Count Rule-Based vs AI
        # We can guess based on execution time or confidence metadata if available
        # But verify_rule_engine already told us ~84% coverage.
        
        logger.info("-" * 40)
        logger.info(f"Total Time:     {duration:.4f}s")
        logger.info(f"Avg Latency:    {avg_latency:.4f}s / msg")
        logger.info(f"Throughput:     {total_msgs / duration:.2f} msg/s")
        logger.info(f"Total Picks:    {len(picks)}")
        logger.info("-" * 40)
        
        # Save Stats
        with open("iteration_36_stats.txt", "w") as f:
            f.write(f"Total Requests: {total_msgs}\n")
            f.write(f"Total Time: {duration:.4f}\n")
            f.write(f"Avg Latency: {avg_latency:.4f}\n")
            f.write(f"Throughput: {total_msgs / duration:.4f}\n")
            
    except Exception as e:
        logger.error(f"Benchmark Failed: {e}", exc_info=True)

if __name__ == "__main__":
    run_pipeline_benchmark()
