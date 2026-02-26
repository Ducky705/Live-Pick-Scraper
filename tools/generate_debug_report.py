import json
import os

output_dir = r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15\data\output'
debug_file = os.path.join(output_dir, 'debug_msgs.json')
picks_file = os.path.join(output_dir, 'picks_2026-01-24.json')
artifact_file = r'C:\Users\diego\.gemini\antigravity\brain\242d89c9-2047-4102-8d5f-e766c87e12bc\debug_report.md'

with open(debug_file, 'r', encoding='utf-8') as f:
    msgs = json.load(f)
    
with open(picks_file, 'r', encoding='utf-8') as f:
    picks = json.load(f)

# Build OCR map
msg_ocr = {}
for m in msgs:
    m_id = str(m.get('id', ''))
    if not m_id and m.get('telegram_id'):
        m_id = "tg_" + str(m.get('telegram_id'))
    elif not m_id and m.get('tweet_id'):
        m_id = "tw_" + str(m.get('tweet_id'))
    ocr = m.get('ocr_text', '')
    if m_id:
        msg_ocr[m_id] = ocr

picks_with_odds = sum(1 for p in picks if p.get('odds') is not None and str(p.get('odds')).strip() != '')
picks_with_results = sum(1 for p in picks if p.get('result') not in ['Pending', 'Pending/Unknown', None, ''])
wins = sum(1 for p in picks if p.get('result') == 'Win')
losses = sum(1 for p in picks if p.get('result') == 'Loss')
pushes = sum(1 for p in picks if p.get('result') == 'Push')

report = []
report.append('# Production Run Debug Report (2026-01-24)')
report.append('')
report.append('## Run Stats')
report.append('- **Total Run Time**: ~5 minutes 35 seconds (14:10:17 to 14:15:52)')
report.append(f'- **Total Picks Extracted**: {len(picks)}')
report.append(f'- **Picks with Odds**: {picks_with_odds}')
report.append(f'- **Picks with Results**: {picks_with_results} (Wins: {wins}, Losses: {losses}, Pushes: {pushes})')
report.append(f'- **Pending/Unknown**: {len(picks) - picks_with_results}')
report.append('')

report.append('## Errors & Parser Issues')
issues = []
for p in picks:
    if not p.get('pick') or str(p.get('pick')).strip().lower() == 'unknown':
        issues.append(f'- Pick ID `{p.get("id")}` has missing or unknown pick name.')
    if not p.get('league') or str(p.get('league')).strip().lower() == 'unknown':
        issues.append(f'- Pick ID `{p.get("id")}` has missing or unknown league.')

if not issues:
    report.append('No critical structural parsing errors found.')
else:
    for i in issues:
        report.append(i)
report.append('')

report.append('## OCR vs Parser Results')
report.append('Below is the raw text + OCR and the structured parsed output for every pick.')
report.append('')

for i, p in enumerate(picks):
    m_id = str(p.get('message_id', ''))
    ocr_text = msg_ocr.get(m_id, '')
    if not ocr_text:
        ocr_text = 'None / Text-only pick / No OCR mapped'
    
    report.append(f'### Pick {i+1}: {p.get("capper_name", "Unknown")} - {p.get("pick", "Unknown")}')
    report.append('**Raw Text + OCR:**')
    report.append('```text')
    
    raw_str = str(p.get('raw_text', ''))
    combined_text = raw_str
    if ocr_text != 'None / Text-only pick / No OCR mapped':
        combined_text += '\n--- OCR ---\n' + str(ocr_text)
    
    report.append(combined_text.strip())
    report.append('```')
    
    report.append('**Parsed Result:**')
    report.append('```json')
    report.append(json.dumps(p, indent=2))
    report.append('```')
    report.append('')

with open(artifact_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print(f'Wrote debug report to {artifact_file}')
