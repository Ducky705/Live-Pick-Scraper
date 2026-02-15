import json
import os

def main():
    file_path = "debug_raw_tweets.json"
    if not os.path.exists(file_path):
        print("No debug_raw_tweets.json found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        tweets = json.load(f)

    # Write to Markdown file
    output_lines = []
    output_lines.append(f"## Tweets from @EZMSports (Parsed)\n")
    output_lines.append(f"Parsed {len(tweets)} tweets.\n")
    
    current_date = None
    
    for t in tweets:
        date_str = t.get("date", "")
        # date format: 2026-02-15 00:56 ET
        day = date_str.split(" ")[0]
        
        if day != current_date:
            output_lines.append(f"\n### {day}\n")
            current_date = day
            
        text = t.get("text", "").replace("\n", " <br> ")
        output_lines.append(f"- **{date_str}**")
        output_lines.append(f"> {text}\n")
        
    with open("parsed_tweets.md", "w", encoding="utf-8") as f:
        f.writelines([l + "\n" for l in output_lines])
        
    print("Formatted tweets saved to parsed_tweets.md")

if __name__ == "__main__":
    main()
