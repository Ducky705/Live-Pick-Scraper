# src/telegram_client.py
import os
import asyncio
import random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import MessageMediaPhoto
from config import API_ID, API_HASH, TEMP_IMG_DIR, SESSION_FILE_PATH

class TelegramManager:
    def __init__(self):
        self.client = None # Lazy init
        self.phone = None
        self.phone_code_hash = None

    async def get_client(self):
        """
        Ensures the client is initialized on the CURRENT event loop (Background Thread).
        """
        if self.client is None:
            print(f"[DEBUG] Initializing Telegram Client on Loop: {id(asyncio.get_running_loop())}")
            print(f"[DEBUG] Session Path: {SESSION_FILE_PATH}")
            
            # Force integer ID
            try: real_api_id = int(API_ID)
            except: real_api_id = API_ID
            
            # Create client attached to the CURRENT running loop
            self.client = TelegramClient(
                SESSION_FILE_PATH, 
                real_api_id, 
                API_HASH, 
                loop=asyncio.get_running_loop()
            )
            await self.client.connect()
        
        if not self.client.is_connected():
            await self.client.connect()
            
        return self.client

    async def connect_client(self):
        try:
            client = await self.get_client()
            authorized = await client.is_user_authorized()
            print(f"[DEBUG] Authorized: {authorized}")
            return authorized
        except Exception as e:
            print(f"[ERROR] Connect Error: {e}")
            return False

    async def send_code(self, phone):
        self.phone = phone
        try:
            client = await self.get_client()
            print(f"[DEBUG] Sending code to {phone}...")
            
            sent = await client.send_code_request(phone)
            self.phone_code_hash = sent.phone_code_hash
            
            print("[DEBUG] Code sent successfully.")
            return True
        except Exception as e:
            print(f"[ERROR] Send Code Failed: {e}")
            # Reset client on major error to force reconnect
            if "database is locked" in str(e) or "auth key" in str(e).lower():
                if self.client: await self.client.disconnect()
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
            print(f"[ERROR] Sign In Failed: {e}")
            return str(e)
        return "SUCCESS"

    async def get_channels(self):
        client = await self.get_client()
        if not await client.is_user_authorized():
            return []
        
        try:
            dialogs = await client.get_dialogs()
            channels = []
            for d in dialogs:
                if d.is_channel or d.is_group:
                    channels.append({
                        'id': d.id,
                        'name': d.name or "Unnamed Channel"
                    })
            return channels
        except Exception as e:
            print(f"[ERROR] Get Channels Failed: {e}")
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
        print(f"Fetching for Date: {target_date_obj}")
        
        all_messages = []
        download_tasks = []
        
        sem = asyncio.Semaphore(3)

        async def download_image_task(message, filename):
            async with sem:
                await asyncio.sleep(random.uniform(0.2, 0.8)) 
                try:
                    path = os.path.join(TEMP_IMG_DIR, filename)
                    await client.download_media(message, path)
                    return path
                except FloodWaitError as e:
                    print(f"[Anti-Flood] Sleeping {e.seconds}s...")
                    await asyncio.sleep(e.seconds + 1)
                    return await client.download_media(message, path)
                except Exception as e:
                    print(f"Download failed: {e}")
                    return None

        for i, channel_id in enumerate(channel_ids):
            if i > 0:
                await asyncio.sleep(random.uniform(1.5, 3.5))

            try:
                try: entity = await client.get_entity(int(channel_id))
                except: entity = await client.get_entity(channel_id)
                
                channel_name = entity.title if hasattr(entity, 'title') else "Unknown"

                try:
                    async for message in client.iter_messages(entity, limit=200):
                        if not message.date: continue
                        
                        msg_et = message.date.astimezone(ET_OFFSET)
                        msg_date = msg_et.date()
                        
                        if msg_date > target_date_obj:
                            continue
                        
                        if msg_date < target_date_obj:
                            break 
                        
                        msg_dict = {
                            'id': message.id,
                            'channel_name': channel_name,
                            'date': msg_et.strftime("%Y-%m-%d %H:%M ET"),
                            'text': message.text or "",
                            'image': None,
                            'selected': True,
                            'do_ocr': True
                        }

                        if message.media and isinstance(message.media, MessageMediaPhoto):
                            timestamp = int(datetime.now().timestamp())
                            filename = f"{message.id}_{timestamp}.jpg"
                            task = asyncio.create_task(download_image_task(message, filename))
                            download_tasks.append((msg_dict, task, filename))
                        
                        all_messages.append(msg_dict)
                
                except FloodWaitError as e:
                    print(f"[Anti-Flood] Wait {e.seconds}s")
                    await asyncio.sleep(e.seconds + 2)
                    continue

            except Exception as e:
                print(f"Error fetching channel {channel_id}: {e}")
                continue
        
        if download_tasks:
            results = await asyncio.gather(*[t[1] for t in download_tasks])
            for i, res in enumerate(results):
                if res:
                    download_tasks[i][0]['image'] = f"/static/temp_images/{download_tasks[i][2]}"
            
        return all_messages

tg_manager = TelegramManager()