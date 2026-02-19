import json

def debug_length():
    with open("src/data/output/debug_msgs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    target_ids = ["32103", "2022539191931035843", "2022538739126333839"]
    for mid in target_ids:
        try:
            m = next(m for m in data if str(m["id"]) == mid)
            text_len = len(m.get("text", ""))
            ocr_len = len(m.get("ocr_text", ""))
            print(f"Message {mid}:")
            print(f"  Text Length: {text_len}")
            print(f"  OCR Length: {ocr_len}")
            print(f"  Text Snippet: {repr(m.get('text', '')[:100])}")
        except StopIteration:
            print(f"Message {mid} not found.")

if __name__ == "__main__":
    debug_length()
