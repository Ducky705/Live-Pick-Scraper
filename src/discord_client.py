import logging
import os
import random
import time
import asyncio
import aiohttp
from datetime import UTC, datetime, timedelta, timezone

from config import TEMP_IMG_DIR, PROXY_URL, USER_AGENTS

# Setup logging
logger = logging.getLogger(__name__)


class DiscordScraper:
    def __init__(self, token=None):
        self.token = token or os.getenv("DISCORD_TOKEN")
        if not self.token:
            # We don't raise error immediately to allow import, but methods will fail
            logger.warning("DISCORD_TOKEN not found in env.")

        self.auth_header = self.token

        # User-Agent to mimic browser (Anti-Detection) - Rotate on init or per request?
        # Let's pick one for the session.
        self.user_agent = random.choice(USER_AGENTS)

        self.headers = {
            "Authorization": self.auth_header,
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }

    async def fetch_messages(self, channel_id, limit=50):
        """
        Fetches the last 'limit' messages from a channel (Async).
        """
        if not self.token:
            logger.error("Cannot fetch: No DISCORD_TOKEN.")
            return []

        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        params = {"limit": str(limit)}

        logger.info(f"[Discord] Fetching {limit} messages from channel {channel_id}...")

        # Anti-Bot: Random delay before request
        await asyncio.sleep(random.uniform(1.0, 3.0))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params, proxy=PROXY_URL) as response:
                    
                    if response.status == 401:
                        # Fallback: Try with "Bot " prefix just in case
                        logger.warning("[Discord] 401 Unauthorized. Retrying with 'Bot ' prefix...")
                        self.headers["Authorization"] = f"Bot {self.token}"
                        async with session.get(url, headers=self.headers, params=params, proxy=PROXY_URL) as response2:
                            response = response2 # Override response
                            if response.status != 200:
                                text = await response.text()
                                logger.error(f"[Discord] Retry Error: {response.status} - {text}")
                                return []

                    if response.status == 429:
                        data = await response.json()
                        retry_after = data.get("retry_after", 5)
                        logger.warning(f"[Discord] Rate limited. Sleeping for {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        # Recursive retry (simple) implementation
                        return await self.fetch_messages(channel_id, limit)

                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"[Discord] Error fetching messages: {response.status} - {text}")
                        return []

                    messages = await response.json()
                    return await self._process_messages(messages, channel_id)

        except Exception as e:
            logger.error(f"[Discord] Exception during fetch: {e}")
            return []

    async def _process_messages(self, messages, channel_id):
        processed = []

        # Ensure directory exists
        if not os.path.exists(TEMP_IMG_DIR):
            os.makedirs(TEMP_IMG_DIR)

        ET_OFFSET = timezone(timedelta(hours=-5))

        download_tasks = []

        # Gather all basic data first
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            # Parse Date
            ts = msg.get("timestamp")
            try:
                if ts:
                    dt = datetime.fromisoformat(str(ts))
                else:
                    raise ValueError("No timestamp")
            except:
                dt = datetime.now(UTC)

            # Convert to ET
            dt_et = dt.astimezone(ET_OFFSET)

            # Handle Images
            image_paths = []
            attachments = msg.get("attachments", [])
            for att in attachments:
                content_type = att.get("content_type", "")
                if content_type and "image" in content_type:
                    url = att.get("url")
                    filename = f"discord_{msg['id']}_{att['id']}.jpg"
                    filepath = os.path.join(TEMP_IMG_DIR, filename)
                    
                    # Add to download queue if not exists
                    if not os.path.exists(filepath):
                        download_tasks.append(self._download_image(url, filepath))
                        image_paths.append(filepath) # Assume it succeeds for metadata
                    else:
                        image_paths.append(filepath)

            # Construct standard dict
            msg_dict = {
                "id": msg["id"],
                "channel_name": "Discord",  # Anonymized as per user request
                "date": dt_et.strftime("%Y-%m-%d %H:%M ET"),
                "text": msg.get("content", ""),
                "images": image_paths,
                "image": image_paths[0] if image_paths else None,
                "grouped_id": None,
                "selected": True,
                "do_ocr": True if image_paths else False,
            }
            processed.append(msg_dict)
        
        # Run downloads concurrently
        # Limit concurrency to 5 downloads at once
        if download_tasks:
            sem = asyncio.Semaphore(5)
            async def semaphore_download(task):
                 async with sem:
                     await task
            
            await asyncio.gather(*[semaphore_download(t) for t in download_tasks])

        return processed

    async def _download_image(self, url, filepath):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={"User-Agent": self.user_agent}, proxy=PROXY_URL, timeout=10) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(filepath, "wb") as f:
                            f.write(content)
        except Exception as e:
            logger.error(f"[Discord] Failed to download image {url}: {e}")


# Singleton instance
discord_manager = DiscordScraper()
