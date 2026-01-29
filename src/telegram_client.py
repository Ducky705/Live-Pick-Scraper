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

from config import API_HASH, API_ID, SESSION_FILE_PATH, TEMP_IMG_DIR


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
        download_tasks = []

        sem = asyncio.Semaphore(3)

        async def download_image_task(message, filename):
            async with sem:
                await asyncio.sleep(random.uniform(0.2, 0.8))
                try:
                    path = os.path.join(TEMP_IMG_DIR, filename)
                    if os.path.exists(path):
                        return path

                    # Try thumbnail first ('x' = 800px), fallback to full image for older posts
                    try:
                        await client.download_media(message, path, thumb="x")
                    except Exception:
                        # Thumbnail not available (common for older messages), try full image
                        logger.warning(f"[Fallback] Thumbnail unavailable for {filename}, downloading full image...")
                        await client.download_media(message, path)  # No thumb = full image

                    return path if os.path.exists(path) else None
                except FloodWaitError as e:
                    logger.warning(f"[Anti-Flood] Sleeping {e.seconds}s...")
                    await asyncio.sleep(e.seconds + 1)
                    try:
                        await client.download_media(message, path)  # Retry with full image
                        return path if os.path.exists(path) else None
                    except:
                        return None
                except Exception as e:
                    logger.error(f"Download failed for {filename}: {e}")
                    return None

        for i, channel_id in enumerate(channel_ids):
            # Report Progress - Channel reading gets 0-10% of the bar (fast)
            percent = int((i / len(channel_ids)) * 10)
            await self._report_progress(percent, f"Reading Channel {i + 1}/{len(channel_ids)}...")

            if i > 0:
                await asyncio.sleep(random.uniform(1.5, 3.5))

            try:
                try:
                    entity = await client.get_entity(int(channel_id))
                except:
                    entity = await client.get_entity(channel_id)

                channel_name = entity.title if hasattr(entity, "title") else "Unknown"

                # GROUPING LOGIC
                grouped_buffer = {}  # grouped_id -> { 'main_msg': msg_dict, 'images': [] }

                try:
                    # Calculate offset_date: Start of the day AFTER target date (in ET)
                    # This ensures we fetch messages starting from midnight after target date, going backwards
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

                        # Determine if message is part of a group
                        gid = message.grouped_id

                        # Base Message Dict
                        msg_dict = {
                            "id": message.id,
                            "channel_name": "Telegram",  # Anonymized as per user request
                            "date": msg_et.strftime("%Y-%m-%d %H:%M ET"),
                            "text": message.text or "",
                            "images": [],  # NEW: List of all images
                            "image": None,  # Legacy compatibility (thumbnail)
                            "grouped_id": gid,
                            "selected": True,
                            "do_ocr": True,
                        }

                        # IMAGE HANDLING
                        if message.media and isinstance(message.media, MessageMediaPhoto):
                            filename = f"{channel_id}_{message.id}.jpg"
                            task = asyncio.create_task(download_image_task(message, filename))
                            # We store the task/metadata temporarily
                            msg_dict["pending_download"] = (task, filename)

                        # GROUPING STRATEGY
                        if gid:
                            if gid not in grouped_buffer:
                                # New Group
                                grouped_buffer[gid] = msg_dict
                            else:
                                # Existing Group - Merge
                                existing = grouped_buffer[gid]
                                # Prefer the ID of the message with text (usually first)
                                if msg_dict["text"] and not existing["text"]:
                                    existing["text"] = msg_dict["text"]
                                    existing["id"] = msg_dict[
                                        "id"
                                    ]  # Use ID of text message? Or keep first? Telethon usually sends text with first.

                                # Add image to existing group
                                if "pending_download" in msg_dict:
                                    # If existing already has a pending download, we need to handle multiple
                                    # We need a structure to hold multiple pending downloads
                                    if "pending_downloads" not in existing:
                                        existing["pending_downloads"] = []
                                        if "pending_download" in existing:
                                            existing["pending_downloads"].append(existing["pending_download"])
                                            del existing["pending_download"]

                                    existing["pending_downloads"].append(msg_dict["pending_download"])
                        else:
                            # Single Message - Add immediately (but handle deferred download)
                            if "pending_download" in msg_dict:
                                msg_dict["pending_downloads"] = [msg_dict["pending_download"]]
                                del msg_dict["pending_download"]
                            all_messages.append(msg_dict)

                except FloodWaitError as e:
                    print(f"[Anti-Flood] Wait {e.seconds}s")
                    await asyncio.sleep(e.seconds + 2)

                # FLUSH GROUPS
                for gid, group_msg in grouped_buffer.items():
                    # Ensure pending_downloads is list
                    if "pending_download" in group_msg:
                        group_msg["pending_downloads"] = [group_msg["pending_download"]]
                        del group_msg["pending_download"]
                    all_messages.append(group_msg)

                # PROCESS DOWNLOADS
                for msg in all_messages:
                    if "pending_downloads" in msg:
                        for task, filename in msg.get("pending_downloads", []):
                            download_tasks.append((msg, task, filename))
                        del msg["pending_downloads"]  # Cleanup logic dict

            except Exception as e:
                logger.error(f"Error fetching channel {channel_id}: {e}")
                continue

        # Media downloading gets 10-95% of the bar with per-file progress
        if download_tasks:
            total_downloads = len(download_tasks)
            completed = 0

            for i, (msg_dict, task, filename) in enumerate(download_tasks):
                # Update progress for each file (10% to 95%)
                percent = 10 + int((i / total_downloads) * 85)
                await self._report_progress(percent, f"Downloading {i + 1}/{total_downloads}...")

                result = await task
                if result:
                    path = result  # Use absolute path for OCR compatibility
                    msg_dict["images"].append(path)
                    if not msg_dict["image"]:
                        msg_dict["image"] = path  # Thumbnail / Backwards Compat

        await self._report_progress(100, "Complete")
        return all_messages


tg_manager = TelegramManager()
