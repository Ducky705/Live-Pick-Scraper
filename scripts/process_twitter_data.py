import json
import os

def main():
    tweets_file = "debug_raw_tweets.json"
    response_file = "debug_ai_response.txt"
    
    if not os.path.exists(tweets_file) or not os.path.exists(response_file):
        print("Missing data files.")
        return

    # Load Tweets
    with open(tweets_file, "r", encoding="utf-8") as f:
        tweets = json.load(f)
    
    # Map ID to Date/Text
    tweet_map = {str(t["id"]): t for t in tweets}
    
    # Load Picks directly from JSON
    picks_file = "twitter_picks.json"
    if not os.path.exists(picks_file):
        print("Missing picks file.")
        return
        
    with open(picks_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        picks = data.get("picks", [])

    print(f"Found {len(picks)} picks.")
    
    # Enriched Picks
    enriched_picks = []
    for p in picks:
        pid = str(p.get("i") or p.get("id") or "")
        tweet = tweet_map.get(pid)
        if tweet:
            p["date"] = tweet["date"]
            p["tweet_text"] = tweet["text"]
            enriched_picks.append(p)
        else:
            # Pick might not have ID or ID mismatch?
            # Try to match by index if strict order? Unreliable.
            pass
            
    # Sort by Date
    enriched_picks.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    # Generate Markdown
    lines = []
    lines.append("## Analyzed Picks (Matches Found)")
    lines.append(f"Total Picks: {len(enriched_picks)}")
    
    # Group by Date
    current_date = None
    
    import html
    
    for p in enriched_picks:
        date_str = p.get("date", "")
        day = date_str.split(" ")[0]
        
        if day != current_date:
            lines.append(f"\n### {day}\n")
            lines.append("| Time | Capper | League | Pick | Odds | Units |")
            lines.append("|---|---|---|---|---|---|")
            current_date = day
            
        time_part = date_str.split(" ")[1] if " " in date_str else ""
        capper = p.get("c", p.get("capper_name", "Unknown"))
        league = p.get("l", p.get("league", "-"))
        pick_name = p.get("p", p.get("pick", "-"))
        
        odds = p.get("o", p.get("odds"))
        if odds is None:
            odds = "-"
            
        units = p.get("u", p.get("units"))
        if units is None:
            units = "-"
            
        pick_type = p.get("t", p.get("type", ""))

        # HTML Unescape
        pick_name = html.unescape(pick_name)
        capper = html.unescape(capper)

        # Format Totals
        # Check for TL type OR if pick looks like a total (contains / and o/u number)
        # Regex check: looks for slash, and words starting with o/u followed by number
        is_total = pick_type == "TL" or (
            "/" in pick_name and re.search(r'\b[ou]\d', pick_name)
        )

        if is_total:
             # Replace / with vs
             # Handle spaces: "A/B" -> "A vs B", "A / B" -> "A vs B"
             pick_name = re.sub(r'\s*/\s*', ' vs ', pick_name)
             
             # Expand o/u
             # match word boundary, o/u, then digits. e.g. "o162.5" -> "Over 162.5"
             pick_name = re.sub(r'\bo(\d)', r'Over \1', pick_name)
             pick_name = re.sub(r'\bu(\d)', r'Under \1', pick_name)
        
        lines.append(f"| {time_part} | **{capper}** | {league} | {pick_name} | {odds} | {units} |")
        
    with open("final_picks_view.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print("Saved enriched picks to final_picks_view.md")

if __name__ == "__main__":
    main()
