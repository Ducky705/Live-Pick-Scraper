import asyncio
import logging
import os
import requests
from datetime import datetime, timezone, timedelta

from twikit import Client
from discord.ext import commands
import discord

from src.config import TEMP_IMG_DIR, PROXY_URL
from live_runner import process_new_message

logger = logging.getLogger(__name__)

class LiveTwitterPoller:
    def __init__(self):
        self.client = None
        self.username = os.getenv("TWITTER_USERNAME")
        self.email = os.getenv("TWITTER_EMAIL")
        self.password = os.getenv("TWITTER_PASSWORD")
        self.auth_token = os.getenv("TWITTER_AUTH_TOKEN")
        self.ct0 = os.getenv("TWITTER_CT0")
        
        env_accounts = os.getenv("TWITTER_MONITORED_ACCOUNTS")
        if env_accounts:
            self.monitored_accounts = [acc.strip() for acc in env_accounts.split(",") if acc.strip()]
        else:
            self.monitored_accounts = [
                "EZMSports", "leakedcaps", "allcappersfree", 
                "Allinonecappers", "allcappersfreee", "Capperleaked", 
                "ItsCappersPicks", "ExclusiveCapper", "free_topCappers", 
                "capperspicksvip", "MrLeaked_", "allpicksarefree"
            ]
            
        self.last_seen_id = None
        
    async def get_client(self):
        if not self.client:
            self.client = Client("en-US", proxy=PROXY_URL)
            cookies_path = os.path.join(os.getcwd(), 'data', 'sessions', 'twitter_cookies.json')
            
            # Manual Cookie Injection (Bypass Cloudflare Login)
            if not os.path.exists(cookies_path) and self.auth_token and self.ct0:
                print("[Twitter] Creating cookies from .env tokens...")
                import json
                cookies = {"auth_token": self.auth_token, "ct0": self.ct0}
                os.makedirs(os.path.dirname(cookies_path), exist_ok=True)
                with open(cookies_path, "w") as f:
                    json.dump(cookies, f)
                    
            if os.path.exists(cookies_path):
                self.client.load_cookies(cookies_path)
            else:
                await self.client.login(
                    auth_info_1=self.username,
                    auth_info_2=self.email,
                    password=self.password,
                )
                self.client.save_cookies(cookies_path)
        return self.client

    async def poll_loop(self):
        """Infinite polling loop for Twitter."""
        print(f"✓ Twitter Poller initialized for {len(self.monitored_accounts)} accounts")
        client = await self.get_client()
        
        while True:
            try:
                # Chunk users
                CHUNK_SIZE = 10
                chunks = [self.monitored_accounts[i:i + CHUNK_SIZE] for i in range(0, len(self.monitored_accounts), CHUNK_SIZE)]
                
                new_max_id = self.last_seen_id
                
                for chunk in chunks:
                    from_clause = " OR ".join([f"from:{acc}" for acc in chunk])
                    query = f"({from_clause})"
                    
                    try:
                        results = await client.search_tweet(query, product="Latest", count=10)
                        
                        for tweet in results:
                            # Use tweet.id to deduplicate. If we haven't set a high water mark yet or it's new
                            tweet_id_int = int(tweet.id)
                            if self.last_seen_id is None or tweet_id_int > int(self.last_seen_id):
                                if new_max_id is None or tweet_id_int > int(new_max_id):
                                    new_max_id = str(tweet_id_int)
                                
                                # Process it!
                                await self.emit_tweet(tweet)
                                
                    except Exception as e:
                        if "429" in str(e):
                            logger.warning("Twitter Rate Limit. Backing off.")
                            await asyncio.sleep(60)
                            
                    await asyncio.sleep(5) # Jitter between chunks
                    
                self.last_seen_id = new_max_id
                
            except Exception as e:
                logger.error(f"Twitter polling error: {e}")
                
            await asyncio.sleep(900) # Poll every 15 minutes

    async def emit_tweet(self, tweet):
        """Morphs a twikit tweet into a Telegram FakeEvent to feed into the live runner."""
        image_paths = []
        if tweet.media:
            for med in tweet.media:
                m_type = getattr(med, 'type', None) or (med.get('type') if isinstance(med, dict) else None)
                m_url = getattr(med, 'media_url_https', None) or (med.get('media_url_https') if hasattr(med, 'get') else None)
                
                if m_type == "photo" and m_url:
                    os.makedirs(TEMP_IMG_DIR, exist_ok=True)
                    fpath = os.path.join(TEMP_IMG_DIR, f"tw_{tweet.id}_{len(image_paths)}.jpg")
                    try:
                        resp = requests.get(m_url)
                        if resp.status_code == 200:
                            with open(fpath, "wb") as f:
                                f.write(resp.content)
                            image_paths.append(fpath)
                    except Exception as e:
                        logger.error(f"Error downloading Twitter image: {e}")

        class FakeMessage:
            def __init__(self):
                self.id = tweet.id
                # Twikit formats it as 'Mon Feb 23 10:20:00 +0000 2024'
                try:
                    self.date = datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y")
                except:
                    self.date = datetime.now(timezone.utc)
                self.text = tweet.full_text if hasattr(tweet, "full_text") else tweet.text
                self.media = image_paths if image_paths else None
        
        class FakeChat:
            def __init__(self):
                self.title = f"@{tweet.user.screen_name}"
                
        class FakeEvent:
            def __init__(self):
                # Hash as a negative channel id to slip past telegram restrictions
                self.chat_id = -abs(hash(tweet.user.screen_name) % (10 ** 8))
                self.message = FakeMessage()
                
            async def get_chat(self):
                return FakeChat()

        # Execute existing pipeline
        await process_new_message(None, FakeEvent(), source_type="twitter", custom_url=f"https://x.com/{tweet.user.screen_name}/status/{tweet.id}")

def setup_discord_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    target_ids = os.getenv("DISCORD_CHANNEL_IDS", "")
    target_ids = [int(i.strip()) for i in target_ids.split(",") if i.strip()]

    @bot.event
    async def on_ready():
        print(f"✓ Discord Bot Listener initialized and logged in as {bot.user}")

    @bot.event
    async def on_message(message):
        if message.channel.id not in target_ids:
            return
            
        if message.author == bot.user:
            return
            
        image_paths = []
        for att in message.attachments:
            if "image" in att.content_type:
                os.makedirs(TEMP_IMG_DIR, exist_ok=True)
                fpath = os.path.join(TEMP_IMG_DIR, f"dc_{message.id}_{att.id}.jpg")
                await att.save(fpath)
                image_paths.append(fpath)

        class FakeMessage:
            def __init__(self):
                self.id = message.id
                self.date = message.created_at
                self.text = message.content
                self.media = image_paths if image_paths else None
                
        class FakeChat:
            def __init__(self):
                try:
                    self.title = f"#{message.channel.name} ({message.guild.name})"
                except:
                    self.title = f"Discord_{message.channel.id}"
                    
        class FakeEvent:
            def __init__(self):
                self.chat_id = message.channel.id
                self.message = FakeMessage()
                
            async def get_chat(self):
                return FakeChat()

        custom_url = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}" if getattr(message, 'guild', None) else ""
        await process_new_message(None, FakeEvent(), source_type="discord", custom_url=custom_url)

    return bot
