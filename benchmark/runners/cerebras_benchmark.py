
import os
import sys
import json
import logging
import argparse
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.openrouter_client import openrouter_completion
from src.cerebras_client import cerebras_completion
from src.prompt_builder import generate_ai_prompt

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

OCR_GOLDEN_SET_PATH = os.path.join("benchmark", "dataset", "ocr_golden_set.json")
PARSING_GOLDEN_SET_PATH = os.path.join("benchmark", "dataset", "parsing_golden_set.json")
RESULTS_DIR = os.path.join("benchmark", "reports")

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

def calculate_f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    if precision + recall == 0: return 0
    return 2 * (precision * recall) / (precision + recall)

def calculate_precision(tp, fp):
    return tp / (tp + fp) if (tp + fp) > 0 else 0

def calculate_recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) > 0 else 0

def run_comparative_benchmark(limit=10):
    if not os.path.exists(OCR_GOLDEN_SET_PATH) or not os.path.exists(PARSING_GOLDEN_SET_PATH):
        print("Error: Golden Sets not found.")
        return

    # Define directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    with open(OCR_GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        ocr_inputs = json.load(f)
        
    with open(PARSING_GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        ground_truth_json = json.load(f)

    # Models to compare
    competitors = [
        {"name": "OpenRouter (Gemini 2.0 Flash)", "id": "google/gemini-2.0-flash-exp:free", "provider": "openrouter"},
        {"name": "Cerebras (Llama 3.3 70b)", "id": "llama-3.3-70b", "provider": "cerebras"}
    ]

    results = {}

    print(f"\nSTARTING COMPARATIVE BENCHMARK (Limit: {limit} samples)", flush=True)
    
    for competitor in competitors:
        model_name = competitor["name"]
        model_id = competitor["id"]
        provider = competitor["provider"]
        
        print(f"\nTesting {model_name}...", flush=True)
        
        model_metrics = {"tp": 0, "fp": 0, "fn": 0, "latency": [], "success_count": 0, "fail_count": 0}
        
        count = 0
        for i, (filename, expected_picks) in enumerate(ground_truth_json.items()):
            if limit > 0 and count >= limit:
                break
            count += 1
            
            raw_text = ocr_inputs.get(filename, "")
            if not raw_text:
                continue
            
            # Build Prompt
            synthetic_message = {
                'id': i + 1,
                'text': "", 
                'ocr_texts': [raw_text], 
                'ocr_text': raw_text
            }
            
            final_prompt = generate_ai_prompt([synthetic_message])
            
            try:
                start_time = time.time()
                
                if provider == "openrouter":
                    response = openrouter_completion(final_prompt, model=model_id, timeout=45)
                else:
                    response = cerebras_completion(final_prompt, model=model_id, timeout=45)
                
                latency = time.time() - start_time
                model_metrics["latency"].append(latency)
                
                # Parse JSON
                cleaned = response.replace("```json", "").replace("```", "").strip()
                try:
                    parsed_json = json.loads(cleaned)
                    if isinstance(parsed_json, dict) and "picks" in parsed_json:
                        parsed_picks = parsed_json["picks"]
                    elif isinstance(parsed_json, list):
                        parsed_picks = parsed_json
                    else:
                        parsed_picks = []
                    model_metrics["success_count"] += 1
                except:
                    parsed_picks = []
                    model_metrics["fail_count"] += 1

                # Score Locally
                matched_gt = set()
                matched_sys = set()
                tp_local = 0
                
                for gi, gp in enumerate(expected_picks):
                    gt_pick = gp.get('p', '')
                    gt_type = gp.get('ty', '')
                    for si, sp in enumerate(parsed_picks):
                        if si in matched_sys: continue
                        sys_pick = sp.get('p') or sp.get('pick') or ''
                        sys_type = sp.get('ty') or sp.get('type') or ''
                        if fuzzy_match(gt_pick, sys_pick, gt_type, sys_type):
                            matched_gt.add(gi)
                            matched_sys.add(si)
                            tp_local += 1
                            break
                            
                fp_local = len(parsed_picks) - len(matched_sys)
                fn_local = len(expected_picks) - len(matched_gt)
                
                model_metrics["tp"] += tp_local
                model_metrics["fp"] += fp_local
                model_metrics["fn"] += fn_local
                
                print(f"  [{count}/{limit}] {filename}: Latency={latency:.2f}s | TP={tp_local} FP={fp_local} FN={fn_local}", flush=True)
                
            except Exception as e:
                print(f"  [{count}/{limit}] Error: {e}", flush=True)
                model_metrics["fail_count"] += 1

        # Calculate metrics
        f1 = calculate_f1(model_metrics["tp"], model_metrics["fp"], model_metrics["fn"])
        avg_latency = sum(model_metrics["latency"]) / len(model_metrics["latency"]) if model_metrics["latency"] else 0
        
        results[model_name] = {
            "f1": f1,
            "precision": calculate_precision(model_metrics["tp"], model_metrics["fp"]),
            "recall": calculate_recall(model_metrics["tp"], model_metrics["fn"]),
            "avg_latency": avg_latency,
            "success_rate": model_metrics["success_count"] / count if count > 0 else 0
        }

    # Print Summary
    print("\n" + "="*60)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*60)
    print(f"{'Provider':<25} | {'F1 Score':<10} | {'Latency':<10} | {'Success Rate':<12}")
    print("-" * 60)
    for name, metrics in results.items():
        print(f"{name:<25} | {metrics['f1']:.2%}    | {metrics['avg_latency']:.2f}s      | {metrics['success_rate']:.0%}")
    print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Limit number of images to test")
    args = parser.parse_args()
    
    run_comparative_benchmark(args.limit)
