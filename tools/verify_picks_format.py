import json

picks_file = r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15\data\output\picks_2026-01-24.json'

with open(picks_file, 'r', encoding='utf-8') as f:
    picks = json.load(f)

issues = []
for i, p in enumerate(picks):
    pick_str = p.get('pick', '')
    p_type = p.get('type', '')
    
    if p_type == 'Unknown' or not pick_str or pick_str == 'Unknown':
        issues.append(f"Missing/Unknown data: Pick {i+1} - {p.get('capper_name')} - {pick_str}")
        
    if p_type == 'Total':
        if ' vs ' not in pick_str:
            issues.append(f"Total mismatch: Pick {i+1} - '{pick_str}' lacks 'Team A vs Team B'")
            
    if p_type == 'Moneyline':
        if ' ML' not in pick_str:
            issues.append(f"Moneyline mismatch: Pick {i+1} - '{pick_str}' lacks ' ML'")
            
    if p_type == 'Player Prop':
        if ':' not in pick_str:
            issues.append(f"Player Prop mismatch: Pick {i+1} - '{pick_str}' lacks ':'")

if len(issues) == 0:
    print('All picks passed basic format checks based on docs/pick_format.md.')
else:
    print(f'Found {len(issues)} structural issues:')
    for issue in issues:
        print(f' - {issue}')
