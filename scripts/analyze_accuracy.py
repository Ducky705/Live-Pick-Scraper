import re

def analyze_report(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split report by messages
    parts = content.split("## Message ID:")
    
    total_msgs = 0
    no_picks_count = 0
    valid_misses = 0
    true_failures = 0
    
    failure_details = []

    # Skip header
    for part in parts[1:]:
        total_msgs += 1
        
        # Check if picks were extracted
        if "No picks extracted from this message" in part:
            no_picks_count += 1
            
            # Extract Text
            text_match = re.search(r"\*\*Text:\*\*\n> (.*?)(\n\n|$)", part, re.DOTALL)
            text = text_match.group(1).strip() if text_match else ""
            
            # Heuristics for Valid Miss (Noise)
            is_noise = False
            
            # 1. Short text (likely chat)
            if len(text) < 15:
                is_noise = True
                
            # 2. URL only
            if "http" in text or "t.co" in text:
                is_noise = True
                
            # 3. Chat keywords
            chat_keywords = ["joined", "pinned", "deleted", "promo", "discount", "check out", "subscribe", "dm me", "message me"]
            if any(k in text.lower() for k in chat_keywords):
                is_noise = True
                
            # 4. Question marks (likely asking, not telling)
            if "?" in text:
                is_noise = True

            if is_noise:
                valid_misses += 1
            else:
                true_failures += 1
                failure_details.append(text[:100].replace("\n", " "))

    print(f"Total Processed: {total_msgs}")
    print(f"Messages with Picks: {total_msgs - no_picks_count}")
    print(f"No Picks: {no_picks_count}")
    print(f"  - Valid Misses (Noise/Chat/Ads): {valid_misses}")
    print(f"  - True Failures (Missed Picks): {true_failures}")
    
    match_rate = (total_msgs - no_picks_count) / total_msgs
    accuracy_adjusted = (total_msgs - true_failures) / total_msgs
    
    print(f"\nRaw Extraction Rate: {match_rate:.2%}")
    print(f"Adjusted Accuracy (Excluding Noise): {accuracy_adjusted:.2%}")
    
    if true_failures > 0:
        print("\n--- Failed Messages (First 100 chars) ---")
        for f in failure_details:
            try:
                print(f"- {f}")
            except UnicodeEncodeError:
                print(f"- {f.encode('ascii', 'replace').decode('ascii')}")

if __name__ == "__main__":
    analyze_report("src/data/output/verification_report_2026-02-14.md")
