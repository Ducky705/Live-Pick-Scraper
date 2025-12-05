import os
import sys
import subprocess

# ==========================================
# 1. FILE CONTENTS
# ==========================================

DATABASE_PY = """import logging
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
            response = self.client.table('live_raw_picks').select('*') \\
                .eq('status', 'pending') \\
                .lt('process_attempts', 3) \\
                .gt('created_at', yesterday_iso) \\
                .order('created_at', desc=True) \\
                .limit(limit).execute()
            return [RawPick(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching picks: {e}")
            return []

    def get_or_create_capper(self, name: str, fuzzer) -> Optional[int]:
        if not self.client or not name: return None
        
        # 1. Normalize Name
        normalized = ' '.join(name.strip().split()).title()
        
        # 2. POPULATE CACHE (The Fix)
        # If cache is empty, fetch the ENTIRE directory (up to 10k).
        # This ensures fuzzy matching works against EVERYONE, not just recent cappers.
        if not self.capper_cache:
            try:
                logger.info("📚 Loading Capper Directory into cache...")
                # Fetch ID and Name for up to 10,000 cappers
                res = self.client.table('capper_directory').select('id, canonical_name').limit(10000).execute()
                for item in res.data:
                    c_name = item['canonical_name'].strip().title()
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
            # If insert failed (409 Conflict), it means it exists but wasn't in our cache.
            # Fetch it directly.
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
"""

STANDARDIZER_PY = """import re
from typing import Optional
import config

# Keyword mapping for league inference
LEAGUE_KEYWORDS = {
    'NFL': [
        'Lions', 'Chiefs', 'Bills', 'Eagles', '49ers', 'Ravens', 'Cowboys', 'Bengals', 
        'Dolphins', 'Browns', 'Texans', 'Jaguars', 'Steelers', 'Colts', 'Seahawks', 
        'Buccaneers', 'Packers', 'Rams', 'Falcons', 'Saints', 'Vikings', 'Bears', 
        'Raiders', 'Broncos', 'Chargers', 'Giants', 'Commanders', 'Titans', 'Cardinals', 
        'Panthers', 'Patriots', 'Jets'
    ],
    'NBA': [
        'Celtics', 'Nuggets', 'Bucks', 'Timberwolves', 'Thunder', 'Clippers', 'Suns', 
        'Knicks', 'Cavaliers', 'Magic', 'Sixers', '76ers', 'Pacers', 'Heat', 'Kings', 
        'Mavericks', 'Lakers', 'Warriors', 'Pelicans', 'Rockets', 'Grizzlies', 'Hawks', 
        'Nets', 'Jazz', 'Bulls', 'Raptors', 'Hornets', 'Wizards', 'Pistons', 'Spurs', 
        'Trail Blazers'
    ],
    'NHL': [
        'Bruins', 'Rangers', 'Stars', 'Canucks', 'Panthers', 'Avalanche', 'Jets', 
        'Oilers', 'Hurricanes', 'Maple Leafs', 'Golden Knights', 'Predators', 'Kings', 
        'Lightning', 'Red Wings', 'Blues', 'Flyers', 'Capitals', 'Islanders', 'Devils', 
        'Flames', 'Kraken', 'Penguins', 'Wild', 'Sabres', 'Senators', 'Coyotes', 
        'Canadiens', 'Blackhawks', 'Ducks', 'Blue Jackets', 'Sharks'
    ],
    'NCAAF': [
        'Boise State', 'Alabama', 'Georgia', 'Ohio State', 'Michigan', 'Texas', 'Oregon',
        'Notre Dame', 'Penn State', 'Ole Miss', 'Missouri', 'LSU', 'Clemson', 'Florida State',
        'Tennessee', 'Oklahoma', 'USC', 'Tulane', 'James Madison', 'JMU', 'Liberty', 
        'UNLV', 'Kennesaw', 'ETSU', 'TCU', 'Navy', 'Army'
    ],
    'NCAAB': [
        'Gonzaga', 'Duke', 'Kansas', 'UConn', 'Houston', 'Purdue', 'Arizona', 'Marquette',
        'Creighton', 'North Carolina', 'Tennessee', 'Auburn', 'Kentucky', 'Illinois',
        'Baylor', 'Iowa State', 'South Florida', 'North Texas', 'Xavier', 'Drake', 'Iona',
        'Quinnipiac'
    ]
}

def standardize_league(val: str) -> str:
    if not val: return 'Other'
    val = val.upper().strip()
    if val in config.LEAGUE_MAP: return config.LEAGUE_MAP[val]
    aliases = {
        'NCAA FOOTBALL': 'NCAAF', 'CFB': 'NCAAF',
        'NCAA BASKETBALL': 'NCAAB', 'CBB': 'NCAAB', 'COLLEGE BASKETBALL': 'NCAAB',
        'PREMIER LEAGUE': 'EPL', 'CHAMPIONS LEAGUE': 'UCL',
        'MMA': 'UFC', 'FIGHTING': 'UFC', 'KBO': 'MLB', 'NPB': 'MLB'
    }
    if val in aliases: return aliases[val]
    return 'Other'

def standardize_bet_type(val: str) -> str:
    if not val: return 'Unknown'
    val = val.upper().strip()
    mapping = {
        'MONEYLINE': 'Moneyline', 'ML': 'Moneyline',
        'SPREAD': 'Spread', 'POINT SPREAD': 'Spread', 'RUN LINE': 'Spread', 'PUCK LINE': 'Spread',
        'TOTAL': 'Total', 'OVER/UNDER': 'Total', 'O/U': 'Total',
        'PLAYER PROP': 'Player Prop', 'PROP': 'Player Prop',
        'TEAM PROP': 'Team Prop', 'GAME PROP': 'Game Prop',
        'PARLAY': 'Parlay', 'TEASER': 'Teaser', 'FUTURE': 'Future',
        'PERIOD': 'Period', 'QUARTER': 'Period', 'HALF': 'Period', '1H': 'Period', '1Q': 'Period'
    }
    for k, v in mapping.items():
        if k in val: return v
    return 'Unknown'

def _smart_title_case(text: str) -> str:
    if not text: return ""
    text = text.title()
    acronyms = {
        r'\\bMl\\b': 'ML', r'\\bNfl\\b': 'NFL', r'\\bNba\\b': 'NBA', r'\\bMlb\\b': 'MLB',
        r'\\bNhl\\b': 'NHL', r'\\bNcaaf\\b': 'NCAAF', r'\\bNcaab\\b': 'NCAAB',
        r'\\bUfc\\b': 'UFC', r'\\bPra\\b': 'PRA', r'\\bSog\\b': 'SOG',
        r'\\b1H\\b': '1H', r'\\b2H\\b': '2H', r'\\b1Q\\b': '1Q', r'\\b2Q\\b': '2Q',
        r'\\b3Q\\b': '3Q', r'\\b4Q\\b': '4Q', r'\\bVs\\b': 'vs', r'\\bJmu\\b': 'JMU',
        r'\\bTcu\\b': 'TCU', r'\\bUnlv\\b': 'UNLV', r'\\bEtsu\\b': 'ETSU'
    }
    for pattern, replacement in acronyms.items():
        text = re.sub(pattern, replacement, text)
    return text

def format_pick_value(pick: str, bet_type: str, league: str) -> str:
    if not pick: return "Unknown Pick"
    pick = pick.strip()
    pick = _smart_title_case(pick)
    
    if bet_type == 'Unknown': return pick

    if bet_type == 'Moneyline':
        clean = re.sub(r'\\bML\\b|\\bMoneyline\\b', '', pick, flags=re.I).strip()
        return f"{clean} ML"

    if bet_type == 'Spread':
        match = re.search(r'(.+?)\\s*([-+]\\d+(\\.\\d+)?)', pick)
        if match:
            team = match.group(1).strip()
            spread = match.group(2).strip()
            return f"{team} {spread}"
        return pick

    if bet_type == 'Total':
        pick = re.sub(r'\\b(O|Over)\\s*(\\d)', r'Over  ', pick, flags=re.I)
        pick = re.sub(r'\\b(U|Under)\\s*(\\d)', r'Under  ', pick, flags=re.I)
        return pick

    if bet_type == 'Player Prop':
        if ':' not in pick:
            parts = pick.split()
            if len(parts) > 2:
                return f"{parts[0]} {parts[1]}: {' '.join(parts[2:])}"
        return pick

    return pick

def infer_league(pick_text: str) -> str:
    if not pick_text: return 'Other'
    
    # Check exact team matches
    for league, teams in LEAGUE_KEYWORDS.items():
        for team in teams:
            # Word boundary check to avoid partial matches
            if re.search(r'\\b' + re.escape(team) + r'\\b', pick_text, re.IGNORECASE):
                return league
                
    return 'Other'
"""

PROCESSING_SERVICE_PY = """import logging
import time
import re
from typing import List
from thefuzz import process as fuzz_process

from database import db
from models import StandardizedPick
import simple_parser
import ai_parser
import standardizer

logger = logging.getLogger(__name__)

def sanitize_text(text: str) -> str:
    if not text: return ""
    return re.sub(r'[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]', '', text)

def filter_duplicates(picks: List[StandardizedPick]) -> List[StandardizedPick]:
    if not picks: return []
    unique_picks = []
    seen = set()
    for p in picks:
        clean_val = sanitize_text(p.pick_value)
        p.pick_value = clean_val
        sig = (p.capper_id, p.pick_date, clean_val, p.bet_type)
        if sig not in seen:
            unique_picks.append(p)
            seen.add(sig)
    return unique_picks

def process_picks():
    start_time = time.time()
    
    # 1. Get Pending Picks
    raw_picks = db.get_pending_raw_picks(limit=5)
    if not raw_picks: 
        print("💤 No pending picks found in DB.")
        return

    print(f"\\n📥 PROCESSING BATCH: {len(raw_picks)} Messages")
    for p in raw_picks:
        print(f"   - ID {p.id}: {p.capper_name} ({len(p.raw_text)} chars)")

    to_standardize = []
    ai_batch = []
    processed_ids = []

    # 2. Parse
    for pick in raw_picks:
        if len(pick.raw_text) < 100 and "\\n" not in pick.raw_text:
            simple = simple_parser.parse_with_regex(pick)
            if simple:
                to_standardize.append((simple, pick))
                processed_ids.append(pick.id)
                continue
        ai_batch.append(pick)

    # 3. Run AI
    if ai_batch:
        try:
            ai_results = ai_parser.parse_with_ai(ai_batch)
            
            for parsed in ai_results:
                orig = next((p for p in ai_batch if p.id == parsed.raw_pick_id), None)
                if orig:
                    to_standardize.append((parsed, orig))
                    if orig.id not in processed_ids:
                        processed_ids.append(orig.id)
            
            for p in ai_batch:
                if p.id not in processed_ids:
                    processed_ids.append(p.id)

        except Exception as e:
            logger.error(f"AI batch failed: {e}")
            failed_ids = [p.id for p in ai_batch]
            db.increment_attempts(failed_ids)
            processed_ids = [pid for pid in processed_ids if pid not in failed_ids]

    # 4. Standardize & Save
    potential_picks = []
    
    for parsed, raw in to_standardize:
        capper_id = db.get_or_create_capper(raw.capper_name, fuzz_process)
        if not capper_id: capper_id = 9999 

        std_league = standardizer.standardize_league(parsed.league)
        
        # --- NEW: League Inference Fallback ---
        if std_league == 'Other':
            std_league = standardizer.infer_league(parsed.pick_value)
        # --------------------------------------

        std_type = standardizer.standardize_bet_type(parsed.bet_type)
        std_val = standardizer.format_pick_value(parsed.pick_value, std_type, std_league)

        std = StandardizedPick(
            capper_id=capper_id,
            pick_date=raw.pick_date,
            league=std_league,
            pick_value=std_val,
            bet_type=std_type,
            unit=parsed.unit,
            odds_american=parsed.odds_american,
            source_url=raw.source_url,
            source_unique_id=raw.source_unique_id
        )
        potential_picks.append(std)

    final_picks = filter_duplicates(potential_picks)
    
    if final_picks:
        db.insert_structured_picks(final_picks)
        print(f"✅ Inserted {len(final_picks)} picks into DB.")

    # 5. Update Status
    if processed_ids:
        db.update_raw_status(processed_ids, 'processed')
    
    duration = time.time() - start_time
    print(f"⏱️  Batch finished in {duration:.2f}s")

if __name__ == "__main__":
    process_picks()
"""

# ==========================================
# 2. EXECUTION
# ==========================================

def write_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Updated {filename}")

def main():
    print("🚀 UPDATING CODEBASE")
    print("="*40)
    
    write_file('database.py', DATABASE_PY)
    write_file('standardizer.py', STANDARDIZER_PY)
    write_file('processing_service.py', PROCESSING_SERVICE_PY)
    
    print("\n🚀 STARTING PIPELINE (main.py --force)")
    print("="*40)
    
    try:
        subprocess.run([sys.executable, "main.py", "--force"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Pipeline failed with exit code {e.returncode}")
    except Exception as e:
        print(f"❌ Execution error: {e}")

if __name__ == "__main__":
    main()