import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from src.supabase_client import get_supabase

class LiveSupabaseClient:
    """Thin wrapper for live pick tables."""
    
    @staticmethod
    def get_checkpoint(channel_id: int) -> str | None:
        client = get_supabase()
        if not client: return None
        
        try:
            res = client.table("scraper_checkpoints").select("last_scraped_at").eq("channel_id", channel_id).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0].get("last_scraped_at")
        except Exception as e:
            logger.error(f"Failed to get checkpoint for channel {channel_id}: {e}")
        return None

    @staticmethod
    def update_checkpoint(channel_id: int, timestamp_str: str) -> bool:
        client = get_supabase()
        if not client: return False
        
        try:
            # We can use upsert/insert with ignore_duplicates, but since we are replacing,
            # REST post might not support true upsert easily, or it might based on primary key.
            # Usually Supabase handles upserts if we send POST with Prefer: resolution=merge-duplicates
            # The underlying QueryBuilder doesn't have an explicit 'upsert' method but insert with conflict resolution works.
            # For simplicity, we just send standard insert, relying on Supabase's config if set, 
            # but ideally we want to UPSERT.
            
            # Since our custom client in `supabase_client.py` doesn't fully support upsert natively in its `insert` 
            # method without tweaking headers, we'll try a manual approach or let `ignore_duplicates=False` act as UPSERT 
            # if the table is configured for it.
            # Actually, standard REST for Supabase uses `Prefer: resolution=merge-duplicates` for upsert.
            
            # Let's add an explicit headers update if possible, or just build the dict and use `utils_urllib.post`
            from src.utils_urllib import post
            
            url = f"{client.url}/rest/v1/scraper_checkpoints"
            headers = client.headers.copy()
            headers["Prefer"] = "return=representation,resolution=merge-duplicates"
            
            payload = {"channel_id": channel_id, "last_scraped_at": timestamp_str}
            
            resp = post(url, json=payload, headers=headers)
            if 200 <= resp.status_code < 300:
                return True
            else:
                logger.error(f"Checkpoint Update Error: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to update checkpoint for channel {channel_id}: {e}")
            return False

    @staticmethod
    def insert_raw_pick(data: dict) -> int | None:
        """
        Inserts into live_raw_picks.
        Returns the inserted ID on success, None on failure.
        """
        client = get_supabase()
        if not client: return None
        
        try:
            # Check if exists first because our custom client might not return the inserted ID 
            # seamlessly if it hits a conflict. But we can just use `ignore_duplicates=True`.
            res = client.table("live_raw_picks").insert([data], ignore_duplicates=True).execute()
            if hasattr(res, 'error') and res.error:
                # If there's an error, check if it's a conflict
                if "duplicate key value" in str(res.error).lower():
                    # It's a duplicate, return None to skip processing
                    return None
                logger.error(f"Insert Raw Error: {res.error}")
                return None
            
            if hasattr(res, 'data') and res.data:
                return res.data[0].get("id")
        except Exception as e:
            logger.error(f"Insert Raw pick failed: {e}")
        return None

    @staticmethod
    def insert_structured_picks(picks: list[dict]) -> bool:
        """
        Inserts into live_structured_picks.
        """
        if not picks:
            return True
            
        client = get_supabase()
        if not client: return False
        
        try:
            res = client.table("live_structured_picks").insert(picks, ignore_duplicates=True).execute()
            if hasattr(res, 'error') and res.error:
                logger.error(f"Insert Structured Error: {res.error}")
                return False
            return True
        except Exception as e:
            logger.error(f"Insert Structured picks failed: {e}")
        return False

    @staticmethod
    def update_raw_pick_status(raw_id: int, status: str) -> bool:
        client = get_supabase()
        if not client: return False
        
        try:
            from src.utils_urllib import request
            url = f"{client.url}/rest/v1/live_raw_picks?id=eq.{raw_id}"
            headers = client.headers.copy()
            # PATCH method for update
            headers["Prefer"] = "return=representation"
            
            payload = {"status": status}
            
            resp = request("PATCH", url, headers=headers, json_data=payload)
            if 200 <= resp.status_code < 300:
                return True
            else:
                logger.error(f"Raw Status Update Error: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to update raw status: {e}")
            return False
