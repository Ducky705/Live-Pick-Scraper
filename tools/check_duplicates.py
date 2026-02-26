import json

picks_file = r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15\data\output\picks_2026-01-24.json'
with open(picks_file, 'r', encoding='utf-8') as f:
    picks = json.load(f)

print(f'Total picks in JSON: {len(picks)}')

unique_signatures = set()
duplicates = 0
for p in picks:
    sig = f"{p.get('capper_name')}_{p.get('pick')}_{p.get('league')}"
    if sig in unique_signatures:
        duplicates += 1
    else:
        unique_signatures.add(sig)

print(f'Duplicate picks in JSON: {duplicates}')
print(f'Unique picks to upload: {len(picks) - duplicates}')
