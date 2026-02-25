import json
import os

def main():
    with open(r'benchmark\dataset\parsing_golden_set.json', encoding='utf-8') as f:
        gt = json.load(f)
        
    messages = {}
    try:
        with open(r'benchmark\dataset\ocr_golden_set.json', encoding='utf-8') as f:
            for m in json.load(f):
                messages[str(m['id'])] = m
    except Exception as e:
        print("Error loading ocr_golden_set:", e)

    with open('gpt4o_results.json', encoding='utf-8') as f:
        res = json.load(f)

    from collections import defaultdict
    res_map = defaultdict(list)
    for p in res.get('picks', []):
        mid = str(p.get('message_id'))
        if not mid.startswith('message_'): 
            mid = 'message_' + mid
        res_map[mid].append(p)

    missing_details = []
    from benchmark_golden_set import fuzzy_match

    for msg_id, expected in gt.items():
        actual = res_map.get(msg_id, [])
        
        matched_indices = set()
        missing_this_msg = []
        for exp in expected:
            matched = False
            for i, act in enumerate(actual):
                if i in matched_indices: continue
                if 'selection' in act and 'pick' not in act:
                    act['pick'] = act['selection']
                if fuzzy_match(exp, act):
                    matched = True
                    matched_indices.add(i)
                    break
            if not matched:
                missing_this_msg.append(exp)
                
        if missing_this_msg:
            msg_obj = messages.get(msg_id.replace('message_', ''), {})
            text = msg_obj.get('text', 'Unknown text')
            missing_details.append({
                'msg_id': msg_id,
                'expected': len(expected),
                'found': len(matched_indices),
                'actual_extracted_total': len(actual),
                'missing_items': missing_this_msg,
                'text': text
            })

    print(f"Messages with misses: {len(missing_details)}\n")
    for detail in missing_details:
        print(f"Msg: {detail['msg_id']}")
        expected = detail['expected']
        found = detail['found']
        actual_pulled = detail['actual_extracted_total']
        print(f"  Expected: {expected} | Matched: {found} | Total Pulled: {actual_pulled}")
        print("  Missed Items:")
        for m in detail['missing_items']:
            print(f"    - {m.get('p')} ({m.get('ty')})")
        print("\n  Text:")
        print(detail['text'])
        print("="*50)

if __name__ == '__main__':
    main()
