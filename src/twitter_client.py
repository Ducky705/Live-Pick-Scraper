import asyncio
import os
import random
from datetime import UTC, datetime, timedelta, timezone

from twikit import Client

from config import PROXY_URL, SESSIONS_DIR, TEMP_IMG_DIR, USER_AGENTS

# Check for credentials in env
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
TWITTER_AUTH_TOKEN = os.getenv("TWITTER_AUTH_TOKEN")
TWITTER_CT0 = os.getenv("TWITTER_CT0")
COOKIES_PATH = os.path.join(SESSIONS_DIR, "twitter_cookies.json")


class TwitterManager:
    def __init__(self):
        self.client = None
        self.user_cache = {}

    async def get_client(self):
        if self.client is None:
            # Use a random user agent to avoid detection
            ua = random.choice(USER_AGENTS)

            # Twikit supports proxy string usage
            print(f"[Twitter] Initializing Client. Proxy: {bool(PROXY_URL)}")
            self.client = Client("en-US", user_agent=ua, proxy=PROXY_URL)

            # Manual Cookie Injection (Bypass Cloudflare Login)
            if not os.path.exists(COOKIES_PATH) and TWITTER_AUTH_TOKEN and TWITTER_CT0:
                print("[Twitter] Creating cookies from .env tokens...")
                import json
                cookies = {
                    "auth_token": TWITTER_AUTH_TOKEN,
                    "ct0": TWITTER_CT0
                }
                # Ensure dir exists
                os.makedirs(os.path.dirname(COOKIES_PATH), exist_ok=True)
                with open(COOKIES_PATH, "w") as f:
                    json.dump(cookies, f)

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
                    password=TWITTER_PASSWORD,
                )
                self.client.save_cookies(COOKIES_PATH)
                print(f"[Twitter] Logged in and saved cookies to {COOKIES_PATH}")
        return self.client

    async def get_user_tweets(self, screen_name, limit=100, min_date_str=None):
        """
        Fetch tweets for a user, handling pagination until limit is reached or dates go past min_date_str.
        min_date_str: "YYYY-MM-DD"
        """
        client = await self.get_client()

        user = None
        # Add retry logic for user fetch with Exponential Backoff
        for attempt in range(5):
            try:
                user = await client.get_user_by_screen_name(screen_name)
                break
            except Exception as e:
                if "User is suspended" in str(e) or "user does not exist" in str(e).lower():
                    print(f"[Twitter] User {screen_name} is unavailable: {e}")
                    return []

                # Check for Rate Limit
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait_time = 60 * (2**attempt)
                    print(f"[Twitter] Rate Limit fetching user {screen_name}. Sleeping {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                print(f"[Twitter] Error getting user {screen_name} (Attempt {attempt + 1}/5): {e!r}")
                await asyncio.sleep(5)  # Standard short retry

        if not user:
            return []

        print(f"[Twitter] Fetching tweets for {screen_name}...")

        collected_tweets = []

        try:
            # Twikit get_user_tweets returns a Result object which is iterable/list-like
            # We use a batch size of 40 (often standard page size)
            tweets = await user.get_tweets("Tweets", count=40)
            if not tweets:
                return []

            collected_tweets.extend(tweets)
            print(f"[Twitter] Batch 1 count: {len(tweets)}")

            # Pagination Loop
            page = 1
            while len(collected_tweets) < limit:
                # Check date condition if provided
                if min_date_str:
                    try:
                        last_tweet = collected_tweets[-1]
                        ts = last_tweet.created_at
                        # Parse date to check if we went far enough back
                        # Format: "Fri Dec 10 20:00:00 +0000 2021"
                        dt = datetime.strptime(ts, "%a %b %d %H:%M:%S %z %Y")

                        target_dt = datetime.strptime(min_date_str, "%Y-%m-%d").date()
                        if dt.date() < target_dt:
                            # We found tweets older than target, so we have enough
                            print(f"[Twitter] Reached older tweets ({dt.date()} < {target_dt}). Stopping.")
                            break
                    except Exception:
                        # If parsing fails, just continue fetching to be safe
                        pass

                # Fetch next page with Retry Logic
                retry_count = 0
                max_retries = 3

                while retry_count < max_retries:
                    try:
                        # Randomized Jitter (2-5s) to look more human
                        await asyncio.sleep(random.uniform(2.0, 5.0))

                        more_tweets = await tweets.next()
                        if not more_tweets:
                            print("[Twitter] No more tweets available.")
                            # Break out of RETRY loop and PAGINATION loop
                            retry_count = 999  # Signal to break outer
                            break

                        collected_tweets.extend(more_tweets)
                        print(f"[Twitter] Batch {page + 1} count: {len(more_tweets)} (Total: {len(collected_tweets)})")
                        tweets = more_tweets  # Update reference for next()
                        page += 1
                        break  # Success, exit retry loop

                    except Exception as e:
                        # Handle Rate Limits (429) specifically
                        if "429" in str(e) or "Too Many Requests" in str(e):
                            retry_count += 1
                            wait_time = 60 * (2 ** (retry_count - 1))  # Exponential Backoff: 60s, 120s, 240s
                            print(
                                f"[Twitter] Rate Limit Hit on page {page + 1}. Attempt {retry_count}/{max_retries}. Sleeping {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            continue  # Retry

                        print(f"[Twitter] Pagination error on page {page + 1}: {e}")
                        retry_count = 999  # Fatal error, stop
                        break

                if retry_count == 999:
                    break  # Break outer pagination loop

        except Exception as e:
            print(f"[Twitter] Error fetching tweets: {e}")
            return []

        parsed_messages = []
        ET_OFFSET = timezone(timedelta(hours=-5))

        if not os.path.exists(TEMP_IMG_DIR):
            os.makedirs(TEMP_IMG_DIR)

        for tweet in collected_tweets:
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
                    # Handle both dict and object access
                    if isinstance(med, dict):
                        m_type = med.get("type")
                        m_url = med.get("media_url_https")
                    else:
                        m_type = getattr(med, "type", None)
                        m_url = getattr(med, "media_url_https", None)

                    if m_type == "photo" and m_url:
                        url = m_url
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
                                        with open(fpath, "wb") as f:
                                            f.write(resp.content)
                                        image_paths.append(f"/static/temp_images/{fname}")
                            except Exception as e:
                                print(f"Error downloading Twitter image: {e}")

            # Construct Message Dict
            # created_at looks like "Wed Oct 10 20:19:24 +0000 2018"
            ts = tweet.created_at
            try:
                # Common Twitter format
                dt = datetime.strptime(ts, "%a %b %d %H:%M:%S %z %Y")
            except:
                try:
                    # Alternative ISO
                    dt = datetime.fromisoformat(ts)
                except:
                    dt = datetime.now(UTC)  # Fallback

            dt_et = dt.astimezone(ET_OFFSET)

            msg_dict = {
                "id": tweet.id,
                "channel_name": f"@{screen_name}",
                "date": dt_et.strftime("%Y-%m-%d %H:%M ET"),
                "text": tweet.full_text if hasattr(tweet, "full_text") else tweet.text,
                "images": image_paths,
                "image": image_paths[0] if image_paths else None,
                "grouped_id": None,  # Twitter threads could be grouped, but treat as single for now
                "selected": True,
                "do_ocr": True if image_paths else False,
            }
            parsed_messages.append(msg_dict)

        return parsed_messages

    async def fetch_tweets(self, target_date=None, limit=100):
        """
        Fetch tweets from monitored accounts matching the target date using optimized SEARCH queries.
        This reduces API calls by grouping users and only fetching new content.
        """
        # Load monitored accounts from .env or default to list
        env_accounts = os.getenv("TWITTER_MONITORED_ACCOUNTS")
        if env_accounts:
            MONITORED_ACCOUNTS = [acc.strip() for acc in env_accounts.split(",") if acc.strip()]
        else:
            # Fallback Default List
            MONITORED_ACCOUNTS = [
                "EZMSports",
                "leakedcaps",
                "allcappersfree",
                "Allinonecappers",
                "allcappersfreee",
                "Capperleaked",
                "ItsCappersPicks",
                "ExclusiveCapper",
                "free_topCappers",
                "capperspicksvip",
                "MrLeaked_",
                "allpicksarefree",
            ]

        if not target_date or target_date == "ALL":
            # If no date, fallback to old method (user timeline) or default to today?
            # For efficiency, let's default to today if not provided, or handle differently.
            # But the system usually provides a date.
            target_date = datetime.now().strftime("%Y-%m-%d")

        print(f"[Twitter] Optimized Search Mode. Target Date: {target_date}")

        client = await self.get_client()
        all_tweets = []

        # Chunk users into groups of 10 to keep query length reasonable
        # (Twitter queries have char limits, but 10 usernames is usually safe)
        CHUNK_SIZE = 10
        chunks = [MONITORED_ACCOUNTS[i : i + CHUNK_SIZE] for i in range(0, len(MONITORED_ACCOUNTS), CHUNK_SIZE)]

        for i, chunk in enumerate(chunks):
            try:
                # Construct Query: (from:user1 OR from:user2) since:2025-01-24
                from_clause = " OR ".join([f"from:{acc}" for acc in chunk])
                query = f"({from_clause}) since:{target_date}"

                print(f"[Twitter] Executing Batch {i + 1}/{len(chunks)}: {query[:50]}...")

                # Fetch with pagination (Search also supports pagination)
                # We use 'Latest' to get chronological order
                collected_batch = []

                # Search loop
                try:
                    results = await client.search_tweet(query, product="Latest", count=40)

                    while results:
                        collected_batch.extend(results)
                        print(f"  - Found {len(results)} tweets in page. Total batch: {len(collected_batch)}")

                        # Jitter
                        await asyncio.sleep(random.uniform(2.0, 4.0))

                        # Next page
                        results = await results.next()

                except Exception as e:
                    if "429" in str(e):
                        print("[Twitter] Rate limit during search. Sleeping 60s...")
                        await asyncio.sleep(60)
                    else:
                        print(f"[Twitter] Search error: {e}")

                # Process Tweets
                # Reuse the parsing logic. We need to normalize tweet objects.
                # Search results are Tweet objects similar to user timeline.
                for tweet in collected_batch:
                    # Parse and add to all_tweets
                    parsed = self._parse_tweet(tweet)
                    all_tweets.append(parsed)

                # Sleep between batches
                await asyncio.sleep(random.uniform(5.0, 8.0))

            except Exception as e:
                print(f"[Twitter] Failed to process batch {chunk}: {e}")

        return all_tweets

    def _parse_tweet(self, tweet):
        """Helper to parse a Twikit tweet object into our dict format"""
        ET_OFFSET = timezone(timedelta(hours=-5))

        # Image Handling
        image_paths = []
        if tweet.media:
            for med in tweet.media:
                if isinstance(med, dict):
                    m_type = med.get("type")
                    m_url = med.get("media_url_https")
                else:
                    m_type = getattr(med, "type", None)
                    m_url = getattr(med, "media_url_https", None)

                if m_type == "photo" and m_url:
                    if not os.path.exists(TEMP_IMG_DIR):
                        os.makedirs(TEMP_IMG_DIR)

                    fname = f"tw_{tweet.id}_{len(image_paths)}.jpg"
                    fpath = os.path.join(TEMP_IMG_DIR, fname)

                    # Deduplicate/Cache check could go here
                    # For now, simplistic download logic
                    try:
                        import requests

                        if not os.path.exists(fpath):
                            resp = requests.get(m_url)
                            if resp.status_code == 200:
                                with open(fpath, "wb") as f:
                                    f.write(resp.content)
                                image_paths.append(fpath)
                        else:
                            image_paths.append(fpath)
                    except Exception as e:
                        print(f"[Twitter] Image download error: {e}")

        # Date Parsing
        ts = tweet.created_at
        try:
            # Try common formats. Search might return different formats sometimes?
            # Usually "Fri Dec 10 20:00:00 +0000 2021"
            dt = datetime.strptime(ts, "%a %b %d %H:%M:%S %z %Y")
        except:
            try:
                dt = datetime.fromisoformat(ts)
            except:
                dt = datetime.now(UTC)

        dt_et = dt.astimezone(ET_OFFSET)

        return {
            "id": tweet.id,
            "channel_name": f"@{tweet.user.screen_name}",
            "date": dt_et.strftime("%Y-%m-%d %H:%M ET"),
            "text": tweet.full_text if hasattr(tweet, "full_text") else tweet.text,
            "images": image_paths,
            "image": image_paths[0] if image_paths else None,
            "grouped_id": None,
            "selected": True,
            "do_ocr": True if image_paths else False,
        }


twitter_manager = TwitterManager()
