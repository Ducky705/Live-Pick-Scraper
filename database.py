import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from models import RawPick, StandardizedPick

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        try:
            if config.SUPABASE_URL and config.SUPABASE_KEY:
                self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                self.capper_cache = {}
            else:
                logger.error("Supabase credentials missing.")
                self.client = None
        except Exception as e:
            logger.error(f"Failed to init Supabase: {e}")
            self.client = None

    def get_last_checkpoint(self, channel_id: int) -> Optional[datetime]:
        if not self.client: return None
        try:
            res = self.client.table('scraper_checkpoints').select('last_scraped_at').eq('channel_id', channel_id).execute()
            if res.data:
                return datetime.fromisoformat(res.data[0]['last_scraped_at'])
            return None
        except Exception:
            return None

    def update_checkpoint(self, channel_id: int, timestamp: datetime):
        if not self.client: return
        try:
            self.client.table('scraper_checkpoints').upsert({
                'channel_id': channel_id,
                'last_scraped_at': timestamp.isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def upload_raw_pick(self, pick: RawPick) -> bool:
        if not self.client: return False
        try:
            data = pick.model_dump(exclude={'id', 'process_attempts', 'created_at'})
            data['pick_date'] = data['pick_date'].isoformat()
            self.client.table('live_raw_picks').upsert(data, on_conflict='source_unique_id', ignore_duplicates=True).execute()
            return True
        except Exception: return False

    def get_pending_raw_picks(self, limit: int = 10) -> List[RawPick]:
        if not self.client: return []
        try:
            yesterday_iso = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            response = self.client.table('live_raw_picks').select('*') \
                .eq('status', 'pending') \
                .lt('process_attempts', 3) \
                .gt('created_at', yesterday_iso) \
                .order('created_at', desc=True) \
                .limit(limit).execute()
            return [RawPick(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching picks: {e}")
            return []

    def _normalize_capper_name(self, name: str) -> str:
        # Remove emojis, special chars like *, -, _, and extra spaces
        # " **AFS** " -> "AFS"
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        return ' '.join(clean.strip().split()).title()

    def get_or_create_capper(self, name: str, fuzzer) -> Optional[int]:
        if not self.client or not name: return None
        
        # 1. Normalize Name (Strict Cleaning)
        normalized = self._normalize_capper_name(name)
        if not normalized: return None
        
        # 2. POPULATE CACHE
        if not self.capper_cache:
            try:
                logger.info("📚 Loading Capper Directory into cache...")
                res = self.client.table('capper_directory').select('id, canonical_name').limit(10000).execute()
                for item in res.data:
                    # Also normalize cache keys to ensure matching works
                    c_name = self._normalize_capper_name(item['canonical_name'])
                    self.capper_cache[c_name] = item['id']
                logger.info(f"📚 Loaded {len(self.capper_cache)} cappers.")
            except Exception as e:
                logger.error(f"Failed to populate capper cache: {e}")

        # 3. Check Local Cache (Exact Match)
        if normalized in self.capper_cache: 
            return self.capper_cache[normalized]

        try:
            # 4. Fuzzy Match against the FULL Cache
            if self.capper_cache:
                best_match, score = fuzzer.extractOne(normalized, self.capper_cache.keys())
                if score > 90:
                    logger.info(f"✨ Fuzzy matched '{normalized}' to '{best_match}' ({score}%)")
                    self.capper_cache[normalized] = self.capper_cache[best_match]
                    return self.capper_cache[best_match]

            # 5. If not found, INSERT
            res = self.client.table('capper_directory').insert({'canonical_name': normalized}).execute()
            if res.data:
                new_id = res.data[0]['id']
                self.capper_cache[normalized] = new_id
                return new_id
            
            return None

        except Exception as e:
            # 6. THE LOOP BACK (Conflict Recovery)
            try:
                res = self.client.table('capper_directory').select('id').eq('canonical_name', normalized).execute()
                if res.data:
                    existing_id = res.data[0]['id']
                    self.capper_cache[normalized] = existing_id
                    logger.info(f"🔄 Recovered existing capper ID {existing_id} for '{normalized}'")
                    return existing_id
            except Exception as e2:
                logger.error(f"❌ Critical Capper Error: {e2}")
            
            return None

    def insert_structured_picks(self, picks: List[StandardizedPick]):
        if not self.client or not picks: return
        try:
            data = []
            for p in picks:
                d = p.model_dump(exclude={'result'})
                d['pick_date'] = d['pick_date'].isoformat()
                data.append(d)
            self.client.table('live_structured_picks').insert(data).execute()
            logger.info(f"✅ Saved {len(picks)} picks.")
        except Exception as e:
            logger.error(f"Error saving: {e}")

    def update_raw_status(self, ids: List[int], status: str):
        if not self.client or not ids: return
        try:
            self.client.table('live_raw_picks').update({'status': status}).in_('id', ids).execute()
        except Exception: pass

    def increment_attempts(self, ids: List[int]):
        if not self.client or not ids: return
        try:
            for pick_id in ids:
                 self.client.rpc('increment_process_attempts', {'pick_ids': [pick_id]}).execute()
        except Exception:
             for pick_id in ids:
                res = self.client.table('live_raw_picks').select('process_attempts').eq('id', pick_id).execute()
                if res.data:
                    current = res.data[0].get('process_attempts', 0)
                    self.client.table('live_raw_picks').update({'process_attempts': current + 1}).eq('id', pick_id).execute()

    def archive_old_picks(self, hours: int):
        if not self.client: return
        threshold = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        try:
            self.client.table('live_structured_picks').update({'result': 'archived'}).eq('result', 'pending').lt('created_at', threshold).execute()
        except: pass

db = DatabaseManager()
