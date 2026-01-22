import json
import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher

sys.path.append(os.getcwd())

from src.prompt_builder import generate_ai_prompt
from src.openrouter_client import openrouter_completion
from src.utils import clean_text_for_ai
from src.pick_normalizer import normalize_pick, picks_match

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def normalize(s):
    if not s: return ""
    # Use the new robust normalizer
    return normalize_pick(str(s))

def is_match(pick_a, pick_b):
    # Use the new robust matching logic
    return picks_match(pick_a.get('p', ''), pick_b.get('p', ''))

def compare_picks(expected_list, actual_list):
    # Simple matching logic
    # Returns (matches, false_negatives, false_positives)
    
    # Create copies to track consumption
    unmatched_expected = list(expected_list)
    unmatched_actual = list(actual_list)
    
    matches = 0
    
    # Forward pass
    for exp in list(unmatched_expected):
        best_match = None
        # We don't need a score anymore, picks_match returns boolean based on robust logic
        
        for act in unmatched_actual:
            if is_match(exp, act):
                best_match = act
                break # Found a match
        
        if best_match:
            matches += 1
            unmatched_expected.remove(exp)
            unmatched_actual.remove(best_match)
            
    return matches, len(unmatched_expected), len(unmatched_actual)

def process_item(item):
    item_id = item['id']
    
    # Construct input for prompt builder
    # It expects dicts with 'id', 'text', 'ocr_texts'
    data_input = {
        'id': item_id,
        'text': item.get('original_text', ''),
        'ocr_texts': item.get('ocr_texts', [])
    }
    
    # Generate prompt
    prompt = generate_ai_prompt([data_input])
    
    try:
        # Call LLM
        response = openrouter_completion(prompt)
        
        # Parse output
        clean_resp = response.strip()
        if clean_resp.startswith("```json"):
            clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
        elif clean_resp.startswith("```"):
            clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
            
        data = json.loads(clean_resp)
        actual_picks = data.get('picks', [])
        
        # Ensure IDs are correct (LLM sometimes hallucinates IDs)
        for p in actual_picks:
            p['id'] = item_id
            
        return item_id, actual_picks, None
        
    except Exception as e:
        logging.error(f"Error processing {item_id}: {e}")
        return item_id, [], str(e)

def main():
    golden_file = 'golden_set/golden_set.json'
    if not os.path.exists(golden_file):
        print(f"Golden set not found: {golden_file}")
        return

    with open(golden_file, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)
        
    print(f"Loaded {len(golden_data)} items from Golden Set.")
    print("Running benchmark (Parallel)...")
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_item, item): item['id'] for item in golden_data}
        
        for future in as_completed(futures):
            item_id, actual_picks, error = future.result()
            
            # Find expected picks
            expected_item = next((x for x in golden_data if str(x['id']) == str(item_id)), None)
            expected_picks = expected_item.get('expected_picks', []) if expected_item else []
            
            matches, missed, extra = compare_picks(expected_picks, actual_picks)
            
            results[item_id] = {
                "expected": len(expected_picks),
                "actual": len(actual_picks),
                "matches": matches,
                "missed": missed,
                "extra": extra,
                "error": error
            }
            
            status = "PASS" if missed == 0 and extra == 0 else "FAIL"
            if error: status = "ERROR"
            
            logging.info(f"[{status}] ID:{item_id} | Exp: {len(expected_picks)} | Act: {len(actual_picks)} | Match: {matches}")

    # Aggregate Metrics
    total_expected = sum(r['expected'] for r in results.values())
    total_matches = sum(r['matches'] for r in results.values())
    total_missed = sum(r['missed'] for r in results.values())
    total_extra = sum(r['extra'] for r in results.values())
    total_errors = sum(1 for r in results.values() if r['error'])
    
    precision = total_matches / (total_matches + total_extra) if (total_matches + total_extra) > 0 else 0
    recall = total_matches / total_expected if total_expected > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\n" + "="*40)
    print("BENCHMARK RESULTS")
    print("="*40)
    print(f"Total Items:      {len(golden_data)}")
    print(f"Total Expected:   {total_expected}")
    print(f"Total Matches:    {total_matches}")
    print(f"Total Missed:     {total_missed} (False Negatives)")
    print(f"Total Extra:      {total_extra} (False Positives)")
    print(f"Errors:           {total_errors}")
    print("-"*40)
    print(f"PRECISION: {precision:.2%}")
    print(f"RECALL:    {recall:.2%}")
    print(f"F1 SCORE:  {f1:.2%}")
    print("="*40)
    
    # Save detailed results
    with open('benchmark_results_v2.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
        
if __name__ == "__main__":
    main()
