import logging
import os
import random
import time
from datetime import UTC, datetime, timedelta, timezone

import requests

from config import TEMP_IMG_DIR

# Setup logging
logger = logging.getLogger(__name__)


class DiscordScraper:
    def __init__(self, token=None):
        self.token = token or os.getenv("DISCORD_TOKEN")
        if not self.token:
            # We don't raise error immediately to allow import, but methods will fail
            logger.warning("DISCORD_TOKEN not found in env.")

        self.auth_header = self.token

        # User-Agent to mimic browser (Anti-Detection)
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        self.headers = {
            "Authorization": self.auth_header,
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }

    def fetch_messages(self, channel_id, limit=50):
        """
        Fetches the last 'limit' messages from a channel.
        """
        if not self.token:
            logger.error("Cannot fetch: No DISCORD_TOKEN.")
            return []

        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        params = {"limit": limit}

        logger.info(f"[Discord] Fetching {limit} messages from channel {channel_id}...")

        # Anti-Bot: Random delay before request
        sleep_time = random.uniform(1.0, 3.0)
        time.sleep(sleep_time)

        try:
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 401:
                # Fallback: Try with "Bot " prefix just in case
                logger.warning("[Discord] 401 Unauthorized. Retrying with 'Bot ' prefix...")
                self.headers["Authorization"] = f"Bot {self.token}"
                response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 429:
                retry_after = response.json().get("retry_after", 5)
                logger.warning(f"[Discord] Rate limited. Sleeping for {retry_after}s...")
                time.sleep(retry_after)
                response = requests.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                logger.error(f"[Discord] Error fetching messages: {response.status_code} - {response.text}")
                return []

            messages = response.json()
            return self._process_messages(messages, channel_id)

        except Exception as e:
            logger.error(f"[Discord] Exception during fetch: {e}")
            return []

    def _process_messages(self, messages, channel_id):
        processed = []

        # Ensure directory exists
        if not os.path.exists(TEMP_IMG_DIR):
            os.makedirs(TEMP_IMG_DIR)

        ET_OFFSET = timezone(timedelta(hours=-5))

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

                    # Download if not exists
                    if not os.path.exists(filepath):
                        self._download_image(url, filepath)

                    if os.path.exists(filepath):
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

        return processed

    def _download_image(self, url, filepath):
        try:
            resp = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=10)
            if resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
        except Exception as e:
            logger.error(f"[Discord] Failed to download image {url}: {e}")


# Singleton instance
discord_manager = DiscordScraper()
