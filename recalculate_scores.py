import json
import os
import glob
from collections import defaultdict
from benchmark_golden_set import fuzzy_match

def grade_file(results_file, ground_truth):
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
    except:
        return None
        
    extracted_picks = results_data.get("picks", [])
    if not extracted_picks:
        # Sometimes it's a list directly, or under another key
        if isinstance(results_data, list):
            extracted_picks = results_data
        else:
            return None
            
    res_map = defaultdict(list)
    all_extracted = []
    
    for p in extracted_picks:
        mid = str(p.get("message_id"))
        if not mid.startswith("message_"):
            mid = f"message_{mid}"
        res_map[mid].append(p)
        all_extracted.append(p)

    total_expected = sum(len(x) for x in ground_truth.values())
    total_found = len(all_extracted)
    true_misses = 0
    matches = 0
    cross_message_matches = 0

    for msg_key, expected_list in ground_truth.items():
        actual_list = res_map.get(msg_key, [])
        used_actual_indices = set()

        for exp in expected_list:
            match_found = False
            for idx, act in enumerate(actual_list):
                if idx in used_actual_indices:
                    continue
                
                if 'selection' in act and 'pick' not in act:
                    act['pick'] = act['selection']

                if fuzzy_match(exp, act):
                    match_found = True
                    used_actual_indices.add(idx)
                    matches += 1
                    break

            if not match_found:
                # Check global
                found_elsewhere = False
                for act in all_extracted:
                    if 'selection' in act and 'pick' not in act:
                        act['pick'] = act['selection']
                    if fuzzy_match(exp, act):
                        found_elsewhere = True
                        cross_message_matches += 1
                        matches += 1
                        break
                if not found_elsewhere:
                    true_misses += 1

    precision = (matches / total_found * 100) if total_found > 0 else 0
    recall = (matches / total_expected * 100) if total_expected > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
    
    return {
        "file": results_file,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matches": matches,
        "misses": true_misses,
        "cross_message": cross_message_matches,
        "total_extracted": total_found
    }


def main():
    parsing_file = r"benchmark\dataset\parsing_golden_set.json"
    with open(parsing_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
        
    json_files = glob.glob("*.json")
    results = []
    for f in json_files:
        if "golden_set" in f or "prd" in f or "task" in f or "plan" in f:
            continue
        try:
            res = grade_file(f, ground_truth)
            if res:
                results.append(res)
        except Exception as e:
            pass

    results.sort(key=lambda x: x["f1"], reverse=True)
    
    print("\n=== RECALCULATED SCORES WITH GLOBAL DEDUPLICATION ===\n")
    for r in results:
        print(f"File: {r['file']}")
        print(f"  Recall:    {r['recall']:.2f}% ({r['matches']}/276 expected - True Misses: {r['misses']})")
        print(f"  Precision: {r['precision']:.2f}% ({r['matches']}/{r['total_extracted']} extracted)")
        print(f"  F1 Score:  {r['f1']:.2f}%")
        print("-" * 40)

if __name__ == "__main__":
    main()
