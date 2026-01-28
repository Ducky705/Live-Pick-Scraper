import json
import time
import os
import logging
import psutil
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Configure Concurrency BEFORE importing pipeline to ensure it takes effect
import src.parallel_batch_processor

# Force Concurrency = 4 as requested
src.parallel_batch_processor.PROVIDER_CONFIG["groq"]["max_concurrent"] = 4
print("Configured Groq Concurrency to 4")

from src.extraction_pipeline import ExtractionPipeline

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("StressTest")


def monitor_memory():
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # MB
    except:
        return 0


def run_stress_test():
    # 1. Load Data
    dataset_path = "benchmark/dataset/stress_test_500.json"
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found.")
        return

    with open(dataset_path, "r") as f:
        all_messages = json.load(f)

    print(f"Loaded {len(all_messages)} messages.")

    # 2. Config
    CHUNK_SIZE = 50  # Process in chunks to measure drift
    total_chunks = len(all_messages) // CHUNK_SIZE
    if len(all_messages) % CHUNK_SIZE != 0:
        total_chunks += 1

    results = []

    print(f"Starting Stress Test with {len(all_messages)} messages, Concurrency=4")
    print("Monitoring: Memory, Latency Drift")

    start_time = time.time()
    initial_mem = monitor_memory()

    for i in range(total_chunks):
        chunk_idx = i
        start_idx = chunk_idx * CHUNK_SIZE
        end_idx = min((chunk_idx + 1) * CHUNK_SIZE, len(all_messages))
        chunk = all_messages[start_idx:end_idx]

        chunk_start = time.time()
        start_mem = monitor_memory()

        print(
            f"\n--- Running Chunk {chunk_idx + 1}/{total_chunks} ({len(chunk)} msgs) ---"
        )
        try:
            # We use batch_size=5 inside the pipeline for the AI requests
            # strategy="groq" uses the modified configuration
            picks = ExtractionPipeline.run(
                chunk, target_date="2024-01-01", batch_size=5, strategy="groq"
            )
            print(f"Extracted {len(picks)} picks from chunk.")
        except Exception as e:
            print(f"Chunk {chunk_idx + 1} failed: {e}")

        chunk_end = time.time()
        end_mem = monitor_memory()

        duration = chunk_end - chunk_start
        mem_diff = end_mem - start_mem

        print(
            f"Chunk {chunk_idx + 1}: Duration={duration:.2f}s, Mem={end_mem:.2f}MB (Diff: {mem_diff:+.2f}MB)"
        )

        results.append(
            {
                "chunk": chunk_idx + 1,
                "duration": duration,
                "memory": end_mem,
                "msg_count": len(chunk),
            }
        )

    total_time = time.time() - start_time
    print(f"\nTotal Time: {total_time:.2f}s")
    print(f"Initial Memory: {initial_mem:.2f}MB")
    print(f"Final Memory: {monitor_memory():.2f}MB")

    # Analyze for Drift
    if len(results) >= 2:
        first_half = results[: len(results) // 2]
        second_half = results[len(results) // 2 :]

        avg_first = sum(r["duration"] for r in first_half) / len(first_half)
        avg_second = sum(r["duration"] for r in second_half) / len(second_half)

        drift_factor = avg_second / avg_first if avg_first > 0 else 1.0

        print(f"\n--- Analysis ---")
        print(f"Avg Duration (First Half): {avg_first:.2f}s")
        print(f"Avg Duration (Second Half): {avg_second:.2f}s")
        print(f"Drift Factor: {drift_factor:.2f}x")

        if drift_factor > 1.5:
            print("WARNING: Significant Latency Drift Detected!")
        else:
            print("Latency appears stable.")

        # Check Memory Leak
        mem_start = results[0]["memory"]
        mem_end = results[-1]["memory"]
        if mem_end > mem_start * 1.2:
            print(
                f"WARNING: Memory usage increased by {(mem_end / mem_start - 1) * 100:.1f}%"
            )


if __name__ == "__main__":
    run_stress_test()
