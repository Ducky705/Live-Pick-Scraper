import argparse
import json
import logging
import os
import sys
import time
from difflib import SequenceMatcher

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.gemini_client import gemini_vision_completion
from src.groq_client import groq_vision_completion
from src.openrouter_client import openrouter_completion

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

DATASET_DIR = os.path.join("benchmark", "dataset")
IMAGES_DIR = os.path.join(DATASET_DIR, "images")
OCR_GOLDEN_SET_PATH = os.path.join(DATASET_DIR, "ocr_golden_set.json")
IMAGE_MAP_PATH = os.path.join(DATASET_DIR, "image_map.json")


def similarity_score(a, b):
    return SequenceMatcher(None, a, b).ratio()


def run_vision_benchmark(limit=10):
    if not os.path.exists(OCR_GOLDEN_SET_PATH) or not os.path.exists(IMAGE_MAP_PATH):
        print("Error: Golden Set or Image Map not found.")
        return

    # Load Golden Set
    with open(OCR_GOLDEN_SET_PATH, encoding="utf-8") as f:
        golden_set = json.load(f)

    # Load Image Map
    with open(IMAGE_MAP_PATH, encoding="utf-8") as f:
        image_map = json.load(f)

    # Filter for images that actually exist
    test_set = {}
    for k, v in golden_set.items():
        if k in image_map and os.path.exists(image_map[k]):
            test_set[k] = {"path": image_map[k], "expected": v}

    if not test_set:
        print("Error: No valid images found from image_map.")
        return

    competitors = [
        {"name": "OpenRouter (Gemini 2.0)", "id": "google/gemini-2.0-flash-exp:free", "provider": "openrouter"},
        {"name": "Groq (Llama 4)", "id": "meta-llama/llama-4-maverick-17b-128e-instruct", "provider": "groq"},
        {"name": "Gemini (2.5 Flash Lite)", "id": "gemini-2.5-flash-lite", "provider": "gemini"},
    ]

    results = {}

    print(f"\nSTARTING VISION BENCHMARK (Limit: {limit} samples)", flush=True)

    # Prompt for OCR
    prompt = "Extract all text from this image exactly as it appears. Return only the text."

    for competitor in competitors:
        model_name = competitor["name"]
        model_id = competitor["id"]
        provider = competitor["provider"]

        print(f"\nTesting {model_name}...", flush=True)

        metrics = {"score": 0, "latency": [], "success_count": 0, "fail_count": 0}

        count = 0
        for i, (key, data) in enumerate(test_set.items()):
            if limit > 0 and count >= limit:
                break

            filename = key
            image_path = data["path"]
            expected_text = data["expected"]
            count += 1

            try:
                # Rate limit pacing for free tier (15 RPM = 4s/req)
                if provider == "gemini":
                    time.sleep(4)

                start_time = time.time()
                response_text = None

                if provider == "openrouter":
                    # OpenRouter client handles base64 conversion internally if we pass path
                    # But we need to be careful about the response format.
                    # openrouter_completion usually expects JSON output if validate_json=True
                    # We'll turn off validation for raw OCR or ask for JSON.
                    # Let's ask for JSON to match the client's preference, or just use a custom prompt.
                    # Actually, let's use the robust client but allow raw text.
                    # The client forces JSON object usually.
                    # Let's wrap the prompt to ask for JSON: {"text": "..."}
                    json_prompt = 'Extract text from image. Return JSON: {"text": "<extracted_text>"}'
                    resp = openrouter_completion(
                        json_prompt, model=model_id, images=[image_path], timeout=60, validate_json=True
                    )
                    try:
                        response_text = json.loads(resp).get("text", "")
                    except:
                        response_text = resp  # Fallback

                elif provider == "gemini":
                    # Gemini Direct
                    response_text = gemini_vision_completion(prompt, image_path, model=model_id)

                elif provider == "groq":
                    # Groq Direct
                    # Groq usually returns JSON if we asked for response_format json_object
                    # We did set that in the client.
                    # So we should prompt for JSON.
                    json_prompt = 'Extract text from image. Return JSON: {"text": "<extracted_text>"}'
                    resp = groq_vision_completion(json_prompt, image_path, model=model_id)
                    if resp:
                        try:
                            response_text = json.loads(resp).get("text", "")
                        except:
                            response_text = resp  # Fallback

                latency = time.time() - start_time
                metrics["latency"].append(latency)

                if response_text:
                    metrics["success_count"] += 1
                    # Clean up
                    clean_resp = response_text.strip().lower()
                    clean_gold = expected_text.strip().lower()

                    # Calculate similarity
                    score = similarity_score(clean_resp, clean_gold)
                    metrics["score"] += score

                    print(f"  [{count}/{limit}] {filename}: Latency={latency:.2f}s | Quality={score:.2%}", flush=True)
                else:
                    metrics["fail_count"] += 1
                    print(f"  [{count}/{limit}] {filename}: FAILED", flush=True)

            except Exception as e:
                print(f"  [{count}/{limit}] Error: {e}", flush=True)
                metrics["fail_count"] += 1

        # Calculate metrics
        avg_latency = sum(metrics["latency"]) / len(metrics["latency"]) if metrics["latency"] else 0
        avg_score = metrics["score"] / metrics["success_count"] if metrics["success_count"] > 0 else 0

        results[model_name] = {
            "avg_score": avg_score,
            "avg_latency": avg_latency,
            "success_rate": metrics["success_count"] / count if count > 0 else 0,
        }

    # Print Summary
    print("\n" + "=" * 70)
    print("VISION BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Provider':<25} | {'Quality (Sim)':<15} | {'Latency':<10} | {'Success Rate':<12}")
    print("-" * 70)
    for name, m in results.items():
        print(f"{name:<25} | {m['avg_score']:.2%}           | {m['avg_latency']:.2f}s      | {m['success_rate']:.0%}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Limit number of images to test")
    args = parser.parse_args()

    run_vision_benchmark(args.limit)
