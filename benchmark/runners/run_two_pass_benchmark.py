import difflib
import json
import logging
import os
import sys
import time

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv

from src.ocr_handler import extract_text_batch

# Load Env
load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def calculate_similarity(text1, text2):
    """Calculates similarity ratio between two strings (0.0 to 1.0)"""
    return difflib.SequenceMatcher(None, text1, text2).ratio()


def run_benchmark():
    # Load Paths
    dataset_dir = os.path.join(PROJECT_ROOT, "benchmark", "dataset")
    map_path = os.path.join(dataset_dir, "image_map.json")
    golden_path = os.path.join(dataset_dir, "ocr_golden_set.json")

    with open(map_path, encoding="utf-8") as f:
        image_map = json.load(f)

    with open(golden_path, encoding="utf-8") as f:
        golden_set = json.load(f)

    logging.info(f"Loaded {len(image_map)} images for benchmarking.")

    results = []
    total_time = 0
    total_sim = 0

    # Process images in batch to test real-world performance
    image_keys = list(image_map.keys())
    image_paths = [image_map[k] for k in image_keys]

    # Ensure paths are valid (some might be absolute/relative mix)
    valid_paths = []
    valid_keys = []

    for k, p in zip(image_keys, image_paths):
        # Fix path separator
        p = p.replace("/", os.sep).replace("\\", os.sep)
        if not os.path.isabs(p):
            p = os.path.join(PROJECT_ROOT, p)

        if os.path.exists(p):
            valid_paths.append(p)
            valid_keys.append(k)
        else:
            logging.warning(f"File not found: {p}")

    logging.info(f"Starting OCR Benchmark on {len(valid_paths)} images...")
    start_time = time.time()

    # Run Batch OCR (includes Two-Pass Logic)
    extracted_texts = extract_text_batch(valid_paths)

    end_time = time.time()
    total_time = end_time - start_time

    # Evaluate
    for i, key in enumerate(valid_keys):
        generated = extracted_texts[i]
        ground_truth = golden_set.get(key, "")

        similarity = calculate_similarity(generated, ground_truth)
        total_sim += similarity

        # Check if Two-Pass was triggered (log output would show it, but we can infer by quality?)
        # We rely on logs to see if "Retrying" happened.

        results.append(
            {
                "image": key,
                "similarity": round(similarity, 4),
                "length_gen": len(generated),
                "length_gt": len(ground_truth),
            }
        )

        logging.info(f"[{key}] Sim: {similarity:.4f} | Len: {len(generated)}/{len(ground_truth)}")

    avg_sim = total_sim / len(valid_keys) if valid_keys else 0
    avg_time = total_time / len(valid_keys) if valid_keys else 0

    print("\n" + "=" * 40)
    print("BENCHMARK RESULTS (Two-Pass System)")
    print("=" * 40)
    print(f"Total Images: {len(valid_keys)}")
    print(f"Total Time:   {total_time:.2f}s")
    print(f"Avg Time/Img: {avg_time:.2f}s")
    print(f"Avg Similarity: {avg_sim:.4f}")
    print("=" * 40)

    # Save Report
    report_path = os.path.join(PROJECT_ROOT, "benchmark", "reports", "two_pass_results.json")
    with open(report_path, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_images": len(valid_keys),
                    "total_time": total_time,
                    "avg_time": avg_time,
                    "avg_similarity": avg_sim,
                },
                "details": results,
            },
            f,
            indent=2,
        )

    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    run_benchmark()
