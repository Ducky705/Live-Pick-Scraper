
# src/supabase_client.py
import logging
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Try config
try:
    from config import SUPABASE_KEY, SUPABASE_URL
except ImportError:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
     try:
        from dotenv import load_dotenv
        load_dotenv()
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
     except: pass

# --- Custom URLLIB Client to replace Supabase Library ---
from src.utils_urllib import get, post

class SupabaseRESTClient:
    def __init__(self, url, key):
        self.url = url.rstrip('/')
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def table(self, table_name):
        return QueryBuilder(self, table_name)

class QueryBuilder:
    def __init__(self, client, table):
        self.client = client
        self.table_url = f"{client.url}/rest/v1/{table}"
        self.params = {}
        
    def select(self, columns="*"):
        self.params["select"] = columns
        return self
        
    def limit(self, count):
        self.params["limit"] = str(count)
        return self
        
    def eq(self, column, value):
        # Allow multiple eq filters? Simple impl for now.
        # REST syntax: column=eq.value
        self.params[column] = f"eq.{value}"
        return self

    def insert(self, data):
        self.data = data
        self.method = "POST"
        return self
        
    def execute(self):
        # Build Query String
        query_parts = []
        for k, v in self.params.items():
            query_parts.append(f"{k}={v}")
        
        full_url = self.table_url
        if query_parts:
            full_url += "?" + "&".join(query_parts)
            
        try:
            if hasattr(self, 'method') and self.method == "POST":
                resp = post(full_url, json=self.data, headers=self.client.headers)
            else:
                resp = get(full_url, headers=self.client.headers)
            
            if 200 <= resp.status_code < 300:
                return type('obj', (object,), {'data': resp.json()})
            else:
                logger.error(f"Supabase REST Error {resp.status_code}: {resp.text}")
                return type('obj', (object,), {'data': []})
        except Exception as e:
            logger.error(f"Supabase Exec Error: {e}")
            return type('obj', (object,), {'data': []})


def get_supabase():
    if SUPABASE_URL and SUPABASE_KEY:
        return SupabaseRESTClient(SUPABASE_URL, SUPABASE_KEY)
    return None

# --- CACHES (Rest of logic remains similar, relying on get_supabase interface) ---
_capper_map = {}
_league_map = {}
_bet_type_map = {}
_variant_map = {}
_active_capper_ids = set()

def refresh_caches():
    client = get_supabase()
    if not client: return
    
    global _capper_map, _league_map, _bet_type_map, _variant_map, _active_capper_ids
    
    try:
        # 1. Cappers
        res = client.table("capper_directory").select("id, canonical_name").execute()
        _capper_map = {i["canonical_name"].lower().strip(): i["id"] for i in res.data}
        
        # 2. Variants
        res = client.table("capper_variants").select("capper_id, variant_name").execute()
        _variant_map = {i["variant_name"].lower().strip(): i["capper_id"] for i in res.data}
        
        # 3. Active
        res = client.table("historical_capper_stats").select("capper_id").execute()
        _active_capper_ids = set(i["capper_id"] for i in res.data)
        
        # 4. Leagues
        res = client.table("leagues").select("id, name, sport").execute()
        _league_map = {}
        for l in res.data:
            _league_map[l["name"].lower().strip()] = l["id"]
            if l.get("sport"): _league_map[l["sport"].lower().strip()] = l["id"]
            
        # 5. Bet Types
        res = client.table("bet_types").select("id, name").execute()
        _bet_type_map = {t["name"].lower().strip(): t["id"] for t in res.data}
        
    except Exception as e:
        logger.error(f"Cache Refresh Error: {e}")

def get_matcher_candidates():
    if not _capper_map: refresh_caches()
    candidates = []
    for name, cid in _capper_map.items():
        candidates.append({"name": name.title(), "id": cid, "type": "canonical", "is_active": cid in _active_capper_ids})
    for name, cid in _variant_map.items():
        candidates.append({"name": name.title(), "id": cid, "type": "variant", "is_active": cid in _active_capper_ids})
    return candidates

def get_or_create_capper_id(name):
    # Simplified for REST client context
    if not name or str(name).lower() == "unknown": return None
    from src.capper_matcher import capper_matcher
    clean = str(name).strip()
    
    candidates = get_matcher_candidates()
    active = [c for c in candidates if c["is_active"]]
    
    match = capper_matcher.smart_match(clean, active)
    if match: return match["id"]
    
    match_all = capper_matcher.smart_match(clean, candidates)
    if match_all: return match_all["id"]
    
    # Create New
    client = get_supabase()
    try:
        res = client.table("capper_directory").insert({"canonical_name": clean}).execute()
        if res.data:
            cid = res.data[0]["id"]
            _capper_map[clean.lower()] = cid
            return cid
    except: pass
    return None

def get_league_id(name):
    if not name: return None
    return _league_map.get(str(name).lower().strip())

def get_bet_type_id(name):
    if not name: return _bet_type_map.get("moneyline")
    clean = str(name).lower().strip()
    if clean in _bet_type_map: return _bet_type_map[clean]
    if "spread" in clean: return _bet_type_map.get("spread")
    return _bet_type_map.get("moneyline")

def upload_picks(picks, target_date=None):
    client = get_supabase()
    if not client: return {"success": False, "error": "No Client"}
    
    refresh_caches()
    if not target_date: target_date = datetime.now().strftime("%Y-%m-%d")
    
    db_rows = []
    errors = []
    
    for i, p in enumerate(picks):
        try:
            cid = get_or_create_capper_id(p.get("capper_name"))
            if not cid: 
                errors.append(f"Row {i}: Capper missing")
                continue
                
            lid = get_league_id(p.get("league")) or _league_map.get("other")
            bid = get_bet_type_id(p.get("type"))
            
            row = {
                "capper_id": cid,
                "league_id": lid,
                "bet_type_id": bid,
                "pick_value": p.get("pick", "Unknown"),
                "pick_date": target_date,
                "odds_american": int(p.get("odds")) if p.get("odds") else None,
                "unit": float(p.get("units", 1.0)),
                "status": p.get("result", "pending_grading").lower() if p.get("result") else "pending_grading"
            }
            db_rows.append(row)
        except Exception as e:
            errors.append(f"Row {i}: {e}")
            
    if db_rows:
        res = client.table("picks").insert(db_rows).execute()
        return {"success": True, "count": len(db_rows)}
        
    return {"success": False, "details": errors}
