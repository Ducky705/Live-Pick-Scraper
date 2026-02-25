import json
from collections import defaultdict

def main():
    with open(r'benchmark\dataset\parsing_golden_set.json', encoding='utf-8') as f:
        gt = json.load(f)

    with open('gpt4o_results.json', encoding='utf-8') as f:
        res = json.load(f)

    res_map = defaultdict(list)
    for p in res.get('picks', []):
        mid = str(p.get('message_id')).replace('message_', '')
        res_map[mid].append(p)

    missed_ids = [
        '32093', '32089', '2022722061203050528', '2023061476768948236',
        '2022803270930960546', '2022803231118668208', '2022786483854156079',
        '2022720997825073552', '2022717139854016649', '2022887457482477609',
        '2023058787276402808', '2022723805852860664', '2022911896568107480',
        '2022746497536950293', '2022539191931035843'
    ]

    for msg_id in missed_ids:
        print(f'=== MSG: {msg_id} ===')
        actual = res_map.get(msg_id, [])
        for p in actual:
            print(f'  [GPT] {p.get("capper_name", "")} | {p.get("selection", "")} | {p.get("bet_type", "")} | Line: {p.get("line")}')
        print('  [EXPECTED]:')
        for e in gt.get('message_' + msg_id, []):
            print(f'    {e.get("c")} | {e.get("p")} | {e.get("ty")}')
        print()

if __name__ == '__main__':
    main()
