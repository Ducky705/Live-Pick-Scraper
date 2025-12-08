# src/prompt_builder.py
import json
from datetime import datetime

def get_master_formatting_guide():
    return """
### **Sports Pick Data Formatting Guide**

### **1. Handling Multiple Cappers (CRITICAL)**
*   **Scenario:** A single message often contains picks from multiple people.
*   **Action:** Separate these into distinct JSON objects.

### **2. Standardized `league` Values**
Use ONLY: `NFL`, `NCAAF`, `NBA`, `NCAAB`, `WNBA`, `MLB`, `KBO`, `NHL`, `CFL`, `UFC`, `PFL`, `TENNIS`, `PGA`, `F1`, `EPL`, `MLS`, `UCL`, `SOCCER`.

### **3. `pick` Format Specification**
*   **Moneyline:** `Team Name ML` (e.g., `Lakers ML`)
*   **Spread:** `Team Name -7.5` (Always include the team)
*   **Total:** `Team A vs Team B Over 215.5` (Always include the matchup)
*   **Player Prop:** `Player Name: Stat Over/Under/Value`
"""

def generate_ai_prompt(selected_data):
    raw_content_list = []
    for item in selected_data:
        entry = f"--- START MESSAGE ID: {item['id']} ---"
        
        text_content = item.get('text', '').strip()
        ocr_content = item.get('ocr_text', '').strip()
        
        if text_content:
            entry += f"\n[CAPTION]:\n{text_content}\n"
        
        if ocr_content:
            entry += f"\n[IMAGE OCR]:\n{ocr_content}\n"
            
        entry += f"--- END MESSAGE ID: {item['id']} ---\n"
        raw_content_list.append(entry)
        
    full_raw_data = "\n".join(raw_content_list)
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0 ***
*** OUTPUT FORMAT: SINGLE LINE RAW JSON ONLY. NO MARKDOWN. NO CODE BLOCKS. ***

You are an expert sports betting data parser. Extract betting picks.

### **CRITICAL INSTRUCTIONS**
1.  **Capper Identification:** 
    *   Look for names in the [CAPTION] first, then Top 3 Lines of [IMAGE OCR].
2.  **Image vs Caption:** 
    *   Map the name from Caption to the lines in OCR.
3.  **Odds Handling:** 
    *   Extract American odds (e.g., -110, +150) into `odds`.
    *   **IMPORTANT:** If odds are NOT visible in the text or image, set `"odds": null`. DO NOT GUESS -110.
4.  **Units:** 
    *   Extract "Units", "U", or "Diamond" count. Default to 1.0.

{get_master_formatting_guide()}

### **REQUIRED OUTPUT FORMAT (JSON ARRAY)**
Respond ONLY with a single, unbroken line of valid JSON.
[
  {{
    "message_id": 12345,
    "capper_name": "KingCap",
    "league": "NBA", 
    "type": "Player Prop",
    "pick": "Anthony Edwards: Steals Over 2.5",
    "odds": -110, 
    "units": 1.0,
    "date": "{current_date}" 
  }}
]
(Note: Use "odds": null if unknown)

### **RAW DATA**
{full_raw_data}
"""
    return prompt

def generate_revision_prompt(failed_items):
    items_json = json.dumps(failed_items)
    return f"""
*** OUTPUT FORMAT: SINGLE LINE RAW JSON ONLY. NO MARKDOWN. ***

You are a data correction specialist. The items below have "Unknown" fields.
Fix the `capper_name`, `league`, and `type`.

INPUT: {items_json}

OUTPUT (JSON Array of fixed objects):
"""

def generate_smart_fill_prompt(unknown_items):
    items_json = json.dumps(unknown_items)
    return f"""
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0.1 ***
*** OUTPUT FORMAT: SINGLE LINE RAW JSON ONLY. NO MARKDOWN. ***

Your Goal: Identify the **Capper Name** for these items where the previous pass failed.

INPUT DATA:
{items_json}

OUTPUT (JSON Array of objects):
[
  {{ "message_id": 123, "pick": "...", "capper_name": "FoundName" }}
]
"""