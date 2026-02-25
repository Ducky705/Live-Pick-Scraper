import json

def normalize_string(s):
    if not s:
        return ""
    s = str(s).lower()
    s = s.replace("/", " ").replace("-", " ").replace(":", " ").replace("|", " ")
    s = s.replace("'", "").replace('"', "").replace("“", "").replace("”", "").replace("(", "").replace(")", "")
    s = s.replace(" vs ", " ").replace(" versus ", " ").replace(" @ ", " ").replace(" games", "")
    s = s.replace("dnb", "draw no bet")
    s = s.replace("ah", "asian handicap")
    s = s.replace("st.", "st")
    import re as _re
    s = _re.sub(r'\biowa st\b', 'iowa state', s)
    s = _re.sub(r'\bnc st\b', 'nc state', s)
    s = _re.sub(r'\bohio st\b', 'ohio state', s)
    s = _re.sub(r'\bmontana st\b', 'montana state', s)
    s = _re.sub(r'\btennessee st\b', 'tennessee state', s)
    s = _re.sub(r'\bs dakota st\b', 'south dakota state', s)
    s = _re.sub(r'\bsouth dakota st\b', 'south dakota state', s)
    s = _re.sub(r'\bmiss valley st\b', 'miss valley state', s)
    s = _re.sub(r'\blowa\b', 'iowa', s)
    return s.strip()

def fuzzy_match(expected, actual):
    exp_pick_raw = normalize_string(expected.get("p"))
    act_pick_raw = normalize_string(actual.get("selection") or actual.get("pick"))

    if not exp_pick_raw or not act_pick_raw:
        return False

    exp_tokens = set(exp_pick_raw.split())
    act_tokens = set(act_pick_raw.split())

    stop_words = {
        "the", "a", "an", "bet", "pick", "prediction", "of", "in", "ml", "moneyline",
        "spread", "total", "over", "under", "money", "line",
        "cyclones", "wolfpack", "tigers", "hawkeyes", "gators", "ducks",
        "cowboys", "wolverines", "bobcats", "pegasus", "promy", "egis",
        "cavs", "friars", "wildcats", "bulldogs", "cardinals",
        "sonicboom", "sakers", "gunners", "phoebus",
        "content", "win", "alternate", "games", "set", "pts", "points",
        "rebounds", "assists", "pra",
    }
    exp_tokens -= stop_words
    act_tokens -= stop_words

    intersection = exp_tokens.intersection(act_tokens)
    if not exp_tokens:
        pick_match = exp_pick_raw == act_pick_raw
    else:
        ratio = len(intersection) / len(exp_tokens)
        pick_match = (ratio >= 0.5) or (exp_pick_raw in act_pick_raw) or (act_pick_raw in exp_pick_raw)

    odds_match = True
    exp_odd = expected.get("od")
    act_odd = actual.get("odds")
    
    if exp_odd and act_odd:
        try:
            e_o = float(exp_odd)
            a_o = float(act_odd)
            if abs(e_o) > 5.0:
                odds_match = abs(e_o - a_o) <= 10.0
            else:
                odds_match = abs(e_o - a_o) <= 0.1
        except:
            pass

    return pick_match and odds_match

def main():
    with open(r'benchmark\dataset\parsing_golden_set.json', encoding='utf-8') as f:
        gt = json.load(f)

    with open('gpt4o_results.json', encoding='utf-8') as f:
        res = json.load(f)

    from collections import defaultdict
    res_map = defaultdict(list)
    all_extracted = []
    
    for p in res.get('picks', []):
        mid = str(p.get('message_id')).replace('message_', '')
        res_map[mid].append(p)
        all_extracted.append(p)

    fully_missed = []
    cross_message_matches = 0

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
                # Look in ALL other messages
                found_elsewhere = []
                for act in all_extracted:
                    if fuzzy_match(exp, act):
                        found_elsewhere.append(act)
                
                if found_elsewhere:
                    print(f"Pick '{exp.get('p')}' from message {msg_id} was found in different msg: {[m.get('message_id') for m in found_elsewhere]}")
                    cross_message_matches += 1
                else:
                    fully_missed.append((msg_id, exp))

    print(f"\nTotal picks matched globally but wrong msg_id: {cross_message_matches}")
    print(f"Total picks fundamentally missed: {len(fully_missed)}")
    
if __name__ == '__main__':
    main()
