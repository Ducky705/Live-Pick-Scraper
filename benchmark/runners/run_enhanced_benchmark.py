"""
Enhanced Pipeline Benchmark Runner
===================================
Tests the IMPROVED pipeline with auto-classification vs baseline.

Key improvements tested:
1. Auto-classification of PICK vs PROMO/RECAP/DATA
2. Better handling of congested images
3. Reduced false positives from noise extraction
"""

import os
import sys
import json
import logging
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt
from src.auto_processor import classify_message_fast, PostClassification

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = os.path.join(BASE_DIR, "benchmark", "dataset")
IMAGE_MAP_PATH = os.path.join(DATASET_DIR, "image_map.json")
OCR_GOLDEN_SET_PATH = os.path.join(DATASET_DIR, "ocr_golden_set.json")
PARSING_GOLDEN_SET_PATH = os.path.join(DATASET_DIR, "parsing_golden_set.json")
RESULTS_DIR = os.path.join(BASE_DIR, "benchmark", "reports")

DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"


def fuzzy_match(gt_pick, sys_pick, gt_type="", sys_type=""):
    """Fuzzy match two pick strings."""
    if not gt_pick or not sys_pick:
        return False
    
    gt_norm = gt_pick.lower().strip()
    sys_norm = sys_pick.lower().strip()
    
    if gt_norm == sys_norm:
        return True
    
    if gt_norm in sys_norm or sys_norm in gt_norm:
        return True
    
    gt_tokens = set(gt_norm.split())
    sys_tokens = set(sys_norm.split())
    overlap = len(gt_tokens & sys_tokens)
    max_len = max(len(gt_tokens), len(sys_tokens))
    if max_len > 0 and overlap / max_len >= 0.6:
        return True
    
    return False


def calculate_metrics(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return {"precision": precision, "recall": recall, "f1": f1}


def run_enhanced_benchmark(model=None, limit=0):
    """
    Run benchmark with auto-classification pre-filter.
    """
    model = model or DEFAULT_MODEL
    
    # Load datasets
    with open(IMAGE_MAP_PATH, 'r', encoding='utf-8') as f:
        image_map = json.load(f)
    
    with open(OCR_GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        ocr_golden = json.load(f)
    
    with open(PARSING_GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        parsing_golden = json.load(f)
    
    # Metrics
    total_tp = 0
    total_fp = 0
    total_fn = 0
    latencies = []
    
    # Classification stats
    classification_stats = {
        "PICK": 0,
        "PROMO": 0,
        "RECAP": 0,
        "DATA": 0,
        "UNKNOWN": 0
    }
    
    images_to_test = list(image_map.keys())
    if limit > 0:
        images_to_test = images_to_test[:limit]
    
    logging.info(f"Starting ENHANCED Pipeline Benchmark with {len(images_to_test)} images")
    logging.info(f"Model: {model}")
    logging.info("-" * 60)
    
    for idx, img_key in enumerate(images_to_test):
        img_path = image_map.get(img_key)
        expected_picks = parsing_golden.get(img_key, [])
        ocr_text = ocr_golden.get(img_key, "")
        
        if not img_path or not os.path.exists(img_path):
            logging.warning(f"[{idx+1}] {img_key}: Image not found")
            continue
        
        logging.info(f"[{idx+1}/{len(images_to_test)}] Processing {img_key}...")
        
        start_time = time.time()
        
        # STEP 1: Auto-Classification using heuristics
        mock_message = {
            'id': idx + 1,
            'text': ocr_text,
            'images': [img_path]
        }
        classification_result = classify_message_fast(mock_message)
        classification = classification_result.get("class", "UNKNOWN")
        classification_stats[classification] = classification_stats.get(classification, 0) + 1
        
        logging.info(f"  Classification: {classification} ({classification_result.get('reason', '')})")
        
        # STEP 2: If classified as non-PICK, skip parsing (saves time & reduces FP)
        if classification not in [PostClassification.PICK, PostClassification.UNKNOWN]:
            logging.info(f"  -> Skipping parsing (classified as {classification})")
            # If ground truth has picks but we skipped, that's a FN
            if expected_picks:
                total_fn += len(expected_picks)
                logging.warning(f"  -> FALSE NEGATIVE: Skipped {len(expected_picks)} real picks!")
            continue
        
        # STEP 3: Parse with AI (same as baseline)
        try:
            if not ocr_text or len(ocr_text.strip()) < 10:
                logging.warning(f"  -> Empty OCR, skipping")
                total_fn += len(expected_picks)
                continue
            
            synthetic_message = {
                'id': idx + 1,
                'text': "",
                'ocr_texts': [ocr_text],
                'ocr_text': ocr_text
            }
            
            prompt = generate_ai_prompt([synthetic_message])
            response = openrouter_completion(prompt, model=model, timeout=60)
            
            latency = time.time() - start_time
            latencies.append(latency)
            
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
                parsed_picks = []
            
            # Score
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
            
            logging.info(f"  -> TP:{tp} FP:{fp} FN:{fn} (Latency: {latency:.1f}s)")
            
        except Exception as e:
            logging.error(f"  -> Error: {e}")
            total_fn += len(expected_picks)
    
    # Final metrics
    metrics = calculate_metrics(total_tp, total_fp, total_fn)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    results = {
        "config": {
            "model": model,
            "enhanced": True,
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
        "classification_stats": classification_stats
    }
    
    # Save
    os.makedirs(RESULTS_DIR, exist_ok=True)
    result_path = os.path.join(RESULTS_DIR, "full_pipeline_enhanced.json")
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("ENHANCED BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Images Tested: {len(images_to_test)}")
    print(f"Model: {model}")
    print("-" * 60)
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall:    {metrics['recall']:.2%}")
    print(f"F1 Score:  {metrics['f1']:.2%}")
    print(f"Avg Latency: {avg_latency:.2f}s")
    print("-" * 60)
    print(f"True Positives:  {total_tp}")
    print(f"False Positives: {total_fp}")
    print(f"False Negatives: {total_fn}")
    print("-" * 60)
    print("Classification Stats:")
    for cls, count in classification_stats.items():
        print(f"  {cls}: {count}")
    print("=" * 60)
    
    # Load baseline for comparison
    baseline_path = os.path.join(RESULTS_DIR, "full_pipeline_baseline.json")
    if os.path.exists(baseline_path):
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)
        
        baseline_f1 = baseline.get("metrics", {}).get("f1", 0)
        enhanced_f1 = metrics["f1"]
        
        print("\nCOMPARISON TO BASELINE:")
        print(f"  Baseline F1:  {baseline_f1:.2%}")
        print(f"  Enhanced F1:  {enhanced_f1:.2%}")
        print(f"  Improvement:  {(enhanced_f1 - baseline_f1) * 100:.2f} percentage points")
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    
    run_enhanced_benchmark(model=args.model, limit=args.limit)
