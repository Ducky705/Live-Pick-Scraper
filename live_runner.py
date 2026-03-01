"""
CapperSuite CLI - Live Pick Listener
A 24/7 event-driven Telegram listener that streams picks to Supabase.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto

# Load configuration
load_dotenv()

# Ensure src is in path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

from src.config import API_ID, API_HASH, TARGET_TELEGRAM_CHANNEL_ID, SESSION_FILE_PATH, TEMP_IMG_DIR
from src.live_supabase import LiveSupabaseClient
from src.live_pipeline import process_live_message

# Setup Logging
log_file = os.path.join(root_dir, "data", "logs", "live_runner.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

async def process_new_message(client, event, source_type="tg", custom_url=""):
    """
    Core event handler for new Telegram/Discord/Twitter messages.
    """
    message = event.message
    channel_id = getattr(event, 'chat_id', getattr(event, 'channel_id', getattr(message, 'chat_id', 'unknown')))
    message_id = message.id
    
    # Get standard names
    try:
        chat = await event.get_chat()
        channel_name = getattr(chat, 'title', f"{source_type}_{channel_id}")
    except Exception:
        channel_name = f"{source_type}_{channel_id}"
        
    if custom_url:
        source_url = custom_url
    else:
        source_url = f"https://t.me/c/{str(abs(channel_id))[4:]}/{message_id}" if str(channel_id).startswith("-100") else ""
        
    source_unique_id = f"{source_type}_{channel_id}_{message_id}"
    
    # Timestamp formatting (ET approx)
    ET_OFFSET = timezone(timedelta(hours=-5))
    msg_date_str = ""
    if message.date:
        msg_date_str = message.date.astimezone(ET_OFFSET).strftime("%Y-%m-%d")
    else:
        msg_date_str = datetime.now(ET_OFFSET).strftime("%Y-%m-%d")
        
    raw_text = message.text or ""
    
    logger.info(f"[{channel_name}] New message id={message_id}")
    
    # 1. Save to live_raw_picks
    is_dry_run = "--dry-run" in sys.argv
    if is_dry_run:
        logger.info(f"[DRY-RUN] Would insert raw pick for {channel_name}")
        raw_id = -1
    else:
        raw_data = {
            "capper_name": channel_name,
            "raw_text": raw_text[:5000],  # Cap length for safety
            "pick_date": msg_date_str,
            "source_url": source_url,
            "source_unique_id": source_unique_id,
            "status": "pending",
            "process_attempts": 0
        }
        raw_id = LiveSupabaseClient.insert_raw_pick(raw_data)
        if not raw_id:
            logger.info(f"[{channel_name}] Skipped: Duplicate or DB error ({source_unique_id})")
            return
        
    # 2. Download Image if exists
    image_paths = []
    
    # If it's a telegram native message
    if source_type == "tg" and message.media and getattr(message.media, "photo", None):
        filename = f"live_{channel_id}_{message_id}.jpg"
        filepath = os.path.join(TEMP_IMG_DIR, filename)
        logger.info(f"[{channel_name}] Downloading image to {filepath}...")
        try:
            await client.download_media(message, filepath)
            if os.path.exists(filepath):
                image_paths.append(filepath)
        except Exception as e:
            logger.error(f"[{channel_name}] Failed to download image: {e}")
    # If it's discord or twitter that pass pre-downloaded images
    elif hasattr(message, "media") and isinstance(message.media, list):
        image_paths = message.media
            
    # 3. AI Extraction
    logger.info(f"[{channel_name}] Sending to AI for classification/extraction...")
    classification, picks = process_live_message(
        message_text=raw_text,
        image_paths=image_paths,
        channel_name=channel_name,
        source_url=source_url,
        source_unique_id=source_unique_id,
        pick_date=msg_date_str
    )
    
    # 4. Save results
    if classification == "PICK" and picks:
        logger.info(f"[{channel_name}] AI extracted {len(picks)} picks.")
        if is_dry_run:
            print("\n[DRY-RUN] EXTACTED PICKS:")
            for p in picks:
                print(f"  - {p['pick_value']} ({p['odds_american']} / {p['unit']}U)")
            print("")
        else:
            success = LiveSupabaseClient.insert_structured_picks(picks)
            if success:
                LiveSupabaseClient.update_raw_pick_status(raw_id, "processed")
            else:
                LiveSupabaseClient.update_raw_pick_status(raw_id, "error")
    else:
        logger.info(f"[{channel_name}] Classified as {classification}. No picks saved.")
        if not is_dry_run:
            LiveSupabaseClient.update_raw_pick_status(raw_id, f"not_a_pick_{classification}")
        
    # 5. Cleanup image to save disk space
    for path in image_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Failed to cleanup {path}: {e}")
            
    # 6. Update Checkpoint
    if not is_dry_run:
        now_iso = datetime.now(timezone.utc).isoformat()
        LiveSupabaseClient.update_checkpoint(channel_id, now_iso)

async def catch_up_missed_messages(client, channel_ids):
    """
    On startup, query standard channels for any messages missed while off.
    Checks the DB checkpoint to see how far back to look.
    """
    logger.info("Starting Catch-Up routine...")
    for cid in channel_ids:
        try:
            cp = LiveSupabaseClient.get_checkpoint(cid)
            if not cp:
                logger.info(f"No checkpoint for {cid}, skipping catch-up.")
                continue
                
            # Parse CP
            try:
                cp_dt = datetime.fromisoformat(cp.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid checkpoint format for {cid}: {cp}")
                continue
                
            # If checkpoint is super old, cap it to 1 day so we don't process thousands
            if datetime.now(timezone.utc) - cp_dt > timedelta(days=1):
                logger.info(f"Checkpoint for {cid} is > 1 day old. Capping to 1 day.")
                cp_dt = datetime.now(timezone.utc) - timedelta(days=1)

            entity = await client.get_entity(cid)
            channel_name = getattr(entity, 'title', str(cid))
            
            # Fetch messages newer than checkpoint
            logger.info(f"Fetching catch-up messages for {channel_name} since {cp_dt}...")
            count = 0
            # Reverse order so we process oldest to newest
            messages = []
            async for msg in client.iter_messages(entity, offset_date=cp_dt, reverse=True):
                if not msg.date: continue
                # Minor buffer just in case
                if msg.date > cp_dt: 
                    messages.append(msg)
                    
            for msg in messages:
                # Wrap it in a fake event object that conforms to our handler
                class FakeEvent:
                    message = msg
                    chat_id = cid
                    async def get_chat(self): return entity
                    
                await process_new_message(client, FakeEvent())
                count += 1
                # Throttle slightly to not hammer the AI
                await asyncio.sleep(2)
                
            logger.info(f"Finished catch-up for {channel_name}: processed {count} messages.")
            
        except Exception as e:
            logger.error(f"Catch-up failed for channel {cid}: {e}")

async def main():
    print("=" * 60)
    print("   CAPPER SUITE LIVE PICK LISTENER   ")
    print("=" * 60)

    if not API_ID or not API_HASH:
        logger.error("API_ID or API_HASH missing in environment.")
        return

    # Parse target channels
    if not TARGET_TELEGRAM_CHANNEL_ID:
        logger.error("TARGET_TELEGRAM_CHANNEL_ID is empty. Nothing to listen to.")
        return
        
    try:
        target_ids = [int(cid.strip()) for cid in TARGET_TELEGRAM_CHANNEL_ID.split(",") if cid.strip()]
    except ValueError as e:
        logger.error(f"Failed to parse channel IDs. Ensure they are integers: {e}")
        return

    # Handle proxy
    proxy_config = None
    from src.config import PROXY_URL
    if PROXY_URL:
        from urllib.parse import urlparse
        import python_socks
        try:
            parsed = urlparse(PROXY_URL)
            scheme = python_socks.PROXY_TYPE_HTTP
            if "socks5" in parsed.scheme:
                scheme = python_socks.PROXY_TYPE_SOCKS5
            elif "socks4" in parsed.scheme:
                scheme = python_socks.PROXY_TYPE_SOCKS4

            proxy_config = {
                'proxy_type': scheme,
                'addr': parsed.hostname,
                'port': parsed.port,
                'username': parsed.username,
                'password': parsed.password,
                'rdns': True
            }
            logger.info("Using Proxy Configuration.")
        except Exception as e:
            logger.warning(f"Failed to parse PROXY_URL: {e}")

    # Init Telethon
    client = TelegramClient(
        SESSION_FILE_PATH,
        int(API_ID),
        API_HASH,
        device_model="Live Scraper v1",
        system_version="Linux",
        app_version="1.0.0",
        proxy=proxy_config
    )
    
    logger.info("Connecting to Telegram...")
    await client.connect()
    
    if not await client.is_user_authorized():
        # Requires manual setup first via cli_tool.py or direct login script
        logger.error("Client is not authorized. Please run interactive login first.")
        print("\nFATAL: Telegram session is not authorized.")
        print("Please run `python cli_tool.py` once to authenticate interactively.")
        await client.disconnect()
        return

    logger.info("Client Authorized. Connected successfully.")
    print("✓ Telegram Connected")
    print(f"✓ Monitoring {len(target_ids)} channels")

    # Optional: Catch up
    if "--no-catchup" not in sys.argv:
        await catch_up_missed_messages(client, target_ids)

    # Register New Message Handler
    @client.on(events.NewMessage(chats=target_ids))
    async def handler(event):
        try:
            await process_new_message(client, event)
        except Exception as e:
            logger.error(f"Error in message handler: {e}")

    logger.info("Now listening for new messages 24/7...")
    print("\n[READY] Listening for new messages...")
    
    # Launch Discord and Twitter loops in parallel with Telegram
    from src.live_extensions import LiveTwitterPoller, setup_discord_bot
    
    tasks = [client.run_until_disconnected()]
    
    if os.getenv("TWITTER_USERNAME") and os.getenv("TWITTER_PASSWORD"):
        tw_poller = LiveTwitterPoller()
        tasks.append(asyncio.create_task(tw_poller.poll_loop()))
        
    if os.getenv("DISCORD_TOKEN"):
        bot = setup_discord_bot()
        # Ensure we wrap the discord run carefully
        async def discord_runner():
            await bot.start(os.getenv("DISCORD_TOKEN"))
        tasks.append(asyncio.create_task(discord_runner()))
        
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nListener stopped by user.")
        logger.info("Listener stopped by user.")
