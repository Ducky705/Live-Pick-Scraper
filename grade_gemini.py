import json
import os
import sys
from collections import defaultdict

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark_golden_set import fuzzy_match

def grade():
    parsing_file = r"benchmark\dataset\parsing_golden_set.json"
    results_file = r"gpt4o_results.json"

    with open(parsing_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    with open(results_file, 'r', encoding='utf-8') as f:
        results_data = json.load(f)
        
    extracted_picks = results_data.get("picks", [])
    
    extracted_map = defaultdict(list)
    for p in extracted_picks:
        mid = str(p.get("message_id"))
        if not mid.startswith("message_"):
            mid = f"message_{mid}"
        extracted_map[mid].append(p)

    total_expected = 0
    total_found = 0
    total_correct = 0

    misses = []

    for msg_key, expected_list in ground_truth.items():
        actual_list = extracted_map.get(msg_key, [])

        total_expected += len(expected_list)
        total_found += len(actual_list)
        
        used_actual_indices = set()

        for exp in expected_list:
            match_found = False
            for idx, act in enumerate(actual_list):
                if idx in used_actual_indices:
                    continue
                
                # Align 'selection' key from gpt4o to 'pick' expected by fuzzy_match
                if 'selection' in act and 'pick' not in act:
                    act['pick'] = act['selection']

                if fuzzy_match(exp, act):
                    match_found = True
                    used_actual_indices.add(idx)
                    total_correct += 1
                    break

            if not match_found:
                misses.append({
                    "msg_id": msg_key,
                    "expected": exp,
                    "candidates": actual_list
                })

    precision = (total_correct / total_found * 100) if total_found > 0 else 0
    recall = (total_correct / total_expected * 100) if total_expected > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    print("=== GPT-4o Evaluation ===")
    print(f"Total Expected Picks (Ground Truth): {total_expected}")
    print(f"Total Extracted Picks (GPT-4o):      {total_found}")
    print(f"Successfully Matched:                {total_correct}")
    print("-" * 30)
    print(f"Recall (Accuracy against GT):        {recall:.2f}%")
    print(f"Precision (Quality of Extraction):   {precision:.2f}%")
    print(f"F1 Score:                            {f1:.2f}%")
    print("-" * 30)

    if misses:
        print(f"\nTop Missed Picks:")
        for m in misses[:10]:
            print(f"- Msg {m['msg_id']}: Expected '{m['expected'].get('p')}' ({m['expected'].get('ty')})")
            print(f"  Candidates in pipeline: {[a.get('pick') for a in m['candidates']]}")

if __name__ == "__main__":
    grade()
