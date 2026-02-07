# src/telegram_client.py
import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.tl.types import MessageMediaPhoto

from config import API_HASH, API_ID, SESSION_FILE_PATH, TEMP_IMG_DIR, PROXY_URL


class TelegramManager:
    def __init__(self):
        self.client = None  # Lazy init
        self.phone = None
        self.phone = None
        self.phone_code_hash = None
        self.progress_callback = None

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    async def _report_progress(self, percent, status):
        if self.progress_callback:
            # Run in executor if callback is synchronous or just call if async?
            # Assuming callback is simple sync function or we run it safely.
            # Since this is async method, we can just call it.
            # But the callback in main.py will likely update a global dict.
            try:
                self.progress_callback(percent, status)
            except Exception as e:
                logger.error(f"Progress Error: {e}")

    async def get_client(self):
        """
        Ensures the client is initialized on the CURRENT event loop (Background Thread).
        """
        if self.client is None:
            logger.debug(f"[DEBUG] Initializing Telegram Client on Loop: {id(asyncio.get_running_loop())}")
            logger.debug(f"[DEBUG] Session Path: {SESSION_FILE_PATH}")

            # Force integer ID
            try:
                real_api_id = int(API_ID)
            except:
                real_api_id = API_ID

            # PROXY CONFIGURATION
            proxy_config = None
            if PROXY_URL:
                try:
                    # Parse Proxy URL: http://user:pass@host:port or http://host:port
                    # Telethon expects tuple/dict: (python_socks.PROXY_TYPE_HTTP, '1.1.1.1', 8080, True, 'user', 'pass')
                    # We'll use a simple dict format if possible or manual parsing
                    from urllib.parse import urlparse
                    import python_socks

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
                    logger.info(f"Using Proxy: {parsed.scheme}://****@{parsed.hostname}:{parsed.port}")
                except Exception as e:
                    logger.error(f"Failed to parse PROXY_URL: {e}")

            # Create client attached to the CURRENT running loop
            # STEALTH MODE: Mimic iPhone 15 Pro
            self.client = TelegramClient(
                SESSION_FILE_PATH,
                real_api_id,
                API_HASH,
                loop=asyncio.get_running_loop(),
                device_model="iPhone 15 Pro",
                system_version="17.5.1",
                app_version="10.12.0",
                lang_code="en",
                system_lang_code="en-US",
                proxy=proxy_config
            )
            await self.client.connect()

        if not self.client.is_connected():
            await self.client.connect()

        return self.client

    async def connect_client(self):
        try:
            client = await self.get_client()
            authorized = await client.is_user_authorized()
            logger.debug(f"[DEBUG] Authorized: {authorized}")
            return authorized
        except Exception as e:
            logger.error(f"[ERROR] Connect Error: {e}")
            return False

    async def send_code(self, phone):
        self.phone = phone
        try:
            client = await self.get_client()
            logger.debug(f"[DEBUG] Sending code to {phone}...")

            sent = await client.send_code_request(phone)
            self.phone_code_hash = sent.phone_code_hash

            logger.debug("[DEBUG] Code sent successfully.")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Send Code Failed: {e}")
            # Reset client on major error to force reconnect
            if "database is locked" in str(e) or "auth key" in str(e).lower():
                if self.client:
                    await self.client.disconnect()
                self.client = None
            raise e

    async def sign_in(self, code, password=None):
        try:
            client = await self.get_client()
            await client.sign_in(self.phone, code, phone_code_hash=self.phone_code_hash)
        except SessionPasswordNeededError:
            if password:
                await client.sign_in(password=password)
            else:
                return "2FA_REQUIRED"
        except Exception as e:
            logger.error(f"[ERROR] Sign In Failed: {e}")
            return str(e)
        return "SUCCESS"

    async def get_channels(self):
        client = await self.get_client()
        if not await client.is_user_authorized():
            return []

        try:
            await self._report_progress(10, "Fetching Dialogs...")
            dialogs = await client.get_dialogs()
            channels = []

            # Create temp dir if not exists
            if not os.path.exists(TEMP_IMG_DIR):
                os.makedirs(TEMP_IMG_DIR)

            total = len(dialogs)
            for i, d in enumerate(dialogs):
                if d.is_channel or d.is_group:
                    # Report Progress
                    percent = 10 + int((i / total) * 80)
                    await self._report_progress(percent, f"Syncing {d.name[:15]}...")

                    # Download profile photo
                    photo_path = None
                    try:
                        # cached photo name
                        fname = f"channel_{d.id}.jpg"
                        fpath = os.path.join(TEMP_IMG_DIR, fname)

                        if not os.path.exists(fpath):
                            await client.download_profile_photo(d.entity, file=fpath)

                        if os.path.exists(fpath):
                            photo_path = fpath  # Use absolute path for OCR
                    except Exception as e:
                        logger.warning(f"Failed to download photo for {d.name}: {e}")

                    channels.append(
                        {
                            "id": d.id,
                            "name": d.name or "Unnamed Channel",
                            "photo": photo_path,
                        }
                    )

            await self._report_progress(100, "Complete")
            return channels
        except Exception as e:
            logger.error(f"[ERROR] Get Channels Failed: {e}")
            return []

    async def fetch_messages(self, channel_ids, target_date_str):
        client = await self.get_client()

        if not isinstance(channel_ids, list):
            channel_ids = [channel_ids]

        try:
            if target_date_str:
                target_date_obj = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            else:
                target_date_obj = (datetime.now() - timedelta(days=1)).date()
        except (ValueError, TypeError):
            target_date_obj = (datetime.now() - timedelta(days=1)).date()

        ET_OFFSET = timezone(timedelta(hours=-5))
        logger.info(f"Fetching for Date: {target_date_obj}")

        all_messages = []
        
        # --- PARALLEL IMAGE DOWNLOADING QUEUE ---
        download_queue = asyncio.Queue()
        
        # Worker function
        async def image_worker():
            while True:
                item = await download_queue.get()
                msg_dict, message, filename = item
                
                try:
                    path = os.path.join(TEMP_IMG_DIR, filename)
                    
                    if not os.path.exists(path):
                        # Try thumbnail first ('x' = 800px), fallback to full image
                        try:
                            # Artificial jitter to avoid instant-ban behavior if too fast
                            await asyncio.sleep(random.uniform(0.05, 0.2))
                            await client.download_media(message, path, thumb="x")
                        except Exception:
                            # logger.debug(f"Thumbnail failed for {filename}, trying full...")
                            await client.download_media(message, path)
                    
                    if os.path.exists(path):
                        # Update the shared dictionary (Thread-safe in asyncio since single-threaded loop)
                        msg_dict["images"].append(path)
                        if not msg_dict["image"]:
                            msg_dict["image"] = path
                            
                except FloodWaitError as e:
                    logger.warning(f"[Anti-Flood] Worker sleeping {e.seconds}s...")
                    await asyncio.sleep(e.seconds + 2)
                    # Put back in queue to retry
                    await download_queue.put(item)
                except Exception as e:
                    logger.error(f"Download worker failed for {filename}: {e}")
                finally:
                    download_queue.task_done()

        # Start 20 parallel workers
        workers = [asyncio.create_task(image_worker()) for _ in range(20)]
        
        try:
            for i, channel_id in enumerate(channel_ids):
                # Report Progress 
                percent = int((i / len(channel_ids)) * 95)
                await self._report_progress(percent, f"Reading Channel {i + 1}/{len(channel_ids)}...")

                # Small sleep between channels to be polite
                if i > 0:
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                try:
                    try:
                        entity = await client.get_entity(int(channel_id))
                    except:
                        entity = await client.get_entity(channel_id)

                    channel_name = entity.title if hasattr(entity, "title") else "Unknown"

                    # GROUPING LOGIC
                    grouped_buffer = {}  # grouped_id -> msg_dict

                    try:
                        offset_dt = datetime.combine(target_date_obj + timedelta(days=1), datetime.min.time())
                        offset_dt = offset_dt.replace(tzinfo=ET_OFFSET)

                        async for message in client.iter_messages(entity, limit=500, offset_date=offset_dt):
                            if not message.date:
                                continue

                            msg_et = message.date.astimezone(ET_OFFSET)
                            msg_date = msg_et.date()

                            if msg_date > target_date_obj:
                                continue
                            if msg_date < target_date_obj:
                                break

                            gid = message.grouped_id
                            
                            # Determine the target dictionary
                            target_dict = None
                            
                            # Standard fields relative to THIS message
                            msg_text = message.text or ""
                            
                            if gid:
                                if gid in grouped_buffer:
                                    # Existing Group - Merge
                                    target_dict = grouped_buffer[gid]
                                    # If this message has text and existing doesn't, update it
                                    if msg_text and not target_dict["text"]:
                                        target_dict["text"] = msg_text
                                        target_dict["id"] = message.id # Prefer ID with text?
                                else:
                                    # New Group
                                    target_dict = {
                                        "id": message.id,
                                        "channel_name": "Telegram",
                                        "date": msg_et.strftime("%Y-%m-%d %H:%M ET"),
                                        "text": msg_text,
                                        "images": [],
                                        "image": None,
                                        "grouped_id": gid,
                                        "selected": True,
                                        "do_ocr": True,
                                    }
                                    grouped_buffer[gid] = target_dict
                            else:
                                # Single Message
                                target_dict = {
                                    "id": message.id,
                                    "channel_name": "Telegram",
                                    "date": msg_et.strftime("%Y-%m-%d %H:%M ET"),
                                    "text": msg_text,
                                    "images": [],
                                    "image": None,
                                    "grouped_id": None,
                                    "selected": True,
                                    "do_ocr": True,
                                }
                                all_messages.append(target_dict)
                            
                            # QUEUE IMAGE DOWNLOAD IMMEDIATELY
                            if message.media and isinstance(message.media, MessageMediaPhoto):
                                filename = f"{channel_id}_{message.id}.jpg"
                                # We pass the target_dict ref so worker can update it
                                download_queue.put_nowait((target_dict, message, filename))

                    except Exception as e:
                        logger.error(f"Iter error: {e}")

                    # FLUSH GROUPS
                    # They are already in grouped_buffer, just add them to all_messages
                    # BUT, we need to add them ONLY ONCE.
                    # Wait, if we added them to all_messages inside the loop, we'd duplicate.
                    # My logic above: 'Single Message -> all_messages.append'. 'Grouped -> grouped_buffer'.
                    # So we need to append values of grouped_buffer to all_messages now.
                    for group_msg in grouped_buffer.values():
                        all_messages.append(group_msg)

                except Exception as e:
                    logger.error(f"Error fetching channel {channel_id}: {e}")
                    continue

            # End of Channel Loop
            # Now we just wait for the download queue to finish
            await self._report_progress(95, "Finishing downloads...")
            await download_queue.join()

        finally:
            # Cancel workers
            for w in workers:
                w.cancel()
            
        await self._report_progress(100, "Complete")
        return all_messages



tg_manager = TelegramManager()
