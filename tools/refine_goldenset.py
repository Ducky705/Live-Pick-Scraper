import json
import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.getcwd())

from src.ocr_handler import extract_text
from src.openrouter_client import openrouter_completion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Strong model for judging correctness
JUDGE_MODEL = "google/gemini-2.0-flash-exp:free"

def refine_item(item):
    item_id = item['id']
    logging.info(f"Refining item {item_id}...")
    
    # 1. Check for bad OCR and fix it
    ocr_texts = item.get('ocr_texts', [])
    bad_ocr = False
    new_ocr_texts = []
    
    # Identify if OCR needs running
    if not ocr_texts or any("error" in t.lower() for t in ocr_texts) or any("unexpected keyword" in t.lower() for t in ocr_texts):
        bad_ocr = True
    
    if bad_ocr and item.get('image_paths'):
        logging.info(f"Re-running OCR for {item_id} due to missing/error text...")
        for img_path in item['image_paths']:
            if os.path.exists(img_path):
                try:
                    # Using extract_text which defaults to AI OCR now
                    text = extract_text(img_path)
                    if text and not "error" in text.lower():
                        new_ocr_texts.append(text)
                    else:
                        logging.warning(f"OCR failed again for {img_path}: {text}")
                except Exception as e:
                    logging.error(f"OCR exception for {img_path}: {e}")
        
        if new_ocr_texts:
            item['ocr_texts'] = new_ocr_texts
            logging.info(f"Updated OCR for {item_id}")

    # 2. Construct Judge Prompt
    context_text = f"Original Text: {item.get('original_text', '')}\n"
    for i, txt in enumerate(item.get('ocr_texts', [])):
        context_text += f"OCR Text {i+1}: {txt}\n"
        
    current_picks = json.dumps(item.get('expected_picks', []), indent=None, separators=(',', ':'))
    
    # Ultra-compact auditor prompt (~60% token reduction)
    prompt = f"""TEMP:0.1 Sports Betting Auditor. Verify and fix picks.

CONTEXT:
{context_text[:1500]}

CURRENT PICKS:
{current_picks}

TASKS:
1.Compare picks to context,identify all bets
2.Fix errors(wrong odds,teams,Unknown fields)
3.Remove duplicates
4.c=capper from @handle or name
5.l=specific league(NBA,NFL,NCAAB,etc)
6.t=ML,SP,TL,PP,TP,GP,PD,PL,TS,FT,UK
7.Skip noise(Whale,Max Bet,Guaranteed)
8.If no picks,return empty []

OUTPUT:{{"picks":[{{"i":123,"c":"Dave","l":"NBA","p":"Lakers -5","u":1}}]}}"""
    
    # 3. Call LLM
    try:
        # Pass images if available for Vision verification
        images = item.get('image_paths', [])
        
        response = openrouter_completion(prompt, model=JUDGE_MODEL, images=images, timeout=60)
        
        clean_resp = response.strip()
        if clean_resp.startswith("```json"):
            clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
        elif clean_resp.startswith("```"):
             clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
             
        data = json.loads(clean_resp)
        corrected_picks = data.get('picks', [])
        
        # Merge ID back if missing
        for p in corrected_picks:
            if 'id' not in p:
                p['id'] = item_id
                
        item['expected_picks'] = corrected_picks
        logging.info(f"Refined {item_id}: {len(corrected_picks)} picks.")
        
    except Exception as e:
        logging.error(f"Refinement failed for {item_id}: {e}")
        # Keep original if failed
        
    return item

def main():
    input_file = 'golden_set/golden_set_v2.json'
    output_file = 'golden_set/golden_set_final.json'
    
    if not os.path.exists(input_file):
        print("Input file not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    logging.info(f"Loaded {len(data)} items for refinement.")
    
    refined_data = []
    
    # Parallel processing
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(refine_item, item): item['id'] for item in data}
        
        for future in as_completed(futures):
            try:
                result = future.result()
                refined_data.append(result)
            except Exception as e:
                logging.error(f"Error in future: {e}")
                
    # Sort by ID to keep it tidy
    refined_data.sort(key=lambda x: str(x['id']))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(refined_data, f, indent=2)
        
    logging.info(f"Refined Golden Set saved to {output_file}")

if __name__ == "__main__":
    main()
