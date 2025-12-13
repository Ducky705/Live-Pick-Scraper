import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from models import RawPick, StandardizedPick

logger = logging.getLogger(__name__)

# --- SMART ALIAS MAPPING ---
CAPPER_ALIASES = {
    "big al": "bigalmcmordie",
    "al mcmordie": "bigalmcmordie",
    "alan mcmordie": "bigalmcmordie",
    "doc sports": "docsports",
    "docs sports": "docsports",
    "scott sprietzer": "scottspreitzer",
    "scott spreitzer": "scottspreitzer",
    "vernon croy": "vernoncroy",
    "vc": "vernoncroy",
    "tony george": "tonygeorge",
    "jason sharpe": "jasonsharpe",
    "strike point": "strikepointsports",
    "sps": "strikepointsports",
    "ferringo": "robertferringo",
    "robert ferringo": "robertferringo",
    "indian cowboy": "indiancowboy",
    "ic": "indiancowboy",
    "vegas mirabe": "vegasmirabet",
    "vegas mira": "vegasmirabet"
}

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

    def _normalize_key(self, name: str) -> str:
        if not name: return ""
        clean = name.lower()
        noise_words = ['vip', 'picks', 'locks', 'plays', 'sports', 'betting', 'consulting', 'capper', 'official', 'premium']
        for word in noise_words:
            clean = clean.replace(word, '')
        clean = re.sub(r'[^a-z0-9]', '', clean)
        return clean

    def _clean_display_name(self, name: str) -> str:
        clean = re.sub(r'[^\x00-\x7F]+', '', name)
        clean = re.sub(r'^[\W_]+|[\W_]+$', '', clean)
        return clean.strip()

    def get_or_create_capper(self, name: str, fuzzer) -> Optional[int]:
        if not self.client or not name: return None
        
        display_name = self._clean_display_name(name)
        
        # --- STRICT VALIDATION ---
        if len(display_name) < 2: return None 
        if re.search(r'\b(vs|over|under)\b', display_name, re.I):
            logger.warning(f"⚠️ Rejected invalid capper name (Matchup): {display_name}")
            return None 
        if re.match(r'^[-+]?\d+(\.\d+)?$', display_name):
            logger.warning(f"⚠️ Rejected invalid capper name (Numeric): {display_name}")
            return None

        normalized_key = self._normalize_key(display_name)
        if not normalized_key: return None

        # Smart Alias Check
        if normalized_key in CAPPER_ALIASES:
            normalized_key = CAPPER_ALIASES[normalized_key]

        # Populate Cache
        if not self.capper_cache:
            try:
                res = self.client.table('capper_directory').select('id, canonical_name').limit(10000).execute()
                for item in res.data:
                    key = self._normalize_key(item['canonical_name'])
                    if key:
                        self.capper_cache[key] = item['id']
                    self.capper_cache[item['canonical_name']] = item['id']
            except Exception as e:
                logger.error(f"Failed to populate capper cache: {e}")

        # Exact Match
        if normalized_key in self.capper_cache:
            return self.capper_cache[normalized_key]

        # Fuzzy Match
        try:
            if self.capper_cache:
                existing_keys = list(self.capper_cache.keys())
                best_match, score = fuzzer.extractOne(normalized_key, existing_keys)
                
                if score >= 88:
                    matched_id = self.capper_cache[best_match]
                    logger.info(f"✨ Fuzzy matched '{display_name}' to existing ({best_match}) - Score: {score}")
                    self.capper_cache[normalized_key] = matched_id
                    return matched_id

            # Create New
            logger.info(f"🆕 Creating NEW Capper: {display_name}")
            res = self.client.table('capper_directory').insert({'canonical_name': display_name}).execute()
            if res.data:
                new_id = res.data[0]['id']
                self.capper_cache[normalized_key] = new_id
                self.capper_cache[display_name] = new_id
                return new_id
            
            return None

        except Exception as e:
            logger.error(f"❌ Error in capper lookup/creation: {e}")
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
