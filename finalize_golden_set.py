import json
import os
import re

def finalize_golden_sets():
    prompt_file = "ultimate_golden_set_prompt.txt"
    ai_output_file = "GoldenSetAIOutput.txt"
    
    ocr_output_file = r"benchmark\dataset\ocr_golden_set_v2.json"
    parsing_output_file = r"benchmark\dataset\parsing_golden_set_v2.json"

    # --- Step 1: Parse the Prompt File for OCR Data ---
    print(f"Reading {prompt_file}...")
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt_content = f.read()

    # Regex to find blocks: ### [ID]\nCONTENT
    # We look for "### [" then capture until the next "### [" or end of string
    # BUT we need to be careful about the "DATA TO PROCESS:" marker
    
    if "DATA TO PROCESS:" in prompt_content:
        data_section = prompt_content.split("DATA TO PROCESS:")[1]
    else:
        print("Error: Could not find 'DATA TO PROCESS:' section in prompt file.")
        return

    # Split by "### ["
    # resulting chunks will start with "ID]\nContent..."
    chunks = data_section.split("### [")
    
    ocr_data = {}
    
    for chunk in chunks:
        if not chunk.strip():
            continue
            
        if "]" not in chunk:
            continue
            
        msg_id, rest = chunk.split("]", 1)
        msg_id = msg_id.strip()
        message_text = rest.strip()
        
        if msg_id and message_text:
            ocr_data[f"message_{msg_id}"] = message_text

    print(f"Extracted {len(ocr_data)} raw messages for OCR Golden Set.")

    # --- Step 2: Parse AI Output for Parsing Data ---
    print(f"Reading {ai_output_file}...")
    with open(ai_output_file, 'r', encoding='utf-8') as f:
        # The file might contain markdown code blocks ```json ... ```
        content = f.read()
        
    # Clean markdown if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
        
    try:
        ai_data = json.loads(content)
        picks_list = ai_data.get("picks", [])
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from AI output: {e}")
        return

    # Group picks by message_id
    parsing_data = {}
    
    # We need to map standard fields to the benchmark "golden set" short keys if necessary
    # or just use the standard schema.
    # Looking at existing parsing_golden_set.json (viewed earlier):
    # keys: "id", "cn" (capper), "lg" (league), "ty" (type), "p" (pick), "od" (odds), "u" (units), "dt"
    
    pick_counters = {} # per message id

    for p in picks_list:
        msg_id = p.get("message_id")
        if not msg_id:
            continue
            
        key = f"message_{msg_id}"
        
        if key not in parsing_data:
            parsing_data[key] = []
            pick_counters[key] = 0
            
        pick_counters[key] += 1
        
        # Transform to golden set compact format
        golden_pick = {
            "id": pick_counters[key],
            "cn": p.get("capper_name"),
            "lg": p.get("sport"),        # 'sport' maps to 'lg' (League/Sport)
            "ty": p.get("bet_type"),     # 'bet_type' maps to 'ty'
            "p": p.get("selection"),     # 'selection' maps to 'p' (Pick)
            "od": p.get("odds"),         # 'odds' maps to 'od'
            "u": p.get("units"),         # 'units' maps to 'u'
            "dt": "2026-02-14"           # Hardcoded for this batch as identified
        }
        
        parsing_data[key].append(golden_pick)

    print(f"Extracted {sum(len(v) for v in parsing_data.values())} picks across {len(parsing_data)} messages for Parsing Golden Set.")

    # --- Step 3: Write Output Files ---
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(ocr_output_file), exist_ok=True)
    
    with open(ocr_output_file, 'w', encoding='utf-8') as f:
        json.dump(ocr_data, f, indent=4)
    print(f"Saved {ocr_output_file}")
    
    with open(parsing_output_file, 'w', encoding='utf-8') as f:
        json.dump(parsing_data, f, indent=4)
    print(f"Saved {parsing_output_file}")

if __name__ == "__main__":
    finalize_golden_sets()
