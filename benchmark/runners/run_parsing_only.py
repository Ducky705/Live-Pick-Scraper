import argparse
import json
import logging
import os
import sys
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt
from src.prompts.decoder import normalize_response


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


def calculate_f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    return 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

OCR_GOLDEN_SET_PATH = os.path.join("benchmark", "dataset", "ocr_golden_set.json")
PARSING_GOLDEN_SET_PATH = os.path.join("benchmark", "dataset", "parsing_golden_set.json")
RESULTS_DIR = os.path.join("benchmark", "reports")

MODELS_TO_TEST = [
    "xiaomi/mimo-v2-flash:free",
    "mistralai/devstral-2512:free",
    "tngtech/deepseek-r1t2-chimera:free",
    "nex-agi/deepseek-v3.1-nex-n1:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "z-ai/glm-4.5-air:free",
    "deepseek/deepseek-r1-0528:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "openai/gpt-oss-120b:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]


def run_parsing_benchmark(specific_model=None, limit=0):
    if not os.path.exists(OCR_GOLDEN_SET_PATH) or not os.path.exists(PARSING_GOLDEN_SET_PATH):
        print("Error: Golden Sets not found. Please generate them first.")
        return

    # Define directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATASET_DIR = os.path.join(BASE_DIR, "benchmark", "dataset")

    # Load Image Map for context if needed (optional for parsing only but good for debug)
    # Load OCR Golden Set for Input Text (CRITICAL)
    with open(OCR_GOLDEN_SET_PATH, encoding="utf-8") as f:
        ocr_inputs = json.load(f)

    with open(PARSING_GOLDEN_SET_PATH, encoding="utf-8") as f:
        ground_truth_json = json.load(f)

    # Load existing results if available to allow resuming
    overall_results = {}
    if os.path.exists(os.path.join(RESULTS_DIR, "parsing_benchmark_results.json")):
        try:
            with open(os.path.join(RESULTS_DIR, "parsing_benchmark_results.json")) as f:
                overall_results = json.load(f)
        except:
            overall_results = {}

    models = [specific_model] if specific_model else MODELS_TO_TEST

    for model in models:
        if model in overall_results and specific_model is None:
            print(f"Skipping {model} (already tested).", flush=True)
            continue

        print(f"\nTesting Model: {model}", flush=True)
        print("-" * 40, flush=True)

        try:
            model_metrics = {"tp": 0, "fp": 0, "fn": 0, "latency": []}

            count = 0
            for i, (filename, expected_picks) in enumerate(ground_truth_json.items()):
                if limit > 0 and count >= limit:
                    break
                count += 1

                # Get Input Text from OCR Golden Set
                raw_text = ocr_inputs.get(filename, "")
                if not raw_text:
                    print(f"[{i + 1}] Skipping {filename}: No OCR text found.", flush=True)
                    continue

                # Build Prompt
                synthetic_message = {"id": i + 1, "text": "", "ocr_texts": [raw_text], "ocr_text": raw_text}

                final_prompt = generate_ai_prompt([synthetic_message])

                try:
                    start_time = time.time()
                    # SHORT TIMEOUT
                    response = openrouter_completion(final_prompt, model=model, timeout=45)
                    latency = time.time() - start_time
                    model_metrics["latency"].append(latency)

                    # Parse using the central decoder (handles DSL and JSON)
                    parsed_picks = normalize_response(response)

                    # DEBUG: Print response if low count
                    if i < 3:
                        print(f"DEBUG: Response for {filename}:\n{response}\nParsed: {parsed_picks}", flush=True)

                    # Score Locally

                    matched_gt = set()
                    matched_sys = set()
                    tp_local = 0

                    for gi, gp in enumerate(expected_picks):
                        gt_pick = gp.get("p", "")
                        gt_type = gp.get("ty", "")
                        for si, sp in enumerate(parsed_picks):
                            if si in matched_sys:
                                continue
                            sys_pick = sp.get("p") or sp.get("pick") or ""
                            sys_type = sp.get("ty") or sp.get("type") or ""
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

                except Exception as e:
                    print(f"  Error on {filename}: {e}", flush=True)

            # Aggregate Results for this Model
            f1 = calculate_f1(model_metrics["tp"], model_metrics["fp"], model_metrics["fn"])
            avg_latency = (
                sum(model_metrics["latency"]) / len(model_metrics["latency"]) if model_metrics["latency"] else 0
            )

            print(f"MODEL RESULT: {model} -> F1: {f1:.2%} (Avg Latency: {avg_latency:.2f}s)", flush=True)

            overall_results[model] = {
                "f1": f1,
                "precision": calculate_precision(model_metrics["tp"], model_metrics["fp"]),
                "recall": calculate_recall(model_metrics["tp"], model_metrics["fn"]),
                "avg_latency": avg_latency,
            }

            # SAVE INCREMENTALLY
            with open(os.path.join(RESULTS_DIR, "parsing_benchmark_results.json"), "w") as f:
                json.dump(overall_results, f, indent=2)

        except Exception as e:
            print(f"CRITICAL ERROR testing model {model}: {e}", flush=True)
            continue


def calculate_precision(tp, fp):
    return tp / (tp + fp) if (tp + fp) > 0 else 0


def calculate_recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) > 0 else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, help="Specific model to run")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of images to test per model")
    args = parser.parse_args()

    run_parsing_benchmark(args.model, args.limit)
