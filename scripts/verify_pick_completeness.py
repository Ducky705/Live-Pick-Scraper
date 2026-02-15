import json
import os

def main():
    tweets_file = "debug_raw_tweets.json"
    picks_file = "twitter_picks.json"
    
    if not os.path.exists(tweets_file) or not os.path.exists(picks_file):
        print("Missing files.")
        return

    with open(tweets_file, "r", encoding="utf-8") as f:
        tweets = json.load(f)
        
    with open(picks_file, "r", encoding="utf-8") as f:
        picks_data = json.load(f)
        picks = picks_data.get("picks", [])
        
    # Map tweet ID to picks
    picks_by_id = {}
    for p in picks:
        # Support both 'i' and 'message_id'
        pid = str(p.get("i") or p.get("message_id"))
        if pid not in picks_by_id:
            picks_by_id[pid] = []
        picks_by_id[pid].append(p)
        
    print(f"Total Tweets: {len(tweets)}")
    print(f"Total Picks: {len(picks)}")
    
    missing_count = 0
    
    for tweet in tweets:
        tid = str(tweet["id"])
        tweet_picks = picks_by_id.get(tid, [])
        
        # Clean newlines for display
        text_preview = tweet["text"].replace("\n", " ")[:100]
        
        if not tweet_picks:
            print(f"\n[FAIL] Tweet {tid} has NO picks extracted:")
            print(f"Text: {tweet['text']}")
            missing_count += 1
        else:
            # print(f"\n[OK] Tweet {tid} - {len(tweet_picks)} picks")
            # print(f"Text: {text_preview}...")
            # for p in tweet_picks:
            #     print(f" -> {p.get('pick')} ({p.get('odds')}, {p.get('units')}u)")
            pass
            
    print("-" * 30)
    if missing_count == 0:
        print("SUCCESS: All tweets have at least one extracted pick!")
    else:
        print(f"WARNING: {missing_count} tweets yielded 0 picks.")

if __name__ == "__main__":
    main()
