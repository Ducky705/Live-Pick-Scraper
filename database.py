import logging
from datetime import datetime, timedelta
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
            # OPTIMIZATION:
            # 1. Order by created_at DESC (Process newest picks first)
            # 2. Filter out anything created > 24 hours ago (Ignore stuck backlog)
            
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

    def get_or_create_capper(self, name: str, fuzzer) -> Optional[int]:
        if not self.client or not name: return None
        normalized = ' '.join(name.strip().split()).title()
        if normalized in self.capper_cache: return self.capper_cache[normalized]

        try:
            picks_res = self.client.table('live_structured_picks').select('capper_id').order('created_at', desc=True).limit(2000).execute()
            active_ids = {item['capper_id'] for item in picks_res.data if item.get('capper_id')}
            
            lookup_map = {}
            if active_ids:
                capper_res = self.client.table('capper_directory').select('id, canonical_name').in_('id', list(active_ids)).execute()
                for item in capper_res.data:
                    lookup_map[item['canonical_name'].strip().title()] = item['id']

            if normalized in lookup_map:
                self.capper_cache[normalized] = lookup_map[normalized]
                return lookup_map[normalized]

            if lookup_map:
                best_match, score = fuzzer.extractOne(normalized, lookup_map.keys())
                if score > 90:
                    self.capper_cache[normalized] = lookup_map[best_match]
                    return lookup_map[best_match]

            res = self.client.table('capper_directory').insert({'canonical_name': normalized}).execute()
            if res.data:
                new_id = res.data[0]['id']
                self.capper_cache[normalized] = new_id
                return new_id
            return None
        except Exception: return None

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
            # Batch optimization: If we are here, AI failed.
            # Instead of reading/writing one by one, we just blindly increment.
            # This is slightly risky but MUCH faster. 
            # Or we can mark them as 'failed' immediately if they crash the JSON parser.
            for pick_id in ids:
                 self.client.rpc('increment_process_attempts', {'pick_ids': [pick_id]}).execute()
        except Exception:
            # Fallback to slow Python loop if RPC missing
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
