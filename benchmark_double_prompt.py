import os
import sys
import json
import logging
from unittest.mock import patch

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extraction_pipeline import ExtractionPipeline
import src.openrouter_client as openrouter_client

# Import the original so we can call it inside our hook
original_openrouter_completion = openrouter_client.openrouter_completion

def patched_openrouter_completion_baseline(prompt, model=None, timeout=180, max_cycles=2, images=None, validate_json=False):
    return original_openrouter_completion(prompt, model="stepfun/step-3.5-flash:free", timeout=timeout, max_cycles=max_cycles, images=images, validate_json=validate_json)

def patched_openrouter_completion_double_stepfun(prompt, model=None, timeout=180, max_cycles=2, images=None, validate_json=False):
    double_prompt = prompt + "\n\n" + prompt
    return original_openrouter_completion(double_prompt, model="stepfun/step-3.5-flash:free", timeout=timeout, max_cycles=max_cycles, images=images, validate_json=validate_json)

def calculate_accuracy(golden_set, actual_picks):
    from verify_golden_set import fuzzy_match
    total_expected = 0
    total_correct = 0
    
    actual_picks_by_id = {}
    for p in actual_picks:
        mid = p.get("message_id")
        if mid not in actual_picks_by_id:
            actual_picks_by_id[mid] = []
        actual_picks_by_id[mid].append(p)

    for item in golden_set:
        mid = item["id"]
        expected_list = item.get("expected_picks", [])
        actual_list = actual_picks_by_id.get(str(mid), [])

        total_expected += len(expected_list)

        matched_indices = set()
        for exp in expected_list:
            for i, act in enumerate(actual_list):
                if i in matched_indices:
                    continue
                if fuzzy_match(exp, act):
                    matched_indices.add(i)
                    total_correct += 1
                    break
                    
    return total_correct, total_expected, (total_correct/total_expected*100) if total_expected > 0 else 0

def run_test():
    with open("new_golden_set.json", encoding="utf-8") as f:
        golden_set = json.load(f)

    messages = []
    for item in golden_set:
        msg = {
            "id": str(item["id"]),
            "date": item.get("date", "2026-01-01"),
            "text": item["text"],
            "images": item.get("images", []),
            "ocr_text": "",
            "ocr_texts": [],
            "source": item.get("source", "Telegram"),
        }
        messages.append(msg)
        
    target_date = "2026-01-24"

    print("=== RUNNING BASELINE (Single Prompt, step-3.5-flash) ===")
    ExtractionPipeline._EXP_CACHE = {} 
    with patch('src.openrouter_client.openrouter_completion', side_effect=patched_openrouter_completion_baseline):
        baseline_picks = ExtractionPipeline.run(messages, target_date=target_date)
        base_correct, base_total, base_acc = calculate_accuracy(golden_set, baseline_picks)
        print(f"\n-> BASELINE Accuracy: {base_acc:.2f}% ({base_correct}/{base_total})\n")

    print("=== RUNNING DOUBLE PROMPT (Double Prompt, step-3.5-flash) ===")
    ExtractionPipeline._EXP_CACHE = {} 
    with patch('src.openrouter_client.openrouter_completion', side_effect=patched_openrouter_completion_double_stepfun):
        double_picks = ExtractionPipeline.run(messages, target_date=target_date)
        dp_correct, dp_total, dp_acc = calculate_accuracy(golden_set, double_picks)
        print(f"\n-> DOUBLE PROMPT Accuracy: {dp_acc:.2f}% ({dp_correct}/{dp_total})\n")
        
    print("=" * 40)
    print(f"BASELINE:      {base_acc:.2f}%")
    print(f"DOUBLE PROMPT: {dp_acc:.2f}%")
    print(f"DIFF:          {dp_acc - base_acc:.2f}%")

if __name__ == "__main__":
    # Suppress verbose logging from submodules
    logging.getLogger("src.extraction_pipeline").setLevel(logging.WARNING)
    logging.getLogger("src.parallel_batch_processor").setLevel(logging.WARNING)
    run_test()
