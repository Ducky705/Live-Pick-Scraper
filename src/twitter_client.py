import os
import logging
import json
import datetime
import random
import asyncio
from datetime import timedelta, timezone
from twikit import Client
from config import TWITTER_USERNAME, TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_TARGET_ACCOUNTS, DATA_DIR

# File to store session cookies
COOKIES_FILE = os.path.join(DATA_DIR, 'twitter_cookies.json')

# User-Agent rotation for anti-bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
]

class TwitterManager:
    def __init__(self):
        # Select a random User-Agent
        self.ua = random.choice(USER_AGENTS)
        logging.info(f"Initializing Twitter Client with UA: {self.ua[:50]}...")
        
        self.client = Client(
            'en-US', 
            user_agent=self.ua
        )
        self.username = TWITTER_USERNAME
        self.email = TWITTER_EMAIL
        self.password = TWITTER_PASSWORD
        self.logged_in = False

    async def _wait_random(self, min_sec=2.0, max_sec=5.0):
        """Wait for a random interval to mimic human behavior."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def login(self):
        """
        Authenticate with Twitter using Twikit.
        Priority:
        1. Manual Cookies from ENV (Best for bypassing Cloudflare)
        2. Saved Cookies File
        3. User/Pass Login (Most likely to be blocked)
        """
        try:
            # 1. Check for Manual Cookies in ENV (Bypass Login Flow)
            auth_token = os.environ.get("TWITTER_AUTH_TOKEN")
            ct0 = os.environ.get("TWITTER_CT0")
            
            if auth_token and ct0:
                logging.info("Using Manual Cookies from .env (Bypassing Login)...")
                # Construct cookie dictionary
                cookies = {
                    "auth_token": auth_token,
                    "ct0": ct0
                }
                # Twikit expects dict for set_cookies (or we can use load_cookies if we format it)
                # But client.set_cookies is not directly exposed in all versions, 
                # usually we use load_cookies from a file or directly manipulate the session.
                # Twikit client has a `set_cookies` method in newer versions or we can save to file and load.
                
                # Safest approach: Write to temp cookie file and load it
                manual_cookies_path = os.path.join(DATA_DIR, 'manual_cookies.json')
                
                # Convert to standard cookie jar format or simple key-value for twikit
                # Twikit's save_cookies saves a simple dict.
                with open(manual_cookies_path, 'w') as f:
                    json.dump(cookies, f)
                
                self.client.load_cookies(manual_cookies_path)
                self.logged_in = True
                
                # Verify?
                try:
                    me = await self.client.user()
                    logging.info(f"Logged in as: {me.name}")
                except Exception as e:
                    logging.warning(f"Cookie session might be invalid, but proceeding: {e}")
                return

            # 2. Check for Saved Cookies
            if os.path.exists(COOKIES_FILE):
                logging.info(f"Loading Twitter cookies from {COOKIES_FILE}")
                self.client.load_cookies(COOKIES_FILE)
                self.logged_in = True
            else:
                # 3. Credentials Login
                logging.info("No cookies found. Logging in with credentials...")
                
                if not self.username or not self.password:
                    logging.error("Twitter credentials missing. Please check .env")
                    return

                await self._wait_random(2, 4)
                await self.client.login(
                    auth_info_1=self.username,
                    auth_info_2=self.email,
                    password=self.password
                )
                self.client.save_cookies(COOKIES_FILE)
                self.logged_in = True
                logging.info("Login successful. Cookies saved.")
        except Exception as e:
            logging.error(f"Twitter Login Failed: {e}")
            self.logged_in = False

    async def fetch_tweets(self, usernames=None, target_date=None):
        """
        Fetch tweets from target accounts for a specific date (Eastern Time).
        Defaults to yesterday if no date provided.
        """
        if not self.logged_in:
            await self.login()
            if not self.logged_in:
                logging.error("Cannot fetch tweets: Login failed.")
                return []

        if usernames is None:
            usernames = TWITTER_TARGET_ACCOUNTS

        # Set Date Range (Eastern Time)
        et_tz = timezone(timedelta(hours=-5))
        now_et = datetime.datetime.now(et_tz)
        
        if target_date:
            if isinstance(target_date, str):
                try:
                    target_date_obj = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
                except ValueError:
                    logging.error(f"Invalid date format {target_date}. Using yesterday.")
                    target_date_obj = (now_et - timedelta(days=1)).date()
            else:
                target_date_obj = target_date
        else:
            # Default to yesterday
            target_date_obj = (now_et - timedelta(days=1)).date()

        # Define bounds in ET
        start_dt = datetime.datetime.combine(target_date_obj, datetime.time.min).replace(tzinfo=et_tz)
        end_dt = datetime.datetime.combine(target_date_obj, datetime.time.max).replace(tzinfo=et_tz)

        # Buffer: Fetch tweets slightly into the future/past to ensure coverage (TZ conversions can be tricky)
        # Twikit returns tweets in reverse chronological order. We stop when we hit tweets older than start_dt.

        all_tweets = []
        
        logging.info(f"Fetching tweets for date: {target_date_obj} (ET)")

        for i, username in enumerate(usernames):
            try:
                # Add delay between users to avoid detection
                if i > 0:
                    await self._wait_random(3, 7)

                # Remove URL prefix/query if present
                clean_username = username.split('/')[-1].split('?')[0]
                
                logging.info(f"Fetching tweets for {clean_username}...")
                
                try:
                    user = await self.client.get_user_by_screen_name(clean_username)
                except Exception as e:
                    logging.warning(f"Could not find user {clean_username}: {e}")
                    continue

                # Add delay before fetching tweets
                await self._wait_random(1, 3)

                # Fetch Tweets (Tweets only, no replies)
                # count=40 is usually enough for a day unless they spam
                try:
                    tweets = await user.get_tweets('Tweets', count=40)
                except Exception as e:
                    logging.error(f"Error getting tweets for {clean_username}: {e}")
                    continue
                
                if not tweets:
                    logging.info(f"No tweets returned for {clean_username}")
                    continue

                for tweet in tweets:
                    # Convert created_at string to datetime
                    tweet_dt = None
                    if hasattr(tweet, 'created_at_datetime') and tweet.created_at_datetime:
                        tweet_dt = tweet.created_at_datetime
                    else:
                        # Parse manually
                        try:
                            tweet_dt = datetime.datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y")
                        except:
                            # Fallback or try other format
                            try:
                                # ISO format sometimes?
                                tweet_dt = datetime.datetime.fromisoformat(tweet.created_at.replace('Z', '+00:00'))
                            except:
                                logging.warning(f"Could not parse tweet date: {tweet.created_at}")
                                continue
                    
                    # Convert to ET
                    tweet_et = tweet_dt.astimezone(et_tz)
                    
                    # Filter by Date
                    if tweet_et.date() == target_date_obj:
                        # Extract Images
                        image_urls = []
                        if hasattr(tweet, 'media') and tweet.media:
                            for m in tweet.media:
                                # Safe extraction for various media types
                                url = getattr(m, 'media_url_https', None)
                                if url:
                                    image_urls.append(url)
                                elif isinstance(m, dict) and 'media_url_https' in m:
                                    image_urls.append(m['media_url_https'])

                        # Create Message Object
                        tweet_dict = {
                            'id': f"tw_{tweet.id}",
                            'channel_name': f"Twitter: {clean_username}",
                            'capper_name': clean_username,
                            'date': tweet_et.strftime("%Y-%m-%d %H:%M ET"),
                            'text': tweet.full_text if hasattr(tweet, 'full_text') else tweet.text,
                            'images': image_urls,
                            'image': image_urls[0] if image_urls else None,
                            'source': 'twitter',
                            'do_ocr': True if image_urls else False,
                            'grouped_id': None,
                            'selected': True
                        }
                        all_tweets.append(tweet_dict)
                    
                    elif tweet_et.date() < target_date_obj:
                        # We went past the target date (tweets are newest first)
                        # We can stop for this user
                        break
            
            except Exception as e:
                logging.error(f"Error processing {username}: {e}")

        return all_tweets
