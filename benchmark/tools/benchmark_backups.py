"""
Benchmark Backup Candidates
===========================
Testing potential backup models to replace or augment Llama 3.3 70B (81% Recall).
Candidates:
1. GPT-OSS 120B
2. Aurora Alpha
3. Qwen 3 235B (Thinking)

Dataset: 15 messages (same scale as previous tests)
Batch Size: 5
"""

import json
import os
import time
import sys
import logging
import re
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.parallel_batch_processor import ParallelBatchProcessor, PROVIDER_CONFIG
import src.openrouter_client as openrouter_module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# VALIDATED IDs from verify_backup_ids.py
MODELS_TO_TEST = [
    "openai/gpt-oss-120b:free",
    "openrouter/aurora-alpha",
    "qwen/qwen3-235b-a22b-thinking-2507"
]

BATCH_SIZES = [5]

def normalize_string(s):
    if not s: return ""
    return str(s).lower().replace(" ", "").replace("-", "").replace(":", "")

def fuzzy_match(exp_pick, act_pick):
    exp = normalize_string(exp_pick)
    act = normalize_string(act_pick)
    return exp in act or act in exp

def parse_json_garbage(text):
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
        return json.loads(text)
    except:
        return []

def run_test_case(model_id, batch_size, messages, ground_truth):
    print(f"\n>>> TESTING: {model_id} @ BatchSize={batch_size}")
    
    processor = ParallelBatchProcessor(providers=["openrouter"])
    
    # Chunking
    batches = []
    current_batch = []
    for msg in messages:
        current_batch.append(msg)
        if len(current_batch) >= batch_size:
            batches.append(list(current_batch))
            current_batch = []
    if current_batch:
        batches.append(current_batch)
        
    print(f"    Processing {len(batches)} batches...")
    start_time = time.time()
    
    # MONKEY PATCH CONFIG
    original_model = PROVIDER_CONFIG["openrouter"]["model"]
    PROVIDER_CONFIG["openrouter"]["model"] = model_id
    
    # Disable fallbacks
    original_defaults = list(openrouter_module.DEFAULT_MODELS)
    openrouter_module.DEFAULT_MODELS = [] 
    
    try:
        results = processor.process_batches(batches, allowed_providers=["openrouter"], schedule_context={}, style_context={})
    finally:
        PROVIDER_CONFIG["openrouter"]["model"] = original_model
        openrouter_module.DEFAULT_MODELS = original_defaults
        
    duration = time.time() - start_time
    throughput = len(messages) / duration if duration > 0 else 0
    
    # Evaluation
    extracted_picks = []
    for r in results:
        if isinstance(r, str):
            data = parse_json_garbage(r)
            if isinstance(data, list):
                extracted_picks.extend(data)
        elif isinstance(r, dict) and "picks" in r:
             extracted_picks.extend(r["picks"])
            
    # Group extracted picks by message ID
    extracted_map = defaultdict(list)
    for p in extracted_picks:
        mid = str(p.get("message_id"))
        extracted_map[f"message_{mid}"].append(p)
    
    total_expected = 0
    total_correct = 0
    total_found = len(extracted_picks)
    
    processed_msg_ids = set([f"message_{m['id']}" for m in messages])

    for msg_key, expected_list in ground_truth.items():
        if msg_key not in processed_msg_ids: continue
        
        actual_list = extracted_map.get(msg_key, [])
        total_expected += len(expected_list)
        
        used_indices = set()
        for exp in expected_list:
            for idx, act in enumerate(actual_list):
                if idx in used_indices: continue
                pick_str = act.get("pick", "") or act.get("selection", "") 
                if fuzzy_match(exp.get("p"), pick_str):
                    used_indices.add(idx)
                    total_correct += 1
                    break
    
    precision = (total_correct / total_found * 100) if total_found > 0 else 0
    recall = (total_correct / total_expected * 100) if total_expected > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
    
    print(f"    Recall: {recall:.2f}% | Precision: {precision:.2f}% | F1: {f1:.2f}%")
    print(f"    Speed: {throughput:.2f} msgs/sec | Duration: {duration:.2f}s")
    
    return {
        "model": model_id,
        "batch_size": batch_size,
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "throughput": throughput,
        "duration": duration
    }

def main():
    ocr_file = r"benchmark\dataset\ocr_golden_set.json"
    parsing_file = r"benchmark\dataset\parsing_golden_set.json"

    with open(ocr_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)

    with open(parsing_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    # Prepare Messages
    messages = []
    for msg_key, text in ocr_data.items():
        msg_id = msg_key.replace("message_", "")
        messages.append({
            "id": msg_id,
            "text": text,
            "ocr_text": "",
            "channel_name": "Benchmark_Channel", 
            "date": "2026-02-14",
            "source": "Benchmark"
        })
        
    messages = messages[:15]
    print(f"Loaded {len(messages)} messages for Backup Benchmark.")
        
    scores = []
    
    for model in MODELS_TO_TEST:
        for batch_size in BATCH_SIZES:
            try:
                result = run_test_case(model, batch_size, messages, ground_truth)
                scores.append(result)
                time.sleep(2)
            except Exception as e:
                print(f"!!! FAILED {model} @ {batch_size}: {e}")
                
    # Report
    print("\n" + "="*60)
    print("BACKUP CANDIDATE RESULTS")
    print("="*60)
    print(f"{'Model':<40} | {'BS':<3} | {'Recall':<8} | {'Prec':<8} | {'F1':<8} | {'Speed':<8}")
    print("-" * 85)
    
    scores.sort(key=lambda x: x["recall"], reverse=True)
    
    for s in scores:
        print(f"{s['model']:<40} | {s['batch_size']:<3} | {s['recall']:.1f}%    | {s['precision']:.1f}%    | {s['f1']:.1f}%    | {s['throughput']:.2f}")

if __name__ == "__main__":
    main()
