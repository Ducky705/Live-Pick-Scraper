import json
import logging
import sys
import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.score_fetcher import fetch_scores_for_date
from src.grading.constants import ESPN_LEAGUE_MAP

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("BackfillScores")

def load_json(path: Path) -> Any:
    """Load JSON file safely."""
    if not path.exists():
        logger.error(f"File not found: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return None

def find_latest_picks_cache(data_dir: Path) -> Path | None:
    """Find the most recent picks_cache file."""
    cache_files = list(data_dir.glob("picks_cache_*.json"))
    if not cache_files:
        return None
    return sorted(cache_files)[-1]  # Sort by name (date is in name)

def main():
    logger.info("Starting historical score backfill...")

    data_dir = project_root / "src" / "data"
    messages_path = project_root / "data" / "cache" / "messages.json"

    # 1. Load Picks Cache
    picks_cache_path = find_latest_picks_cache(data_dir)
    if not picks_cache_path:
        logger.error("No picks cache found in src/data/")
        return
    
    logger.info(f"Loading picks from: {picks_cache_path}")
    picks = load_json(picks_cache_path)
    if not picks:
        return

    # 2. Load Messages for Date Mapping
    logger.info(f"Loading messages from: {messages_path}")
    messages_data = load_json(messages_path)
    if not messages_data or "messages" not in messages_data:
        logger.error("Invalid messages.json format")
        return
    
    # Map message_id -> date
    msg_date_map = {}
    for msg in messages_data["messages"]:
        msg_id = str(msg.get("id"))
        date_str = msg.get("date") # Format: "2026-01-23 19:01 ET"
        if msg_id and date_str:
            # Extract pure date part (YYYY-MM-DD or MM/DD/YYYY)
            # The date in messages.json seems to be "YYYY-MM-DD ..." based on `view_file` output in Step 28
            # Example: "2026-01-23 19:01 ET" -> "2026-01-23"
            clean_date = date_str.split(" ")[0]
            msg_date_map[msg_id] = clean_date
            
    # 3. Identify Missing Dates
    dates_to_fetch = set()
    pending_count = 0
    
    for pick in picks:
        grade = pick.get("grade")
        details = pick.get("grading_details", "")
        
        # Criteria for backfill: PENDING or specific error messages
        needs_backfill = (
            grade == "PENDING" or 
            "Game not found" in details or 
            pick.get("score_summary") == ""
        )
        
        if needs_backfill:
            msg_id = str(pick.get("message_id"))
            date = msg_date_map.get(msg_id)
            
            # Fallback: Try Snowflake decoding
            if not date and msg_id.isdigit() and len(msg_id) > 15:
                try:
                    twitter_epoch = 1288834974657
                    timestamp_ms = (int(msg_id) >> 22) + twitter_epoch
                    dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0)
                    date = dt.strftime("%Y-%m-%d")
                    logger.info(f"Decoded date {date} from Snowflake ID {msg_id}")
                except Exception as e:
                    logger.debug(f"Failed to decode snowflake {msg_id}: {e}")

            if date:
                dates_to_fetch.add(date)
                pending_count += 1
            else:
                logger.warning(f"Could not find date for message {msg_id} (Pick: {pick.get('pick')})")

    logger.info(f"Found {pending_count} pending picks needing backfill.")
    logger.info(f"Unique dates to fetch: {sorted(list(dates_to_fetch))}")

    # 4. Fetch Scores based on dates
    # We fetch for ALL leagues to be safe, or we could filter by the leagues present in pending picks.
    # For now, let's just fetch everything consistent with ScoreFetcher defaults.
    
    for date_str in sorted(list(dates_to_fetch)):
        logger.info(f"Fetching scores for {date_str}...")
        try:
            # fetch_scores_for_date handles caching internally
            games = fetch_scores_for_date(date_str, force_refresh=True) 
            logger.info(f"  -> Fetched {len(games)} games.")
        except Exception as e:
            logger.error(f"Failed to fetch for {date_str}: {e}")

    logger.info("Backfill complete.")

if __name__ == "__main__":
    main()
