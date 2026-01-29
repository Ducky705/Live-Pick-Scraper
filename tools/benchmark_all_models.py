#!/usr/bin/env python3
"""
Comprehensive Model Benchmark
=============================
Benchmarks ALL models across 5 providers against the golden set (Text Parsing).
Measure: Precision, Recall, F1, Latency, Cost (Tokens).

Usage:
    python tools/benchmark_all_models.py
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass

from src.cerebras_client import cerebras_completion
from src.gemini_client import gemini_text_completion
from src.groq_client import groq_text_completion
from src.mistral_client import mistral_completion
from src.model_registry import get_all_models
from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt


@dataclass
class EvaluationResult:
    """Aggregated evaluation results."""

    total_images: int = 0
    total_expected_picks: int = 0
    total_actual_picks: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)


def normalize_golden_pick(pick: dict) -> dict:
    """Normalize golden set pick format to standard format expected by evaluator."""
    return {
        "pick": pick.get("p") or pick.get("pick", ""),
        "league": pick.get("lg") or pick.get("league", ""),
        "type": pick.get("ty") or pick.get("type", ""),
        "odds": pick.get("od") or pick.get("odds"),
        "capper": pick.get("cn") or pick.get("capper_name", ""),
        "units": pick.get("u") or pick.get("units", 1.0),
    }


def evaluate_image(expected_picks: list[dict], actual_picks: list[dict], result):
    """Evaluate parser output for a single item - fixed to handle minified keys."""
    result.total_images += 1

    # Normalize expected picks to standard format
    normalized_expected = [normalize_golden_pick(p) for p in expected_picks]
    # Normalize actual picks (from AI response)
    normalized_actual = [normalize_golden_pick(p) for p in actual_picks]

    result.total_expected_picks += len(normalized_expected)
    result.total_actual_picks += len(normalized_actual)

    # Simple matching based on pick text similarity
    from difflib import SequenceMatcher

    def normalize_text(s):
        if not s:
            return ""
        return s.lower().strip().replace("  ", " ")

    matched = 0
    used_actual = set()

    for exp in normalized_expected:
        exp_pick = normalize_text(exp.get("pick", ""))
        best_score = 0
        best_idx = -1

        for i, act in enumerate(normalized_actual):
            if i in used_actual:
                continue
            act_pick = normalize_text(act.get("pick", ""))

            # Calculate similarity
            score = SequenceMatcher(None, exp_pick, act_pick).ratio()

            # Bonus for matching league/type
            if exp.get("league") and exp.get("league") == act.get("league"):
                score += 0.1
            if exp.get("type") and exp.get("type") == act.get("type"):
                score += 0.1

            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx >= 0 and best_score >= 0.6:  # Lower threshold for matching
            matched += 1
            used_actual.add(best_idx)

    result.true_positives += matched
    result.false_negatives += len(normalized_expected) - matched
    result.false_positives += len(normalized_actual) - matched


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("benchmark_all.log"), logging.StreamHandler(sys.stdout)],
)


def load_golden_set(path: Path, limit: int | None = None) -> list[dict]:
    """Load golden set items."""
    items = []
    if not path.exists():
        logging.error(f"Golden set not found at {path}")
        return []

    try:
        # Try loading as standard JSON (list of objects)
        with open(path, encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, list):
                items = content
            else:
                logging.warning("Golden set is not a list, attempting JSONL fallback...")
                items = [content]
    except json.JSONDecodeError:
        # Fallback to JSONL (one object per line)
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        items.append(json.loads(line))
                    except:
                        pass

    if limit is not None:
        return items[:limit]
    return items


def run_model_inference(provider: str, model: str, item: dict) -> dict:
    """Run inference for a single item using specific model."""

    # Adapt item structure
    mock_item = {
        "id": item.get("id", "0"),
        "text": item.get("original_text", ""),
        "ocr_texts": item.get("ocr_texts", []),
        "ocr_text": "\n".join(item.get("ocr_texts", [])),
    }

    prompt = generate_ai_prompt([mock_item])

    start_time = time.time()
    result = None
    error = None

    try:
        if provider == "cerebras":
            result = cerebras_completion(prompt, model=model, timeout=30)
        elif provider == "groq":
            result = groq_text_completion(prompt, model=model, timeout=30)
        elif provider == "mistral":
            result = mistral_completion(prompt, model=model, timeout=30)
        elif provider == "gemini":
            result = gemini_text_completion(prompt, model=model, timeout=30)
        elif provider == "openrouter":
            result = openrouter_completion(prompt, model=model, timeout=45)
    except Exception as e:
        error = str(e)

    duration = (time.time() - start_time) * 1000  # ms

    # Parse Result
    picks = []
    if result:
        try:
            # Clean markdown
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]

            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                picks = parsed.get("picks", [])
            elif isinstance(parsed, list):
                picks = parsed
        except Exception as e:
            error = f"Parse Error: {e}"

    return {"picks": picks, "latency": duration, "error": error}


def load_existing_results(path: str) -> dict[str, dict]:
    """Load existing benchmark results to allow resuming/retrying."""
    if not os.path.exists(path):
        return {}

    try:
        with open(path) as f:
            data = json.load(f)
            # Map "provider/model" -> result dict
            return {f"{r['provider']}/{r['model']}": r for r in data.get("results", [])}
    except Exception:
        return {}


def benchmark_model(provider: str, model: str, golden_items: list[dict]):
    """Benchmark a single model against full golden set."""
    logging.info(f"Benchmarking {provider}/{model}...")

    result = EvaluationResult()
    total_latency = 0
    errors = 0
    consecutive_failures = 0

    for i, item in enumerate(golden_items):
        # Retry loop for rate limits at the benchmark level
        max_retries = 3
        res = {"picks": [], "latency": 0, "error": "Unknown Error"}

        for attempt in range(max_retries):
            res = run_model_inference(provider, model, item)

            # Check for potential rate limit indicators in error
            is_rate_limit = False
            if res["error"]:
                err_str = str(res["error"]).lower()
                if "429" in err_str or "limit" in err_str or "quota" in err_str:
                    is_rate_limit = True

            if is_rate_limit:
                wait_time = 10 * (attempt + 1)
                logging.warning(f"Rate limit hit for {provider}/{model} on item {i}. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue  # Retry

            # If successful or non-rate-limit error, break retry loop
            break

        if res["error"]:
            errors += 1
            consecutive_failures += 1
        else:
            consecutive_failures = 0

        total_latency += res["latency"]

        # Evaluate
        expected = item.get("expected_picks", [])
        actual = res["picks"]
        evaluate_image(expected, actual, result)

        # Rate limit safety pause - Dynamic based on provider
        if provider in ["gemini", "groq"]:
            time.sleep(4.0)  # Slower for sensitive providers
        else:
            time.sleep(1.0)

        # Circuit breaker if too many failures (likely total outage or rate limit)
        if consecutive_failures >= 5:
            logging.error(f"Too many consecutive failures for {provider}/{model}. Aborting model.")
            break

    avg_latency = total_latency / len(golden_items) if golden_items else 0

    return {
        "provider": provider,
        "model": model,
        "f1": result.f1,
        "precision": result.precision,
        "recall": result.recall,
        "avg_latency": avg_latency,
        "errors": errors,
        "total_picks": result.total_actual_picks,
        "correct_picks": result.true_positives,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Items per model")
    parser.add_argument("--providers", nargs="+", help="Filter providers")
    parser.add_argument("--retry-failed", action="store_true", help="Only run models that failed or are missing")
    parser.add_argument("--output", default="benchmark/reports/all_models_benchmark.json", help="Output file")
    args = parser.parse_args()

    golden_path = Path("golden_set/golden_set.json")
    if not golden_path.exists():
        golden_path = Path("golden_set/golden_set.jsonl")

    golden_items = load_golden_set(golden_path, args.limit)
    logging.info(f"Loaded {len(golden_items)} golden set items.")

    all_models = get_all_models()
    if args.providers:
        all_models = [m for m in all_models if m[0] in args.providers]

    # Load existing results
    existing_results = load_existing_results(args.output)
    final_results = []

    models_to_run = []

    for provider, model in all_models:
        key = f"{provider}/{model}"
        prev_result = existing_results.get(key)

        should_run = True
        if args.retry_failed and prev_result:
            # Check if it was successful (low error rate and reasonable F1 if applicable)
            # If errors > 50% of items or F1 is 0.0 with errors, consider it failed
            total_items = args.limit or 10  # Estimate
            if prev_result.get("errors", 0) == 0 and prev_result.get("f1", 0) > 0:
                should_run = False
                final_results.append(prev_result)  # Keep existing

        if should_run:
            models_to_run.append((provider, model))
        else:
            print(f"Skipping {key} (already successful)")

    print(f"\nRunning benchmarks for {len(models_to_run)} models...")
    print(f"{'Provider':<12} | {'Model':<30} | {'F1':<6} | {'Prec':<6} | {'Rec':<6} | {'Lat (ms)':<8}")
    print("-" * 85)

    for provider, model in models_to_run:
        try:
            metrics = benchmark_model(provider, model, golden_items)
            final_results.append(metrics)

            # Update file immediately after each model (save progress)
            os.makedirs("benchmark/reports", exist_ok=True)
            with open(args.output, "w") as f:
                json.dump(
                    {"date": time.strftime("%Y-%m-%d"), "dataset_size": len(golden_items), "results": final_results},
                    f,
                    indent=2,
                )

            print(
                f"{provider:<12} | {model:<30} | {metrics['f1']:.1%} | {metrics['precision']:.1%} | {metrics['recall']:.1%} | {metrics['avg_latency']:.0f}"
            )

        except Exception as e:
            logging.error(f"Failed to benchmark {provider}/{model}: {e}")
            print(f"{provider:<12} | {model:<30} | ERROR  | -      | -      | -")

    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
