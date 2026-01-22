import json
import os
import re

def main():
    filepath = 'golden_set/golden_set_v2.json'
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total entries: {len(data)}")
    
    suspicious_count = 0
    empty_picks_count = 0
    ocr_error_count = 0
    unknown_capper_count = 0
    
    for i, item in enumerate(data):
        item_id = item.get('id')
        ocr_texts = item.get('ocr_texts', [])
        picks = item.get('expected_picks', [])
        
        # Check for OCR errors
        is_ocr_error = False
        for text in ocr_texts:
            if "error" in text.lower() or "unexpected keyword" in text.lower():
                is_ocr_error = True
                ocr_error_count += 1
                print(f"\n[#{i} ID:{item_id}] OCR Error detected:")
                print(f"  OCR: {text[:100]}...")
                
        # Check for empty picks
        if not picks:
            # Maybe it's valid empty? (e.g. just a chat message)
            # But let's flag it if there is significant text/OCR
            has_content = len(item.get('original_text', '')) > 20 or (ocr_texts and len(ocr_texts[0]) > 20)
            if has_content:
                empty_picks_count += 1
                print(f"\n[#{i} ID:{item_id}] Empty picks with content:")
                print(f"  Text: {item.get('original_text', '')[:100]}...")
                if ocr_texts:
                    print(f"  OCR: {ocr_texts[0][:100]}...")
        
        # Check for Unknown Capper
        for p in picks:
            if p.get('cn') == 'Unknown':
                unknown_capper_count += 1
                print(f"\n[#{i} ID:{item_id}] Unknown Capper in pick: {p['p']}")
                
        # Heuristic check: does pick text look valid?
        for p in picks:
            pick_text = p.get('p')
            if not pick_text or len(pick_text) < 3:
                 print(f"\n[#{i} ID:{item_id}] Suspicious pick text: '{pick_text}'")

    print("\n--- Summary ---")
    print(f"OCR Errors: {ocr_error_count}")
    print(f"Empty Picks (with content): {empty_picks_count}")
    print(f"Unknown Cappers: {unknown_capper_count}")

if __name__ == "__main__":
    main()
