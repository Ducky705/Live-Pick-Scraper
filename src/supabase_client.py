# src/supabase_client.py
import os
from datetime import datetime
# Lazy import: supabase module is loaded on first use
# from supabase import create_client, Client  # Moved to get_supabase()

# Try to import from config first (for bundled EXE), fallback to .env
try:
    from config import SUPABASE_URL, SUPABASE_KEY
except ImportError:
    SUPABASE_URL = None
    SUPABASE_KEY = None

# Fallback to environment variables if config doesn't have them
if not SUPABASE_URL or not SUPABASE_KEY:
    from dotenv import load_dotenv

    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- HARDCODED ALIASES ---
MANUAL_ALIASES = {
    "big al": "Al McMordie",
    "bigal": "Al McMordie",
    "aaa": "AAA Sports",
    "asa": "ASA Inc",
}

# --- LAZY SUPABASE CLIENT ---
# Client is created on first use to speed up startup
_supabase = None
_supabase_init_attempted = False


def get_supabase():
    """Lazily initialize and return the Supabase client."""
    global _supabase, _supabase_init_attempted

    if _supabase_init_attempted:
        return _supabase

    _supabase_init_attempted = True

    try:
        if SUPABASE_URL and SUPABASE_KEY:
            from supabase import create_client

            _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            print("Supabase Config Error: Credentials missing in config.py")
            _supabase = None
    except Exception as e:
        print(f"Supabase Init Error: {e}")
        _supabase = None

    return _supabase


# --- CACHES ---
_capper_map = {}  # Name -> ID
_league_map = {}  # Name -> ID
_bet_type_map = {}  # Name -> ID
_variant_map = {}  # Variant Name -> Capper ID
_active_capper_ids = set()  # Set of IDs that have at least 1 pick


def refresh_caches():
    """Fetches IDs for Foreign Key constraints."""
    supabase = get_supabase()
    if not supabase:
        return

    global _capper_map, _league_map, _bet_type_map, _variant_map, _active_capper_ids

    try:
        # 1. Cappers
        res_cap = (
            supabase.table("capper_directory").select("id, canonical_name").execute()
        )
        _capper_map = {
            item["canonical_name"].lower().strip(): item["id"] for item in res_cap.data
        }

        # 2. Variants (Map alias to Capper ID)
        res_var = (
            supabase.table("capper_variants")
            .select("capper_id, variant_name")
            .execute()
        )
        _variant_map = {
            item["variant_name"].lower().strip(): item["capper_id"]
            for item in res_var.data
        }

        # 3. Active Cappers (Check historical stats for activity)
        # Using historical_capper_stats is efficient as it's aggregated
        res_active = (
            supabase.table("historical_capper_stats").select("capper_id").execute()
        )
        # Also check picks table for very recent activity not yet in stats
        # (Optional but safer)
        # res_recent = supabase.table("picks").select("capper_id").limit(1000).execute()

        _active_capper_ids = set(item["capper_id"] for item in res_active.data)

        # 3. Leagues
        res_leagues = supabase.table("leagues").select("id, name, sport").execute()
        _league_map = {}
        for l in res_leagues.data:
            _league_map[l["name"].lower().strip()] = l["id"]
            if l.get("sport"):
                _league_map[l["sport"].lower().strip()] = l["id"]

        # 4. Bet Types
        res_types = supabase.table("bet_types").select("id, name").execute()
        _bet_type_map = {t["name"].lower().strip(): t["id"] for t in res_types.data}

        print(
            f"Cached: {len(_capper_map)} Cappers ({len(_active_capper_ids)} Active), {len(_league_map)} Leagues, {len(_bet_type_map)} Bet Types."
        )

    except Exception as e:
        print(f"Error refreshing caches: {e}")


def get_capper_cache():
    if not _capper_map:
        refresh_caches()
    return _capper_map, _variant_map


def get_matcher_candidates():
    """
    Constructs the candidate list for CapperMatcher.
    Returns list of dicts: {'name': str, 'id': int, 'type': str, 'is_active': bool}
    """
    if not _capper_map:
        refresh_caches()

    candidates = []

    # Add Canonicals
    for name, cid in _capper_map.items():
        candidates.append(
            {
                "name": name.title(),  # Title case for better matching/display
                "id": cid,
                "type": "canonical",
                "is_active": cid in _active_capper_ids,
            }
        )

    # Add Variants
    for name, cid in _variant_map.items():
        candidates.append(
            {
                "name": name.title(),
                "id": cid,
                "type": "variant",
                "is_active": cid in _active_capper_ids,
            }
        )

    return candidates


def get_or_create_capper_id(name):
    if not name or str(name).lower() == "unknown":
        return None

    # Import here to avoid circular dependency
    from src.capper_matcher import capper_matcher

    clean_lookup = str(name).lower().strip()

    if clean_lookup in MANUAL_ALIASES:
        corrected_name = MANUAL_ALIASES[clean_lookup]
        # Recursively call to handle the corrected name
        return get_or_create_capper_id(corrected_name)

    # Prepare candidates
    candidates = get_matcher_candidates()

    # 1. Try Exact Match (Fast)
    # The new CapperMatcher handles exact matching too, but we can do a quick check here if we wanted.
    # We will let CapperMatcher handle everything to be consistent.

    # 2. Run Fuzzy Match
    # First, try to match against ACTIVE cappers with strict threshold (90)
    # Filter candidates to active only
    active_candidates = [c for c in candidates if c["is_active"]]

    # Try active match first
    matches = capper_matcher.match_name(
        clean_lookup, active_candidates, limit=1, threshold=90
    )

    if matches:
        best = matches[0]
        print(
            f"[Match] '{name}' -> '{best['name']}' (ID: {best['id']}, Score: {best['score']}, Type: {best['type']})"
        )
        return best["id"]

    # 3. If no active match, try matching against ALL cappers (including inactive)
    # Still strict threshold
    matches_all = capper_matcher.match_name(
        clean_lookup, candidates, limit=1, threshold=90
    )

    if matches_all:
        best = matches_all[0]
        print(
            f"[Match-Inactive] '{name}' -> '{best['name']}' (ID: {best['id']}, Score: {best['score']})"
        )
        return best["id"]

    # 4. If still no match, Create New Capper (User Preference: Auto-Create)
    clean_insert_name = str(name).strip()
    supabase = get_supabase()
    try:
        print(f"[DB] No match found. Creating new capper: {clean_insert_name}")
        res = (
            supabase.table("capper_directory")
            .insert({"canonical_name": clean_insert_name})
            .execute()
        )

        if res.data and len(res.data) > 0:
            new_id = res.data[0]["id"]
            # Update cache immediately
            _capper_map[clean_insert_name.lower()] = new_id
            return new_id
    except Exception as e:
        print(f"Error creating capper '{name}': {e}")
        return None
    return None


def get_league_id(name):
    if not name:
        return None
    clean = str(name).lower().strip()
    return _league_map.get(clean)


def get_bet_type_id(type_str):
    if not type_str:
        return _bet_type_map.get("moneyline")
    clean = str(type_str).lower().strip()

    if clean in _bet_type_map:
        return _bet_type_map[clean]
    if "spread" in clean:
        return _bet_type_map.get("spread")
    if "total" in clean or "over" in clean or "under" in clean:
        return _bet_type_map.get("total")
    if "prop" in clean:
        return _bet_type_map.get("player prop")
    if "parlay" in clean:
        return _bet_type_map.get("parlay")
    return _bet_type_map.get("moneyline")


def fetch_all_cappers():
    if not _capper_map:
        refresh_caches()
    return [{"name": k.title(), "id": v} for k, v in _capper_map.items()]


def upload_picks(picks, target_date=None):
    supabase = get_supabase()
    if not supabase:
        return {"success": False, "error": "Supabase not configured."}

    refresh_caches()

    # Fallback date if target_date is missing (should rely on main.py passing it though)
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    db_rows = []
    errors = []

    for i, p in enumerate(picks):
        try:
            capper_id = get_or_create_capper_id(p.get("capper_name"))
            if not capper_id:
                errors.append(
                    f"Row {i + 1}: Could not find or create Capper '{p.get('capper_name')}'."
                )
                continue

            league_id = get_league_id(p.get("league"))
            if not league_id:
                league_id = _league_map.get("other")
                if not league_id:
                    errors.append(
                        f"Row {i + 1}: League '{p.get('league')}' not recognized."
                    )
                    continue

            bet_type_id = get_bet_type_id(p.get("type"))
            if not bet_type_id:
                if _bet_type_map:
                    bet_type_id = list(_bet_type_map.values())[0]
                else:
                    errors.append(f"Row {i + 1}: No Bet Types defined in DB.")
                    continue

            odds_val = p.get("odds")
            if odds_val == "" or odds_val is None:
                odds_val = None
            else:
                try:
                    odds_val = int(odds_val)
                except:
                    odds_val = None

            res_map = {"win": "win", "loss": "loss", "push": "push", "void": "void"}
            result_val = res_map.get(str(p.get("result", "")).lower(), None)

            row = {
                "capper_id": capper_id,
                "league_id": league_id,
                "bet_type_id": bet_type_id,
                "pick_value": p.get("pick", "Unknown Pick"),
                "pick_date": target_date,  # FORCE USE OF TARGET DATE
                "odds_american": odds_val,
                "unit": float(p.get("units", 1.0)),
                "result": result_val,
                "status": "graded" if result_val else "pending_grading",
                "grading_notes": p.get("score_summary", ""),
                "created_at": "now()",
                "updated_at": "now()",
            }
            db_rows.append(row)

        except Exception as e:
            errors.append(f"Row {i + 1} Error: {str(e)}")

    if not db_rows:
        return {
            "success": False,
            "error": "No valid rows to insert.",
            "details": errors,
        }

    try:
        response = supabase.table("picks").insert(db_rows).execute()
        return {"success": True, "count": len(db_rows), "details": errors}
    except Exception as e:
        return {"success": False, "error": str(e), "details": errors}
