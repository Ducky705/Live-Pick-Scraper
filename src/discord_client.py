import asyncio
import logging
import os
import random
from datetime import UTC, datetime, timedelta, timezone

import aiohttp

from config import PROXY_URL, TEMP_IMG_DIR, USER_AGENTS

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

    async def fetch_messages(self, channel_id, target_date=None, limit=100):
        """
        Fetches the messages from a channel (Async).
        Paginates backwards until all messages for the target_date are fetched.
        """
        if not self.token:
            logger.error("Cannot fetch: No DISCORD_TOKEN.")
            return []

        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        
        # Parse target date
        target_dt = None
        if target_date:
            try:
                target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
            except Exception as e:
                logger.warning(f"Could not parse target_date {target_date}: {e}")

        logger.info(f"[Discord] Fetching exhaustively from channel {channel_id} (Date Bound: {target_date})...")

        all_messages = []
        before_id = None
        
        while True:
            params = {"limit": str(limit)}
            if before_id:
                params["before"] = before_id

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
                                    break

                        if response.status == 429:
                            data = await response.json()
                            retry_after = data.get("retry_after", 5)
                            logger.warning(f"[Discord] Rate limited. Sleeping for {retry_after}s...")
                            await asyncio.sleep(retry_after)
                            continue

                        if response.status != 200:
                            text = await response.text()
                            logger.error(f"[Discord] Error fetching messages: {response.status} - {text}")
                            break

                        messages = await response.json()
                        if not messages:
                            break # No more messages in history
                            
                        # Process dates and check if we went far enough
                        reached_past = False
                        
                        for msg in messages:
                            # Parse Message Date
                            ts = msg.get("timestamp")
                            try:
                                msg_dt = datetime.fromisoformat(str(ts)).astimezone(timezone(timedelta(hours=-5))).date()
                                if target_dt and msg_dt < target_dt:
                                    reached_past = True
                                    continue # Don't strictly need to slice out, base pipeline Deduplicator/Filter will clean it, but we can stop.
                            except:
                                pass
                                
                            all_messages.append(msg)
                            
                        if reached_past:
                            logger.info(f"[Discord] Reached messages older than {target_date}. Stopping pagination.")
                            break
                            
                        # Update before_id to the oldest message in the batch to paginate backwards
                        before_id = messages[-1]["id"]
                        
                        # Just a huge safety net in case of no date bound
                        if not target_date and len(all_messages) >= 200:
                            break

            except Exception as e:
                logger.error(f"[Discord] Exception during fetch: {e}")
                break

        logger.info(f"[Discord] Total raw messages fetched for {channel_id}: {len(all_messages)}")
        return await self._process_messages(all_messages, channel_id)

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
