import json
import os
from collections import defaultdict

def create_goldenset():
    input_file = r"src\data\output\picks_2026-02-14_manual.json"
    ocr_output_file = r"benchmark\dataset\ocr_golden_set_saturday.json"
    parsing_output_file = r"benchmark\dataset\parsing_golden_set_saturday.json"

    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ocr_data = {}
    parsing_data = defaultdict(list)

    pick_counters = defaultdict(int)

    for entry in data:
        msg_id = entry.get("message_id")
        if not msg_id:
            continue
        
        key = f"message_{msg_id}"
        
        # Populate OCR data (only once per message, but we might overwrite with same text)
        source_text = entry.get("_source_text", "")
        if source_text:
             ocr_data[key] = source_text

        # Populate Parsing data
        pick_counters[key] += 1
        
        pick_obj = {
            "id": pick_counters[key],
            "cn": entry.get("capper_name"),
            "lg": entry.get("league"),
            "ty": entry.get("type"),
            "p": entry.get("pick"),
            "od": entry.get("odds"),
            "u": entry.get("units"),
            "dt": entry.get("game_date", "2026-02-14") 
        }
        parsing_data[key].append(pick_obj)

    # Write OCR Golden Set
    with open(ocr_output_file, 'w', encoding='utf-8') as f:
        json.dump(ocr_data, f, indent=4)
    print(f"Created {ocr_output_file} with {len(ocr_data)} entries.")

    # Write Parsing Golden Set
    with open(parsing_output_file, 'w', encoding='utf-8') as f:
        json.dump(parsing_data, f, indent=4)
    print(f"Created {parsing_output_file} with {len(parsing_data)} entries.")

if __name__ == "__main__":
    create_goldenset()
