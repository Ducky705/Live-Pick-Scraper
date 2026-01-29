"""
Parser Model Benchmark
======================
Benchmarks LLM models for parsing betting picks from OCR text.

Tests:
- Cerebras (llama-3.3-70b)
- Groq (llama-3.3-70b-versatile)
- Mistral (mistral-large-latest)
- OpenRouter (deepseek-r1t2-chimera:free)

Usage:
    python -m benchmark.parser_benchmark [--samples N]
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import Any

# Setup paths
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# --- PARSER MODELS TO BENCHMARK ---

PARSER_MODELS = [
    {
        "name": "Cerebras Llama 3.3 70B",
        "provider": "cerebras",
        "model": "llama-3.3-70b",
    },
    {
        "name": "Groq Llama 3.3 70B",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
    },
    {
        "name": "Mistral Large",
        "provider": "mistral",
        "model": "mistral-large-latest",
    },
    {
        "name": "OpenRouter DeepSeek R1",
        "provider": "openrouter",
        "model": "tngtech/deepseek-r1t2-chimera:free",
    },
    {
        "name": "OpenRouter Devstral",
        "provider": "openrouter",
        "model": "mistralai/devstral-2512:free",
    },
]

# --- TEST SAMPLES ---
# Sample OCR text outputs from betting slip images

TEST_SAMPLES = [
    {
        "id": "sample_1",
        "ocr_text": """
PARLAY - 2 Picks
Lakers -4.5 (-110)
Celtics ML (-150)
Stake: 2 units
        """,
        "expected_picks": 2,
    },
    {
        "id": "sample_2",
        "ocr_text": """
NBA POTD
Golden State Warriors vs Dallas Mavericks
Pick: GSW -3.5
Odds: -110
Confidence: HIGH
        """,
        "expected_picks": 1,
    },
    {
        "id": "sample_3",
        "ocr_text": """
TODAY'S PLAYS:
1. Patriots +7 (-105) - NFL
2. Chiefs ML (-120) - NFL
3. Ravens/Bengals OVER 47.5 (-110) - NFL
BOL!
        """,
        "expected_picks": 3,
    },
    {
        "id": "sample_4",
        "ocr_text": """
MLB Free Play
Yankees vs Red Sox
Total: UNDER 8.5 runs
Odds: -115
@CappersFree
        """,
        "expected_picks": 1,
    },
    {
        "id": "sample_5",
        "ocr_text": """
NHL Lock of the Day
Toronto Maple Leafs ML
vs Montreal Canadiens
-145 | 3 units
Record: 42-18 (+24.5u)
        """,
        "expected_picks": 1,
    },
]

# --- PARSING PROMPT (Optimized for token efficiency) ---

PARSING_PROMPT = """Extract betting picks from text. Return JSON only.

KEYS:c=capper,l=league,t=type,p=pick,o=odds
TYPES:ML,SP,TL,PP,TP,GP,PD,PL,TS,FT,UK
LEAGUES:NFL,NBA,MLB,NHL,NCAAF,NCAAB,UFC,TENNIS,SOCCER,Other

RULES:
1.Extract ALL picks
2.null for unknown fields
3.Ignore promos,watermarks,records
4.SP=+/-X.X|TL=O/U X

TEXT:
{text}

OUTPUT:{{"picks":[{{"c":null,"l":"NBA","p":"GSW -3.5","t":"SP","o":"-110"}}]}}"""


def call_cerebras(prompt: str, model: str) -> str | None:
    """Call Cerebras API."""
    try:
        from src.cerebras_client import cerebras_completion

        return cerebras_completion(prompt, model=model, timeout=60)
    except Exception as e:
        return f"ERROR: {e}"


def call_groq(prompt: str, model: str) -> str | None:
    """Call Groq API."""
    try:
        from src.groq_client import groq_text_completion

        return groq_text_completion(prompt, model=model, timeout=60)
    except Exception as e:
        return f"ERROR: {e}"


def call_mistral(prompt: str, model: str) -> str | None:
    """Call Mistral API."""
    try:
        from src.mistral_client import mistral_completion

        return mistral_completion(prompt, model=model, timeout=60)
    except Exception as e:
        return f"ERROR: {e}"


def call_openrouter(prompt: str, model: str) -> str | None:
    """Call OpenRouter API."""
    try:
        from src.openrouter_client import openrouter_completion

        return openrouter_completion(prompt, model=model, timeout=120)
    except Exception as e:
        return f"ERROR: {e}"


def extract_picks_count(response: str) -> int:
    """Extract number of picks from JSON response."""
    if not response or response.startswith("ERROR"):
        return 0

    try:
        # Clean markdown
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)

        if isinstance(data, dict):
            picks = data.get("picks", [])
            return len(picks) if isinstance(picks, list) else 0
        elif isinstance(data, list):
            return len(data)
        return 0
    except:
        return 0


def run_benchmark(samples: int = 5) -> dict[str, Any]:
    """Run parser benchmark on all models."""

    results = {model["name"]: [] for model in PARSER_MODELS}
    test_data = TEST_SAMPLES[:samples]

    print("=" * 80)
    print("PARSER MODEL BENCHMARK")
    print("=" * 80)
    print(f"Samples: {len(test_data)}")
    print(f"Models: {len(PARSER_MODELS)}")
    print("=" * 80)
    print()

    for sample in test_data:
        prompt = PARSING_PROMPT.format(text=sample["ocr_text"])

        for model_info in PARSER_MODELS:
            name = model_info["name"]
            provider = model_info["provider"]
            model = model_info["model"]

            # Check API key
            key_map = {
                "cerebras": "CEREBRAS_TOKEN",
                "groq": "GROQ_TOKEN",
                "mistral": "MISTRAL_TOKEN",
                "openrouter": "OPENROUTER_API_KEY",
            }

            if not os.getenv(key_map.get(provider, "")):
                results[name].append(
                    {
                        "sample_id": sample["id"],
                        "time_ms": 0,
                        "picks_found": 0,
                        "expected_picks": sample["expected_picks"],
                        "error": f"{key_map.get(provider)} not set",
                    }
                )
                print(f"[{name:30}] SKIP - {key_map.get(provider)} not set")
                continue

            # Call provider
            start = time.time()

            if provider == "cerebras":
                response = call_cerebras(prompt, model)
            elif provider == "groq":
                response = call_groq(prompt, model)
            elif provider == "mistral":
                response = call_mistral(prompt, model)
            elif provider == "openrouter":
                response = call_openrouter(prompt, model)
            else:
                response = None

            elapsed_ms = int((time.time() - start) * 1000)
            picks_found = extract_picks_count(response)

            error = None
            if response and response.startswith("ERROR"):
                error = response
                picks_found = 0

            results[name].append(
                {
                    "sample_id": sample["id"],
                    "time_ms": elapsed_ms,
                    "picks_found": picks_found,
                    "expected_picks": sample["expected_picks"],
                    "error": error,
                }
            )

            status = "OK" if picks_found > 0 else "FAIL"
            if error:
                status = "ERR"

            print(f"[{name:30}] {elapsed_ms:6}ms | picks={picks_found}/{sample['expected_picks']} | {status}")

    return results


def summarize_results(results: dict[str, list]) -> None:
    """Print summary table."""
    print()
    print("=" * 80)
    print("SUMMARY BY MODEL")
    print("=" * 80)
    print()
    print(f"{'Model':<35} {'Avg Time':>10} {'Accuracy':>10} {'Success':>10} {'Status':>15}")
    print("-" * 80)

    summaries = []

    for model_name, model_results in results.items():
        if not model_results:
            continue

        # Filter out errors
        valid = [r for r in model_results if not r.get("error")]
        errors = [r for r in model_results if r.get("error")]

        if not valid and errors:
            # All failed due to missing API key
            if "not set" in str(errors[0].get("error", "")):
                print(f"{model_name:<35} {'N/A':>10} {'N/A':>10} {'0%':>10} {'NO API KEY':>15}")
            else:
                print(f"{model_name:<35} {'N/A':>10} {'N/A':>10} {'0%':>10} {'FAILED':>15}")
            continue

        total_samples = len(model_results)
        success_count = len(valid)

        avg_time = sum(r["time_ms"] for r in valid) / len(valid) if valid else 0

        # Calculate accuracy (picks found vs expected)
        total_expected = sum(r["expected_picks"] for r in valid)
        total_found = sum(r["picks_found"] for r in valid)
        accuracy = (total_found / total_expected * 100) if total_expected > 0 else 0

        success_rate = (success_count / total_samples * 100) if total_samples > 0 else 0

        # Determine status
        if success_rate >= 80 and accuracy >= 80:
            status = "GOOD"
        elif success_rate >= 50 or accuracy >= 50:
            status = "UNRELIABLE"
        else:
            status = "POOR"

        summaries.append(
            {
                "name": model_name,
                "avg_time": avg_time,
                "accuracy": accuracy,
                "success_rate": success_rate,
                "status": status,
            }
        )

        print(f"{model_name:<35} {avg_time:>8.0f}ms {accuracy:>9.0f}% {success_rate:>9.0f}% {status:>15}")

    print("=" * 80)

    # Find best model
    good_models = [s for s in summaries if s["status"] == "GOOD"]
    if good_models:
        best = min(good_models, key=lambda x: x["avg_time"])
        print(f"\n BEST MODEL: {best['name']} ({best['avg_time']:.0f}ms, {best['accuracy']:.0f}% accuracy)")


def main():
    parser = argparse.ArgumentParser(description="Benchmark parser models")
    parser.add_argument("--samples", type=int, default=5, help="Number of test samples")
    args = parser.parse_args()

    start = time.time()
    results = run_benchmark(args.samples)
    summarize_results(results)

    total_time = time.time() - start
    print(f"\nTotal benchmark time: {total_time:.1f}s")

    # Save results
    report_dir = os.path.join(BASE_DIR, "benchmark", "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "parser_benchmark_results.json")

    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
