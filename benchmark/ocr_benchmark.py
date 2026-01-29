"""
OCR Vision Model Benchmark
==========================
Benchmarks ALL models from user-specified providers to find which support vision:

GROQ (testing all):
- llama-3.1-8b-instant
- llama-3.3-70b-versatile
- meta-llama/llama-guard-4-12b (20MB file support)
- openai/gpt-oss-120b
- openai/gpt-oss-20b

CEREBRAS (testing all):
- llama3.1-8b
- llama-3.3-70b
- gpt-oss-120b
- qwen-3-32b

OPENROUTER:
- google/gemini-2.0-flash-exp:free
- google/gemma-3-12b-it:free
- google/gemma-3-27b-it:free

MISTRAL:
- pixtral-large-latest

Usage:
    python -m benchmark.ocr_benchmark --limit 5 --parallel
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import requests

# Setup paths
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# --- CONFIGURATION ---

MODELS_TO_BENCHMARK = [
    # Tesseract (local baseline)
    {"provider": "tesseract", "model": "tesseract-v3", "name": "Tesseract (local)"},
    # OpenRouter models
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-exp:free", "name": "OR Gemini 2.0 Flash"},
    {"provider": "openrouter", "model": "google/gemma-3-12b-it:free", "name": "OR Gemma 3 12B"},
    {"provider": "openrouter", "model": "google/gemma-3-27b-it:free", "name": "OR Gemma 3 27B"},
    # Groq models - testing ALL from user's list
    {"provider": "groq", "model": "llama-3.1-8b-instant", "name": "Groq Llama 3.1 8B"},
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "name": "Groq Llama 3.3 70B"},
    {"provider": "groq", "model": "meta-llama/llama-guard-4-12b", "name": "Groq Guard 4 12B"},
    {"provider": "groq", "model": "openai/gpt-oss-120b", "name": "Groq GPT-OSS 120B"},
    {"provider": "groq", "model": "openai/gpt-oss-20b", "name": "Groq GPT-OSS 20B"},
    # Cerebras models - testing ALL from user's list
    {"provider": "cerebras", "model": "llama3.1-8b", "name": "Cerebras Llama 3.1 8B"},
    {"provider": "cerebras", "model": "llama-3.3-70b", "name": "Cerebras Llama 3.3 70B"},
    {"provider": "cerebras", "model": "gpt-oss-120b", "name": "Cerebras GPT-OSS 120B"},
    {"provider": "cerebras", "model": "qwen-3-32b", "name": "Cerebras Qwen 3 32B"},
    # Mistral
    {"provider": "mistral", "model": "pixtral-large-latest", "name": "Mistral Pixtral Large"},
]

STRUCTURED_PROMPT = """Extract betting information from this image.

Return JSON:
{
  "capper": "name if visible, else null",
  "text": "all readable text from the image",
  "picks": ["pick 1 exactly as written", "pick 2"]
}

IMPORTANT:
- Extract ALL text, especially team names, spreads (+/-X.X), totals (over/under), odds
- IGNORE watermarks like @cappersfree
- If multiple picks, list them all in the picks array"""


@dataclass
class BenchmarkResult:
    """Result from a single model test."""

    image: str
    provider: str
    model: str
    name: str
    time_ms: int
    text_length: int
    picks_count: int
    success: bool
    error: str | None = None


def encode_image(image_path: str) -> str | None:
    """Encode image to base64."""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def count_picks(text: str) -> int:
    """Rough count of picks in extracted text."""
    if not text:
        return 0

    count = 0
    indicators = [
        "over",
        "under",
        "spread",
        "moneyline",
        "ml",
        "+1",
        "+2",
        "+3",
        "+4",
        "+5",
        "+6",
        "+7",
        "+8",
        "+9",
        "-1",
        "-2",
        "-3",
        "-4",
        "-5",
        "-6",
        "-7",
        "-8",
        "-9",
        "lakers",
        "celtics",
        "warriors",
        "chiefs",
        "eagles",
        "bills",
        "cowboys",
        "niners",
        "49ers",
        "ravens",
    ]

    text_lower = text.lower()
    for ind in indicators:
        if ind in text_lower:
            count += 1

    return min(count, 10)


def run_tesseract(image_path: str) -> tuple:
    """Run Tesseract OCR."""
    try:
        from src.ocr_cascade import _run_tesseract

        result = _run_tesseract(image_path)
        return result.text, result.error
    except Exception as e:
        return "", str(e)


def run_openrouter(image_path: str, model: str, prompt: str) -> tuple:
    """Run OpenRouter model."""
    try:
        from src.openrouter_client import openrouter_completion

        b64 = encode_image(image_path)
        if not b64:
            return "", "Failed to encode image"

        response = openrouter_completion(prompt, model=model, images=[b64], validate_json=False)
        return response or "", None if response else "Empty response"
    except Exception as e:
        return "", str(e)


def run_groq_direct(image_path: str, model: str, prompt: str) -> tuple:
    """Run Groq model with direct API call to test vision support."""
    api_key = os.getenv("GROQ_TOKEN")
    if not api_key:
        return "", "GROQ_TOKEN not set"

    try:
        b64 = encode_image(image_path)
        if not b64:
            return "", "Failed to encode image"

        # Try multimodal format first
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
            "temperature": 0.1,
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content, None
        else:
            error_msg = response.json().get("error", {}).get("message", response.text[:100])
            return "", f"HTTP {response.status_code}: {error_msg}"

    except Exception as e:
        return "", str(e)


def run_cerebras_direct(image_path: str, model: str, prompt: str) -> tuple:
    """Run Cerebras model with direct API call to test vision support."""
    api_key = os.getenv("CEREBRAS_TOKEN")
    if not api_key:
        return "", "CEREBRAS_TOKEN not set"

    try:
        b64 = encode_image(image_path)
        if not b64:
            return "", "Failed to encode image"

        # Try multimodal format
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
            "temperature": 0.1,
        }

        response = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content, None
        else:
            error_msg = response.json().get("error", {}).get("message", response.text[:100])
            return "", f"HTTP {response.status_code}: {error_msg}"

    except Exception as e:
        return "", str(e)


def run_mistral(image_path: str, model: str, prompt: str) -> tuple:
    """Run Mistral model."""
    try:
        from src.mistral_client import mistral_completion

        response = mistral_completion(prompt, model=model, image_input=image_path, validate_json=False)
        return response or "", None if response else "Empty response"
    except Exception as e:
        return "", str(e)


def run_single_test(image_path: str, config: dict) -> BenchmarkResult:
    """Run a single model on a single image."""
    provider = config["provider"]
    model = config["model"]
    name = config["name"]

    start = time.time()
    text = ""
    error = None

    try:
        if provider == "tesseract":
            text, error = run_tesseract(image_path)
        elif provider == "openrouter":
            text, error = run_openrouter(image_path, model, STRUCTURED_PROMPT)
        elif provider == "groq":
            text, error = run_groq_direct(image_path, model, STRUCTURED_PROMPT)
        elif provider == "cerebras":
            text, error = run_cerebras_direct(image_path, model, STRUCTURED_PROMPT)
        elif provider == "mistral":
            text, error = run_mistral(image_path, model, STRUCTURED_PROMPT)
        else:
            error = f"Unknown provider: {provider}"
    except Exception as e:
        error = str(e)

    elapsed = int((time.time() - start) * 1000)
    picks = count_picks(text)

    return BenchmarkResult(
        image=os.path.basename(image_path),
        provider=provider,
        model=model,
        name=name,
        time_ms=elapsed,
        text_length=len(text) if text else 0,
        picks_count=picks,
        success=bool(text) and not error,
        error=error,
    )


def run_benchmark(limit: int = 5, parallel: bool = True):
    """Run full benchmark."""
    # Find images
    images_dir = os.path.join(BASE_DIR, "benchmark", "dataset", "images")
    if not os.path.exists(images_dir):
        images_dir = os.path.join(BASE_DIR, "temp_images")

    if not os.path.exists(images_dir):
        print("ERROR: Images directory not found")
        return

    images = [os.path.join(images_dir, f) for f in os.listdir(images_dir) if f.endswith((".jpg", ".jpeg", ".png"))][
        :limit
    ]

    if not images:
        print("ERROR: No images found")
        return

    print(f"\n{'=' * 80}")
    print("OCR VISION MODEL BENCHMARK")
    print(f"{'=' * 80}")
    print(f"Images: {len(images)}")
    print(f"Models: {len(MODELS_TO_BENCHMARK)}")
    print(f"Parallel: {parallel}")
    print(f"{'=' * 80}\n")

    all_results = []
    start_time = time.time()

    if parallel:
        # Run all tests in parallel
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []

            for img in images:
                for config in MODELS_TO_BENCHMARK:
                    futures.append(executor.submit(run_single_test, img, config))

            for future in as_completed(futures):
                result = future.result()
                all_results.append(result)

                status = "OK" if result.success else f"FAIL: {result.error[:40] if result.error else 'unknown'}"
                print(f"[{result.name:<25}] {result.time_ms:>6}ms | picks={result.picks_count} | {status}")
    else:
        # Sequential
        for img in images:
            print(f"\n--- {os.path.basename(img)} ---")
            for config in MODELS_TO_BENCHMARK:
                result = run_single_test(img, config)
                all_results.append(result)

                status = "OK" if result.success else "FAIL"
                print(f"  [{result.name:<25}] {result.time_ms:>6}ms | picks={result.picks_count} | {status}")

    total_time = time.time() - start_time

    # Aggregate stats
    print(f"\n{'=' * 80}")
    print("SUMMARY BY MODEL")
    print(f"{'=' * 80}")

    stats = {}
    for r in all_results:
        key = r.name
        if key not in stats:
            stats[key] = {
                "provider": r.provider,
                "model": r.model,
                "count": 0,
                "total_time": 0,
                "total_picks": 0,
                "successes": 0,
                "failures": 0,
                "errors": [],
            }

        s = stats[key]
        s["count"] += 1
        s["total_time"] += r.time_ms
        s["total_picks"] += r.picks_count
        if r.success:
            s["successes"] += 1
        else:
            s["failures"] += 1
            if r.error and r.error not in s["errors"]:
                s["errors"].append(r.error[:50])

    # Print table
    print(f"\n{'Model':<28} {'Avg Time':>10} {'Picks/Img':>10} {'Success':>10} {'Status':>15}")
    print("-" * 80)

    report_data = []

    # Sort by success rate, then speed
    sorted_stats = sorted(
        stats.items(), key=lambda x: (-x[1]["successes"] / x[1]["count"], x[1]["total_time"] / x[1]["count"])
    )

    for name, s in sorted_stats:
        avg_time = s["total_time"] / s["count"]
        avg_picks = s["total_picks"] / s["count"]
        success_rate = (s["successes"] / s["count"]) * 100

        # Determine status
        if success_rate < 20:
            status = "NO VISION"
        elif success_rate < 50:
            status = "UNRELIABLE"
        elif avg_time > 20000:
            status = "TOO SLOW"
        elif success_rate >= 80 and avg_picks >= 1:
            status = "GOOD"
        elif success_rate >= 80:
            status = "TEXT-ONLY"
        else:
            status = "OK"

        print(f"{name:<28} {avg_time:>8.0f}ms {avg_picks:>10.1f} {success_rate:>9.0f}% {status:>15}")

        report_data.append(
            {
                "name": name,
                "provider": s["provider"],
                "model": s["model"],
                "avg_time_ms": round(avg_time),
                "avg_picks": round(avg_picks, 1),
                "success_rate": round(success_rate, 1),
                "status": status,
                "total_tests": s["count"],
                "successes": s["successes"],
                "failures": s["failures"],
                "sample_errors": s["errors"][:2],
            }
        )

    print(f"\n{'=' * 80}")
    print(f"Total benchmark time: {total_time:.1f}s")
    print(f"{'=' * 80}")

    # Recommendations
    print("\n RECOMMENDATIONS:")

    good_models = [r for r in report_data if r["status"] == "GOOD"]
    no_vision = [r for r in report_data if r["status"] == "NO VISION"]
    text_only = [r for r in report_data if r["status"] == "TEXT-ONLY"]

    if good_models:
        fastest = min(good_models, key=lambda x: x["avg_time_ms"])
        print(
            f"  BEST MODEL: {fastest['name']} ({fastest['avg_time_ms']}ms, {fastest['success_rate']}% success, {fastest['avg_picks']} picks/img)"
        )

    if no_vision:
        print(f"  NO VISION SUPPORT: {', '.join(r['name'] for r in no_vision)}")

    if text_only:
        print(f"  TEXT-ONLY (no image processing): {', '.join(r['name'] for r in text_only)}")

    # Save report
    report_path = os.path.join(BASE_DIR, "benchmark", "reports", "ocr_benchmark_results.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_images": len(images),
                "total_time_seconds": round(total_time, 1),
                "results": report_data,
            },
            f,
            indent=2,
        )

    print(f"\nReport saved to: {report_path}")

    return report_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR Vision Model Benchmark")
    parser.add_argument("--limit", type=int, default=5, help="Number of images to test")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--sequential", action="store_true", help="Run tests sequentially")
    args = parser.parse_args()

    parallel = not args.sequential
    run_benchmark(limit=args.limit, parallel=parallel)
