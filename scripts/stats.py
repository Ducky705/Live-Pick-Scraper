import json
import os

dates = ['2026-01-25', '2026-01-26', '2026-01-27', '2026-01-28']
base_dir = r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15\data\output'

total_picks = 0
total_odds = 0
total_graded = 0

stats = {}

for d in dates:
    fpath = os.path.join(base_dir, f'picks_{d}.json')
    if os.path.exists(fpath):
        with open(fpath, 'r', encoding='utf-8') as f:
            picks = json.load(f)
            
        c_picks = len(picks)
        c_odds = sum(1 for p in picks if p.get('odds'))
        c_graded = sum(1 for p in picks if p.get('result') not in [None, 'Pending'])
        
        total_picks += c_picks
        total_odds += c_odds
        total_graded += c_graded
        
        stats[d] = {
            'picks': c_picks,
            'odds': c_odds,
            'graded': c_graded
        }
    else:
        stats[d] = 'File not found - run failed or found 0 picks'

print('--- MULTI-DAY RUN RESULTS ---')
for d, s in stats.items():
    if isinstance(s, dict):
        print(f"{d}: {s['picks']} picks extracted | {s['graded']} fully graded | {s['odds']} with odds")
    else:
        print(f"{d}: {s}")

print('\n--- GRAND TOTALS ---')
print(f'Total Picks Extracted: {total_picks}')
print(f'Total Picks with ESPN Odds Maps: {total_odds}')
print(f'Total Picks Fully Graded (Win/Loss/Push): {total_graded}')
