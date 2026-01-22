import os
import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from twikit import Client
from config import TEMP_IMG_DIR

# Check for credentials in env
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
COOKIES_PATH = "twitter_cookies.json"

class TwitterManager:
    def __init__(self):
        self.client = None
        self.user_cache = {}

    async def get_client(self):
        if self.client is None:
            # Use a standard browser user agent to avoid detection
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            self.client = Client('en-US', user_agent=ua)
            
            # Try loading cookies first
            if os.path.exists(COOKIES_PATH):
                print(f"[Twitter] Loading cookies from {COOKIES_PATH}")
                self.client.load_cookies(COOKIES_PATH)
            else:
                print("[Twitter] No cookies found. Attempting login...")
                if not TWITTER_USERNAME or not TWITTER_PASSWORD:
                    raise ValueError("TWITTER_USERNAME and TWITTER_PASSWORD must be set in .env or environment")
                
                await self.client.login(
                    auth_info_1=TWITTER_USERNAME,
                    auth_info_2=TWITTER_EMAIL,
                    password=TWITTER_PASSWORD
                )
                self.client.save_cookies(COOKIES_PATH)
                print(f"[Twitter] Logged in and saved cookies to {COOKIES_PATH}")
        return self.client

    async def get_user_tweets(self, screen_name, count=20):
        client = await self.get_client()
        
        try:
            user = await client.get_user_by_screen_name(screen_name)
        except Exception as e:
            print(f"[Twitter] Error getting user {screen_name}: {repr(e)}")
            return []

        print(f"[Twitter] Fetching tweets for {screen_name}...")
        try:
            # Twikit get_user_tweets returns a Result object which is iterable/list-like
            tweets = await user.get_tweets('Tweets', count=count)
        except Exception as e:
             print(f"[Twitter] Error fetching tweets: {e}")
             return []

        parsed_messages = []
        ET_OFFSET = timezone(timedelta(hours=-5))

        if not os.path.exists(TEMP_IMG_DIR):
            os.makedirs(TEMP_IMG_DIR)

        for tweet in tweets:
            # Twikit tweet object structure varies, but generally has .text, .created_at, .media
            # created_at is usually a string string "Fri Dec 10 20:00:00 +0000 2021" or similar
            # Update: Twikit recent versions return structured objects.
            
            # Date Parsing
            # Typically twikit returns datetime string or object? 
            # Looking at twikit docs/examples, it's often a string.
            # We'll try to parse safely.
            
            # If tweet has media, download it
            image_paths = []
            if tweet.media:
                for med in tweet.media:
                    if med.get('type') == 'photo':
                        url = med.get('media_url_https')
                        if url:
                            fname = f"tw_{tweet.id}_{len(image_paths)}.jpg"
                            fpath = os.path.join(TEMP_IMG_DIR, fname)
                            # Download using simple request or client?
                            # For simplicity we can use standard requests or client's session?
                            # Client doesn't expose a download helper easily, but we can use requests
                            # provided we have headers if needed, but media URLs are usually public.
                            # We'll allow the main loop to download or do it here.
                            # Let's do it here nicely.
                            
                            # Actually, to be async and safe, we'll mark it for download or just use the URL
                            # The Telegram scraper downloads to a local path.
                            # Let's use the 'pending_download' pattern if we want, or just download now.
                            try:
                                # Quick sync download using requests (or aiohttp if available)
                                import requests
                                if not os.path.exists(fpath):
                                    resp = requests.get(url)
                                    if resp.status_code == 200:
                                        with open(fpath, 'wb') as f:
                                            f.write(resp.content)
                                        image_paths.append(f"/static/temp_images/{fname}")
                            except Exception as e:
                                print(f"Error downloading Twitter image: {e}")

            # Construct Message Dict
            # created_at looks like "Wed Oct 10 20:19:24 +0000 2018"
            ts = tweet.created_at
            try:
                # Common Twitter format
                dt = datetime.strptime(ts, '%a %b %d %H:%M:%S %z %Y')
            except:
                try:
                    # Alternative ISO
                     dt = datetime.fromisoformat(ts)
                except:
                    dt = datetime.now(timezone.utc) # Fallback

            dt_et = dt.astimezone(ET_OFFSET)
            
            msg_dict = {
                'id': tweet.id,
                'channel_name': f"@{screen_name}",
                'date': dt_et.strftime("%Y-%m-%d %H:%M ET"),
                'text': tweet.full_text if hasattr(tweet, 'full_text') else tweet.text,
                'images': image_paths, 
                'image': image_paths[0] if image_paths else None,
                'grouped_id': None, # Twitter threads could be grouped, but treat as single for now
                'selected': True,
                'do_ocr': True if image_paths else False
            }
            parsed_messages.append(msg_dict)
            
        return parsed_messages

    async def fetch_tweets(self, target_date=None):
        """
        Fetches tweets from ALL followed accounts for the target date.
        """
        client = await self.get_client()
        if not client: return []
        
        try:
            # 1. Get My User ID
            me = await client.user()
            my_id = me.id
            
            # 2. Get Following (limit to 20 for safety/speed)
            print(f"[Twitter] Fetching following list for {me.screen_name}...")
            following_result = await client.get_user_following(my_id, count=20)
            
            if not following_result:
                print("[Twitter] No followed accounts found.")
                return []
                
            # 3. Iterate and Fetch
            all_tweets = []
            ET_OFFSET = timezone(timedelta(hours=-5))
            
            if target_date:
                if isinstance(target_date, str):
                    target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
                else:
                    target_dt = target_date
            else:
                target_dt = (datetime.now(ET_OFFSET) - timedelta(days=1)).date()
                
            print(f"[Twitter] Scanning {len(following_result)} accounts for tweets on {target_dt}...")
            
            for user in following_result:
                # screen_name might be an attribute
                screen_name = user.screen_name
                
                # Use existing helper
                user_tweets = await self.get_user_tweets(screen_name, count=5) # 5 per user is enough for daily check
                
                # Filter by date
                for msg in user_tweets:
                    # msg['date'] is "YYYY-MM-DD HH:MM ET"
                    try:
                        msg_dt_str = msg['date'].replace(" ET", "")
                        msg_date = datetime.strptime(msg_dt_str, "%Y-%m-%d %H:%M").date()
                        
                        if msg_date == target_dt:
                            all_tweets.append(msg)
                    except Exception as e:
                        print(f"Date parse error: {e}")
                        
            return all_tweets
            
        except Exception as e:
            print(f"[Twitter] Error in fetch_tweets: {e}")
            return []

twitter_manager = TwitterManager()
