import json
import random
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CreateV4Dataset")

FRESH_FILE = "data/cache/fresh_benchmark_raw_final.json"
CACHE_FILE = "data/cache/messages.json"
OUTPUT_FILE = "benchmark/dataset/golden_set_v4_candidates.json"

def main():
    final_set = []
    seen_ids = set()
    counts = {"telegram": 0, "twitter": 0, "discord": 0}

    # 1. Load Fresh Data (Twitter, Discord, Telegram)
    if os.path.exists(FRESH_FILE):
        with open(FRESH_FILE, "r") as f:
            fresh_data = json.load(f)
            logger.info(f"Loaded {len(fresh_data)} fresh items.")
            
            # Prioritize fresh items
            for item in fresh_data:
                # infer source
                # Twitter items have 'source'="twitter" already.
                src = item.get("source", "unknown").lower()
                
                if src == "unknown":
                    # Heuristics
                    if "t.co" in item.get("text", ""):
                        src = "twitter"
                    elif item.get("grouped_id") is not None:
                        src = "telegram"
                        
                if src in counts and counts[src] < 50:
                    mid = str(item.get("id"))
                    if mid not in seen_ids:
                        if (item.get("text") and len(item["text"]) > 5) or item.get("images"):
                            item["source"] = src
                            final_set.append(item)
                            counts[src] += 1
                            seen_ids.add(mid)

    # 2. Backfill from Cache (Telegram/Discord)
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)
            messages = cache_data.get("messages", [])
            logger.info(f"Loaded {len(messages)} cached items.")
            
            # Shuffle to get random distribution or take latest? 
            # Cache is usually sorted new->old or old->new. 
            # We want "fresh" but if we can't scrape, we take what we have.
            # Let's take from the TOP (usually newest)
            
            # Filter by source
            # Inspect channel_name or source field?
            # In snippet: "channel_name": "Telegram", "source" is missing?
            # Let's check for 'source' key or infer from channel_name
            
            for m in messages:
                # Infer source
                src = m.get("source", "").lower()
                if not src:
                    cname = m.get("channel_name", "").lower()
                    if "telegram" in cname:
                        src = "telegram"
                    elif "discord" in cname:
                        src = "discord"
                    elif "@" in cname: # Twitter often has @
                        src = "twitter"
                
                if src in counts and counts[src] < 50:
                    mid = str(m.get("id"))
                    if mid not in seen_ids:
                         # Ensure quality
                        if (m.get("text") and len(m["text"]) > 10) or m.get("images"):
                            # Normalize structure
                            m["source"] = src
                            final_set.append(m)
                            counts[src] += 1
                            seen_ids.add(mid)

    # Summary
    logger.info("Final Counts:")
    for k, v in counts.items():
        logger.info(f"  {k}: {v}")
        
    # Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_set, f, indent=2)
        
    logger.info(f"Saved {len(final_set)} candidates to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
