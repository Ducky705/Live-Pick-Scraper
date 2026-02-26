import json
from verify_duplicates import fuzzy_match

def main():
    with open(r'benchmark\dataset\parsing_golden_set.json', encoding='utf-8') as f:
        gt = json.load(f)

    with open('gpt4o_results.json', encoding='utf-8') as f:
        res = json.load(f)

    res_map = {}
    all_extracted = []
    for p in res.get('picks', []):
        mid = str(p.get('message_id')).replace('message_', '')
        if mid not in res_map:
            res_map[mid] = []
        res_map[mid].append(p)
        all_extracted.append(p)

    fully_missed = []
    for msg_id, expected_list in gt.items():
        actual_list = res_map.get(msg_id.replace('message_', ''), [])
        matched_indices = set()
        
        for exp in expected_list:
            matched = False
            for i, act in enumerate(actual_list):
                if i in matched_indices: continue
                if fuzzy_match(exp, act):
                    matched = True
                    matched_indices.add(i)
                    break
            
            if not matched:
                found_elsewhere = False
                for act in all_extracted:
                    if fuzzy_match(exp, act):
                        found_elsewhere = True
                        break
                if not found_elsewhere:
                    fully_missed.append((msg_id, exp))

    for m, e in fully_missed:
        print(f"MISSED: {e.get('p')} ({e.get('ty')}) from {m}")

if __name__ == '__main__':
    main()
