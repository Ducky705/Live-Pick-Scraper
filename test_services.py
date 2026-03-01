import os
import asyncio
import discord
from twikit import Client
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

async def test_discord():
    print("\n--- Testing Discord ---")
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("No DISCORD_TOKEN found in .env")
        return
        
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"✅ Discord Success! Logged in as {client.user}")
        await client.close()
        
    try:
        print("Attempting to connect to Discord...")
        await client.start(token)
    except Exception as e:
        print(f"❌ Discord Error: {e}")

async def test_twitter():
    print("\n--- Testing Twitter ---")
    username = os.getenv("TWITTER_USERNAME")
    email = os.getenv("TWITTER_EMAIL")
    password = os.getenv("TWITTER_PASSWORD")
    auth_token = os.getenv("TWITTER_AUTH_TOKEN")
    ct0 = os.getenv("TWITTER_CT0")

    client = Client("en-US")
    cookies_path = "twitter_cookies_test.json"
    
    if auth_token and ct0:
        import json
        with open(cookies_path, "w") as f:
            json.dump({"auth_token": auth_token, "ct0": ct0}, f)
        
    try:
        if os.path.exists(cookies_path):
            print("Loading cookies...")
            client.load_cookies(cookies_path)
            
        print("Testing query...")
        results = await client.search_tweet("from:leakedcaps", product="Latest", count=2)
        print(f"✅ Twitter Success! Found {len(results)} tweets.")
        for t in results:
            print(f" - {t.user.screen_name}: {t.text[:50]}...")
            
    except Exception as e:
        print(f"❌ Twitter Error: {e}")

async def main():
    await test_discord()
    await test_twitter()

if __name__ == "__main__":
    asyncio.run(main())
