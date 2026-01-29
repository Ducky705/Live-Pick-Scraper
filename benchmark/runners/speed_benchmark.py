"""
Speed Benchmark for OCR Pipeline
Measures throughput (images/second) and total time.
Used to compare BEFORE and AFTER parallelization changes.
"""

import json
import logging
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = os.path.join(BASE_DIR, "benchmark", "dataset")
IMAGE_DIR = os.path.join(DATASET_DIR, "images")
RESULTS_DIR = os.path.join(BASE_DIR, "benchmark", "reports")


def run_speed_benchmark(limit=10, name="speed_test"):
    """
    Runs a speed benchmark on the OCR pipeline.

    Args:
        limit: Number of images to test
        name: Name for the results file
    """
    from src.ocr_handler import extract_text_batch

    # Get image paths
    all_images = [os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR) if f.endswith((".jpg", ".png", ".jpeg"))]

    if not all_images:
        logging.error("No images found in dataset!")
        return None

    images_to_test = all_images[:limit]

    logging.info("=" * 60)
    logging.info(f"SPEED BENCHMARK: {name}")
    logging.info("=" * 60)
    logging.info(f"Images to process: {len(images_to_test)}")
    logging.info("-" * 60)

    # Run OCR
    start_time = time.time()

    results = extract_text_batch(images_to_test)

    end_time = time.time()
    total_time = end_time - start_time

    # Calculate metrics
    successful = sum(1 for r in results if r and len(r) > 10)
    throughput = len(images_to_test) / total_time if total_time > 0 else 0
    avg_time_per_image = total_time / len(images_to_test) if images_to_test else 0

    # Build results
    benchmark_results = {
        "name": name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "images_tested": len(images_to_test),
        "successful_ocr": successful,
        "total_time_seconds": round(total_time, 2),
        "avg_time_per_image": round(avg_time_per_image, 2),
        "throughput_images_per_second": round(throughput, 3),
        "sample_results": [
            {"path": os.path.basename(images_to_test[i]), "text_length": len(results[i]) if results[i] else 0}
            for i in range(min(5, len(images_to_test)))
        ],
    }

    # Print summary
    logging.info("-" * 60)
    logging.info("RESULTS:")
    logging.info(f"  Total Time:      {total_time:.2f} seconds")
    logging.info(f"  Successful OCR:  {successful}/{len(images_to_test)}")
    logging.info(f"  Avg per Image:   {avg_time_per_image:.2f} seconds")
    logging.info(f"  Throughput:      {throughput:.3f} images/second")
    logging.info("=" * 60)

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    result_path = os.path.join(RESULTS_DIR, f"speed_{name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    logging.info(f"Results saved to: {result_path}")

    return benchmark_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run speed benchmark")
    parser.add_argument("--limit", type=int, default=10, help="Number of images to test")
    parser.add_argument("--name", type=str, default="baseline", help="Name for results file")

    args = parser.parse_args()

    run_speed_benchmark(limit=args.limit, name=args.name)
