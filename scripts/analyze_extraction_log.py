
import json
import logging
import re
import os

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Absolute Path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "src", "data", "debug_extraction_log_2026-02-10.json")

def analyze_log():
    try:
        with open(LOG_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Log file not found: {LOG_FILE}")
        return

    total_msgs = len(data)
    total_extracted_picks = 0
    total_parsed_picks = 0
    msgs_with_drops = []

    print(f"--- EXTRACTION ANALYSIS: {os.path.basename(LOG_FILE)} ---")
    print(f"Total Messages Processed: {total_msgs}")

    for i, entry in enumerate(data):
        raw_ai_text = entry.get('raw_response', '[]')
        final_picks = entry.get('parsed_picks', [])

        # Parse AI response
        ai_picks = []
        try:
            cleaned = raw_ai_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            ai_picks = json.loads(cleaned)
            if not isinstance(ai_picks, list):
                ai_picks = [] # Should be list of dicts
        except json.JSONDecodeError:
            pass # Failed to parse AI JSON

        num_ai = len(ai_picks)
        num_final = len(final_picks)

        total_extracted_picks += num_ai
        total_parsed_picks += num_final

        if num_ai > num_final:
            msgs_with_drops.append({
                "msg_idx": i,
                "msg_id": entry.get('message_id', 'unknown'),
                "ai_count": num_ai,
                "final_count": num_final,
                "dropped": num_ai - num_final,
                "ai_picks": ai_picks,
                "reason": "Parsed count lower than Extracted count"
            })

    print(f"Total Picks Extracted (AI): {total_extracted_picks}")
    print(f"Total Picks Parsed (Final): {total_parsed_picks}")
    
    if total_extracted_picks > 0:
        retention = (total_parsed_picks / total_extracted_picks) * 100
        print(f"Retention Rate: {retention:.1f}%")
        print(f"Dropped Picks: {total_extracted_picks - total_parsed_picks}")
    else:
        print("No picks extracted.")

    if msgs_with_drops:
        print("\n--- SAMPLE DROPPED PICKS ---")
        for drop in msgs_with_drops[:5]:
            print(f"Msg {drop['msg_id']}: AI found {drop['ai_count']}, Final has {drop['final_count']} (Dropped {drop['dropped']})")
            print(f"  AI Picks: {json.dumps(drop['ai_picks'], indent=2)}")
            print(f"  Input Text Snippet: {entry.get('input_text', '')[:500]}...")

    print("\n--- MANUAL RECALL POOL (Sample of 3 Successful Messages) ---")
    successful_msgs = [m for i, m in enumerate(data) if len(m.get('parsed_picks', [])) > 0 and i not in [d['msg_idx'] for d in msgs_with_drops]]
    
    for msg in successful_msgs[:3]:
        # Try different keys for input text
        input_content = msg.get('input_text') or msg.get('input_batch') or msg.get('batch_text') or ''
        
        if isinstance(input_content, list):
            input_str = "\n---\n".join([str(s) for s in input_content])
        else:
            input_str = str(input_content)

        print(f"\nMsg {msg.get('message_id')}:")
        print(f"Input Text (Snippet):\n{input_str[:1000]}...")
        print(f"AI Picks ({len(msg.get('parsed_picks', []))}):")
        # Just print concise summary
        for p in msg.get('parsed_picks', []):
             print(f" - {p.get('pick')} ({p.get('odds')})")

if __name__ == "__main__":
    analyze_log()
