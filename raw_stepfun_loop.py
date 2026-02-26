import json
import os
import requests

def run_raw_benchmark():
    api_key = os.getenv("OPENROUTER_API_KEY")
    ocr_file = r"benchmark\dataset\ocr_golden_set.json"
    
    with open(ocr_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
        
    all_picks = []
    
    def process_msg(msg_id, text):
        prompt = f"""
You are an expert sports betting analyst. Extract all sports picks from this message context and output JSON.

Rules:
- Output {{"picks": [ {{ "capper_name", "sport", "bet_type", "selection", "line", "odds", "units" }} ] }}
- Extract every single pick.
- For parlays, try to separate the legs if possible or combine them into Bet Type "Parlay".

Message ID: {msg_id}
Text:
{text}
        """

        payload = {
            "model": "stepfun/step-3.5-flash:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            # "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram-scraper.local",
            "X-Title": "CapperSuite",
        }
        
        try:
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                j = resp.json()
                if "choices" in j:
                    content = j["choices"][0]["message"]["content"]
                    if "```json" in content:
                        content = content.split("```json")[-1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[-1].split("```")[0].strip()
                    
                    data = json.loads(content)
                    
                    # Tag with message ID if missing
                    for pick in data.get("picks", []):
                        pick["message_id"] = msg_id
                        all_picks.append(pick)
                    return True
        except Exception as e:
            print(f"Failed {msg_id}: {e}")
        return False

    print(f"Processing {len(ocr_data)} messages strictly sequentially... This will take ~60 minutes if rate limits are hit 1/min")
    count = 0
    for key, text in ocr_data.items():
        mid = key.replace("message_", "")
        success = False
        attempts = 0
        while not success and attempts < 3:
            success = process_msg(mid, text)
            if not success:
                import time
                time.sleep(15) 
            attempts += 1
        count += 1
        print(f"[{count}/{len(ocr_data)}] Processed {mid}. Success: {success}. Collected {len(all_picks)} total so far.")
        
        # Write incremental just in case
        with open("raw_stepfun_results.json", "w", encoding="utf-8") as f:
            json.dump({"picks": all_picks}, f)

if __name__ == "__main__":
    run_raw_benchmark()
