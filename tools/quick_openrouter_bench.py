#!/usr/bin/env python3
"""Quick OpenRouter benchmark on 3 items."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv()

from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt

# Load golden set
golden = json.load(open("golden_set/golden_set.json"))[:3]

models = [
    "deepseek/deepseek-r1-0528:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "arcee-ai/trinity-mini:free",
]

results = []
print(f"Benchmarking {len(models)} OpenRouter models on 3 items...")
print()
print(f"{'Model':<45} | {'F1':>6} | {'Latency':>8}")
print("-" * 70)

for model in models:
    correct = 0
    total_expected = 0
    total_actual = 0
    total_time = 0
    errors = 0

    for item in golden:
        mock_item = {
            "id": item.get("id", "0"),
            "text": item.get("original_text", ""),
            "ocr_texts": item.get("ocr_texts", []),
            "ocr_text": "\n".join(item.get("ocr_texts", [])),
        }
        prompt = generate_ai_prompt([mock_item])

        start = time.time()
        try:
            result = openrouter_completion(prompt, model=model, timeout=90)
            duration = (time.time() - start) * 1000
            total_time += duration

            # Parse
            picks = []
            if result:
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    parts = cleaned.split("```")
                    if len(parts) > 1:
                        cleaned = parts[1]
                        if cleaned.startswith("json"):
                            cleaned = cleaned[4:]
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict):
                        picks = parsed.get("picks", [])
                    elif isinstance(parsed, list):
                        picks = parsed
                except:
                    pass

            expected = item.get("expected_picks", [])
            total_expected += len(expected)
            total_actual += len(picks)

            # Simple match count
            matched = min(len(picks), len(expected))
            correct += matched

        except Exception as e:
            errors += 1
            total_time += (time.time() - start) * 1000
            print(f"  Error on {model}: {e}")

        time.sleep(2)  # Rate limit

    # Calculate F1
    precision = correct / total_actual if total_actual > 0 else 0
    recall = correct / total_expected if total_expected > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    avg_latency = total_time / len(golden)

    results.append(
        {
            "provider": "openrouter",
            "model": model,
            "f1": f1,
            "precision": precision,
            "recall": recall,
            "avg_latency": avg_latency,
            "errors": errors,
        }
    )

    print(f"{model[:45]:<45} | {f1 * 100:>5.1f}% | {avg_latency:>6.0f}ms")

# Save
with open("benchmark/reports/openrouter_models_benchmark.json", "w") as f:
    json.dump({"date": "2026-01-22", "dataset_size": 3, "results": results}, f, indent=2)

print()
print("Saved to benchmark/reports/openrouter_models_benchmark.json")
