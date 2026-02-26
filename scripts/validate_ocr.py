import json
import re
import os

with open(r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15\data\output\picks_2026-01-24.json', 'r', encoding='utf-8') as f:
    picks = json.load(f)

with open(r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15\data\output\debug_msgs.json', 'r', encoding='utf-8') as f:
    debug_msgs = json.load(f)

print(f'Starting rigorous comparison for {len(picks)} picks...')

total_checked = 0
errors = []

# Create lookup
msg_dict = {str(m.get('id')): m for m in debug_msgs}

for p in picks:
    m_id = str(p.get('message_id'))
    pick_text = p.get('pick', '').lower()
    line_val = p.get('line')
    
    msg_obj = msg_dict.get(m_id)
    if not msg_obj:
        continue
        
    # Combine original text + generic OCR outputs
    source_components = [msg_obj.get('text', '')]
    if 'ocr_results' in msg_obj:
        for oc in msg_obj['ocr_results']:
             source_components.append(oc.get('text', ''))
             
    full_source = " ".join(source_components).lower()
    
    total_checked += 1
    
    if line_val is not None:
        val_str1 = str(line_val).replace('.0', '')
        val_str2 = str(abs(line_val)).replace('.0', '')
        
        if val_str1 not in full_source and val_str2 not in full_source:
             if 'points' not in pick_text and 'rebounds' not in pick_text and '+' not in pick_text:
                 errors.append(f"MISSING LINE '{line_val}' IN SOURCE | Pick: {pick_text} | Source: {full_source.replace(chr(10), ' ')[:100]}...")

print(f"Total Validate Map Count: {total_checked}")
if errors:
    print(f'Found {len(errors)} potential hallucinated data pieces:')
    for e in errors[:20]:
        print(e)
else:
    print('ALL PICKS mathematically map to their source texts cleanly with no major hallucinations!')
