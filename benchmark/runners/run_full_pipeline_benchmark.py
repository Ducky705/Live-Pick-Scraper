"""
Full Pipeline Benchmark Runner
Tests both OCR + Parsing as a complete pipeline against the golden dataset.
This simulates the REAL workflow: Image -> OCR -> Parse -> Compare to Ground Truth.

Key Metrics:
- Classification Accuracy: Does it correctly identify PICK vs NOISE?
- Extraction F1: For images classified as PICK, are the picks correct?
- Recall: Are we missing picks? (Critical for user's "100% accuracy" goal)
- Precision: Are we extracting garbage picks? (False positives)
"""

import os
import sys
import json
import logging
import time
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt, generate_compact_prompt
from src.provider_pool import pooled_completion
from src.ocr_handler import extract_text_batch

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = os.path.join(BASE_DIR, "benchmark", "dataset")
IMAGE_MAP_PATH = os.path.join(DATASET_DIR, "image_map.json")
OCR_GOLDEN_SET_PATH = os.path.join(DATASET_DIR, "ocr_golden_set.json")
PARSING_GOLDEN_SET_PATH = os.path.join(DATASET_DIR, "parsing_golden_set.json")
RESULTS_DIR = os.path.join(BASE_DIR, "benchmark", "reports")

# Default model (same as in openrouter_client.py)
DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"


def fuzzy_match(gt_pick, sys_pick, gt_type="", sys_type=""):
    """
    Fuzzy match two pick strings.
    Returns True if they are semantically similar.
    """
    if not gt_pick or not sys_pick:
        return False
    
    gt_norm = gt_pick.lower().strip()
    sys_norm = sys_pick.lower().strip()
    
    # Exact match
    if gt_norm == sys_norm:
        return True
    
    # Substring match (one contains the other)
    if gt_norm in sys_norm or sys_norm in gt_norm:
        return True
    
    # Token overlap (e.g., "Lakers +3" vs "Los Angeles Lakers +3")
    gt_tokens = set(gt_norm.split())
    sys_tokens = set(sys_norm.split())
    overlap = len(gt_tokens & sys_tokens)
    max_len = max(len(gt_tokens), len(sys_tokens))
    if max_len > 0 and overlap / max_len >= 0.6:
        return True
    
    return False


def calculate_metrics(tp, fp, fn):
    """Calculate precision, recall, F1"""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return {"precision": precision, "recall": recall, "f1": f1}


def run_full_pipeline_benchmark(use_vision_ocr=True, model=None, limit=0, save_name="baseline"):
    """
    Runs the full pipeline benchmark.
    
    Args:
        use_vision_ocr: If True, uses VLM for OCR. If False, uses Tesseract.
        model: The parsing model to use.
        limit: Limit number of images to test (0 = all).
        save_name: Name suffix for the results file.
    """
    model = model or DEFAULT_MODEL
    
    # Load datasets
    with open(IMAGE_MAP_PATH, 'r', encoding='utf-8') as f:
        image_map = json.load(f)
    
    with open(OCR_GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        ocr_golden = json.load(f)
    
    with open(PARSING_GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        parsing_golden = json.load(f)
    
    # Overall metrics
    total_tp = 0
    total_fp = 0
    total_fn = 0
    latencies = []
    per_image_results = {}
    
    images_to_test = list(image_map.keys())
    if limit > 0:
        images_to_test = images_to_test[:limit]
    
    logging.info(f"Starting Full Pipeline Benchmark with {len(images_to_test)} images")
    logging.info(f"Model: {model}")
    logging.info(f"Vision OCR: {use_vision_ocr}")
    logging.info("-" * 60)
    
    for idx, img_key in enumerate(images_to_test):
        img_path = image_map.get(img_key)
        expected_picks = parsing_golden.get(img_key, [])
        
        if not img_path or not os.path.exists(img_path):
            logging.warning(f"[{idx+1}/{len(images_to_test)}] {img_key}: Image not found at {img_path}")
            continue
        
        logging.info(f"[{idx+1}/{len(images_to_test)}] Processing {img_key}...")
        
        start_time = time.time()
        
        try:
            # Step 1: OCR
            if use_vision_ocr:
                # Use the VLM-based batch OCR
                ocr_results = extract_text_batch([img_path])
                ocr_text = ocr_results[0] if ocr_results else ""
            else:
                # Use golden OCR text (simulates perfect OCR for parsing-only test)
                ocr_text = ocr_golden.get(img_key, "")
            
            if not ocr_text or len(ocr_text.strip()) < 10:
                logging.warning(f"  -> Empty OCR result, skipping parsing")
                total_fn += len(expected_picks)
                continue
            
            # Step 2: Parsing - Use Hybrid Pool with compact prompt
            synthetic_message = {
                'id': idx + 1,
                'text': "",
                'ocr_texts': [ocr_text],
                'ocr_text': ocr_text
            }
            
            # Use compact prompt for faster parsing
            prompt = generate_compact_prompt([synthetic_message])
            
            # Use pooled_completion for hybrid strategy (fast first, then fallback)
            response = pooled_completion(prompt, timeout=60)
            
            latency = time.time() - start_time
            latencies.append(latency)
            
            if not response:
                logging.error(f"  -> No response from pool")
                total_fn += len(expected_picks)
                continue
            
            # Parse response
            cleaned = response.replace("```json", "").replace("```", "").strip()
            try:
                parsed_json = json.loads(cleaned)
                if isinstance(parsed_json, dict) and "picks" in parsed_json:
                    parsed_picks = parsed_json["picks"]
                elif isinstance(parsed_json, list):
                    parsed_picks = parsed_json
                else:
                    parsed_picks = []
            except json.JSONDecodeError:
                logging.error(f"  -> JSON parse error")
                parsed_picks = []
            
            # Step 3: Score against ground truth
            matched_gt = set()
            matched_sys = set()
            
            for gi, gp in enumerate(expected_picks):
                gt_pick = gp.get('p', '')
                gt_type = gp.get('ty', '')
                
                for si, sp in enumerate(parsed_picks):
                    if si in matched_sys:
                        continue
                    sys_pick = sp.get('p') or sp.get('pick') or ''
                    sys_type = sp.get('ty') or sp.get('type') or ''
                    
                    if fuzzy_match(gt_pick, sys_pick, gt_type, sys_type):
                        matched_gt.add(gi)
                        matched_sys.add(si)
                        break
            
            tp = len(matched_gt)
            fp = len(parsed_picks) - len(matched_sys)
            fn = len(expected_picks) - len(matched_gt)
            
            total_tp += tp
            total_fp += fp
            total_fn += fn
            
            per_image_results[img_key] = {
                "expected": len(expected_picks),
                "extracted": len(parsed_picks),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "latency": latency
            }
            
            logging.info(f"  -> TP:{tp} FP:{fp} FN:{fn} (Latency: {latency:.1f}s)")
            
        except Exception as e:
            logging.error(f"  -> Error: {e}")
            total_fn += len(expected_picks)
            continue
    
    # Calculate final metrics
    metrics = calculate_metrics(total_tp, total_fp, total_fn)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    results = {
        "config": {
            "model": model,
            "use_vision_ocr": use_vision_ocr,
            "images_tested": len(images_to_test)
        },
        "metrics": {
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_fn": total_fn,
            "avg_latency": avg_latency
        },
        "per_image": per_image_results
    }
    
    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    result_path = os.path.join(RESULTS_DIR, f"full_pipeline_{save_name}.json")
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"BENCHMARK RESULTS: {save_name}")
    print("=" * 60)
    print(f"Images Tested: {len(images_to_test)}")
    print(f"Model: {model}")
    print(f"Vision OCR: {use_vision_ocr}")
    print("-" * 60)
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall:    {metrics['recall']:.2%}")
    print(f"F1 Score:  {metrics['f1']:.2%}")
    print(f"Avg Latency: {avg_latency:.2f}s")
    print("-" * 60)
    print(f"True Positives:  {total_tp}")
    print(f"False Positives: {total_fp}")
    print(f"False Negatives: {total_fn}")
    print("=" * 60)
    print(f"Results saved to: {result_path}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full pipeline benchmark")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Parsing model to use")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of images (0=all)")
    parser.add_argument("--name", type=str, default="baseline", help="Name for results file")
    parser.add_argument("--no-vision", action="store_true", help="Use golden OCR instead of VLM")
    
    args = parser.parse_args()
    
    run_full_pipeline_benchmark(
        use_vision_ocr=not args.no_vision,
        model=args.model,
        limit=args.limit,
        save_name=args.name
    )
