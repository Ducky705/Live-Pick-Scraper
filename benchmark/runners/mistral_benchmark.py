import argparse
import json
import logging
import os
import sys
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.mistral_client import mistral_completion
from src.prompt_builder import generate_ai_prompt

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

OCR_GOLDEN_SET_PATH = os.path.join("benchmark", "dataset", "ocr_golden_set.json")
PARSING_GOLDEN_SET_PATH = os.path.join("benchmark", "dataset", "parsing_golden_set.json")
IMAGE_MAP_PATH = os.path.join("benchmark", "dataset", "image_map.json")
RESULTS_DIR = os.path.join("benchmark", "reports")


def calculate_similarity(s1, s2):
    """Calculate normalized similarity between two strings (0.0 to 1.0)."""
    if not s1 or not s2:
        return 0.0

    # Simple Jaccard similarity on tokens for robustness against whitespace/formatting
    tokens1 = set(s1.lower().split())
    tokens2 = set(s2.lower().split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)

    return intersection / union if union > 0 else 0.0


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
    if precision + recall == 0:
        return 0
    return 2 * (precision * recall) / (precision + recall)


def calculate_precision(tp, fp):
    return tp / (tp + fp) if (tp + fp) > 0 else 0


def calculate_recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) > 0 else 0


def run_mistral_benchmark(limit=10, run_ocr_test=False):
    if not os.path.exists(OCR_GOLDEN_SET_PATH) or not os.path.exists(PARSING_GOLDEN_SET_PATH):
        print("Error: Golden Sets not found.")
        return

    # Load Golden Sets
    with open(OCR_GOLDEN_SET_PATH, encoding="utf-8") as f:
        ocr_inputs = json.load(f)

    with open(PARSING_GOLDEN_SET_PATH, encoding="utf-8") as f:
        ground_truth_json = json.load(f)

    # Load Image Map
    image_map = {}
    if os.path.exists(IMAGE_MAP_PATH):
        with open(IMAGE_MAP_PATH, encoding="utf-8") as f:
            image_map = json.load(f)

    # Models to test
    models_to_test = [
        {"name": "Mistral Small (Latest)", "id": "mistral-small-latest"},
        {"name": "Mistral Large (Latest)", "id": "mistral-large-latest"},
        {"name": "Codestral (Latest)", "id": "codestral-latest"},
        {"name": "Ministral 8B", "id": "ministral-8b-latest"},
        # Vision models (if we were testing vision, but for now we test parsing logic)
    ]

    if run_ocr_test:
        models_to_test = [
            {"name": "Pixtral 12B", "id": "pixtral-12b-2409"},
            {"name": "Pixtral Large", "id": "pixtral-large-latest"},
        ]

    results = {}

    print(f"\nSTARTING MISTRAL BENCHMARK (Limit: {limit} samples)", flush=True)

    for competitor in models_to_test:
        model_name = competitor["name"]
        model_id = competitor["id"]

        print(f"\nTesting {model_name}...", flush=True)

        model_metrics = {"tp": 0, "fp": 0, "fn": 0, "latency": [], "success_count": 0, "fail_count": 0}
        ocr_scores = []

        count = 0
        for i, (filename, expected_picks) in enumerate(ground_truth_json.items()):
            if limit > 0 and count >= limit:
                break
            count += 1

            raw_text = ocr_inputs.get(filename, "")

            try:
                start_time = time.time()
                response = None

                if run_ocr_test:
                    # Vision Test (Image-to-Text)
                    # Resolve image path
                    image_path = image_map.get(filename)
                    if not image_path or not os.path.exists(image_path):
                        # Try to construct default path if not in map
                        base_image_path = os.path.join("benchmark", "dataset", "images", filename)
                        if os.path.exists(base_image_path):
                            image_path = base_image_path
                        else:
                            print(f"  [{count}/{limit}] Skipping {filename}: Image not found", flush=True)
                            continue

                    prompt = (
                        "Extract all text from this image exactly as it appears. "
                        "Return a JSON object with a single key 'text' containing the extracted string."
                    )

                    response_raw = mistral_completion(prompt, model=model_id, image_input=image_path, timeout=60)

                    # Mistral wrapper returns JSON string or text?
                    # Our wrapper attempts to extract valid JSON.

                    extracted_text = ""
                    if response_raw:
                        try:
                            # Try to parse as JSON first
                            if response_raw.strip().startswith("{"):
                                data = json.loads(response_raw)
                                extracted_text = data.get("text", "")
                            else:
                                extracted_text = response_raw
                        except:
                            extracted_text = response_raw

                    latency = time.time() - start_time
                    model_metrics["latency"].append(latency)

                    # Calculate Similarity Score (Ground Truth Text vs Extracted Text)
                    score = calculate_similarity(raw_text, extracted_text)
                    ocr_scores.append(score)

                    print(
                        f"  [{count}/{limit}] {filename}: Latency={latency:.2f}s | Similarity={score:.2%}", flush=True
                    )

                else:
                    # Parsing Test (Text-to-JSON)
                    synthetic_message = {"id": i + 1, "text": "", "ocr_texts": [raw_text], "ocr_text": raw_text}
                    final_prompt = generate_ai_prompt([synthetic_message])

                    response = mistral_completion(final_prompt, model=model_id, timeout=45)

                    latency = time.time() - start_time
                    model_metrics["latency"].append(latency)

                    # Parse JSON
                    if response:
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
                    else:
                        parsed_picks = []
                        model_metrics["fail_count"] += 1

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

                    print(
                        f"  [{count}/{limit}] {filename}: Latency={latency:.2f}s | TP={tp_local} FP={fp_local} FN={fn_local}",
                        flush=True,
                    )

            except Exception as e:
                print(f"  [{count}/{limit}] Error: {e}", flush=True)
                model_metrics["fail_count"] += 1

        # Calculate metrics
        avg_latency = sum(model_metrics["latency"]) / len(model_metrics["latency"]) if model_metrics["latency"] else 0

        if run_ocr_test:
            avg_similarity = sum(ocr_scores) / len(ocr_scores) if ocr_scores else 0
            results[model_name] = {"avg_similarity": avg_similarity, "avg_latency": avg_latency}
        else:
            f1 = calculate_f1(model_metrics["tp"], model_metrics["fp"], model_metrics["fn"])
            results[model_name] = {
                "f1": f1,
                "precision": calculate_precision(model_metrics["tp"], model_metrics["fp"]),
                "recall": calculate_recall(model_metrics["tp"], model_metrics["fn"]),
                "avg_latency": avg_latency,
                "success_rate": model_metrics["success_count"] / count if count > 0 else 0,
            }

    # Print Summary
    print("\n" + "=" * 60)
    print("MISTRAL BENCHMARK RESULTS SUMMARY")
    print("=" * 60)

    if run_ocr_test:
        print(f"{'Model':<25} | {'Avg Similarity':<15} | {'Latency':<10}")
        print("-" * 60)
        for name, metrics in results.items():
            print(f"{name:<25} | {metrics['avg_similarity']:.2%}         | {metrics['avg_latency']:.2f}s")
    else:
        print(f"{'Model':<25} | {'F1 Score':<10} | {'Latency':<10} | {'Success Rate':<12}")
        print("-" * 60)
        for name, metrics in results.items():
            print(
                f"{name:<25} | {metrics['f1']:.2%}    | {metrics['avg_latency']:.2f}s      | {metrics['success_rate']:.0%}"
            )
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Limit number of images to test")
    parser.add_argument("--ocr", action="store_true", help="Run OCR test instead of Parsing test")
    args = parser.parse_args()

    run_mistral_benchmark(args.limit, args.ocr)
