import json
import logging
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.grading.engine import GraderEngine
from src.grading.loader import DataLoader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("RegradePending")

def load_json(path: Path) -> Any:
    """Load JSON file safely."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return None

def save_json(path: Path, data: Any):
    """Save JSON file safely."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {path}")
    except Exception as e:
        logger.error(f"Error saving {path}: {e}")

def find_latest_picks_cache(data_dir: Path) -> Path | None:
    """Find the most recent picks_cache file."""
    cache_files = list(data_dir.glob("picks_cache_*.json"))
    if not cache_files:
        return None
    return sorted(cache_files)[-1]

def main():
    logger.info("Starting regrade of pending picks...")

    data_dir = project_root / "src" / "data"
    picks_cache_path = find_latest_picks_cache(data_dir)

    if not picks_cache_path:
        logger.error("No picks cache found.")
        return

    logger.info(f"Loading picks from: {picks_cache_path}")
    picks = load_json(picks_cache_path)
    if not picks:
        return

    # Identify pending picks
    pending_indices = []
    pending_items = []

    for i, pick in enumerate(picks):
        grade = pick.get("grade")
        if grade == "PENDING" or "Game not found" in pick.get("grading_details", ""):
            # Construct the dict structure expected by grade_batch
            # It expects {'pick': str, 'league': str, ...}
            # Our cache items have 'pick' (text) and 'league' keys already.
            # However, we must ensure 'pick' key contains the text.
            # In cache: "pick": "The text..."
            # grading/engine.py:165 uses item.get("pick")
            pending_indices.append(i)
            pending_items.append(pick)

    count = len(pending_indices)
    logger.info(f"Found {count} pending picks to regrade.")

    if count == 0:
        logger.info("No pending picks found. Exiting.")
        return

    # Initialize Engine with DataLoader (which uses cache automatically)
    # The DataLoader fetches on demand, but since we ran backfill, cache should be hot.
    # However, GraderEngine takes 'scores' in __init__.
    # "scores: List of game dictionaries from DataLoader.fetch_scores()"
    # Attempting to load ALL scores might be heavy?
    # Actually, GraderEngine usually pre-fetches for the batch dates.
    # But here we don't know the dates upfront easily without the same logic as backfill.
    # Wait, GraderEngine.__init__ takes `scores`.
    # If the engine is used in a "live" script, it usually fetches scores first.
    # src/grading/auto_processor.py usually does:
    # scores = DataLoader.fetch_scores(dates)
    # engine = GraderEngine(scores)

    # We need to know which dates to feed the engine.
    # We can rely on the same Snowflake logic or just fetch everything relevant?
    # Or, we can instantiate GraderEngine with an empty list and assume it fetches dynamically?
    # Looking at GraderEngine code (Step 6):
    # It has `_get_boxscore` which fetches.
    # But `_find_game` iterates `self.scores`.
    # So we MUST populate `self.scores`.

    # So we need to collect dates again.
    import datetime

    # Simple Snowflake extraction again (duplicated logic, but safe)
    dates_to_fetch = set()
    msg_date_map = {} # We don't have this here easily without reloading strings.
    # Let's just use Snowflake logic primarily.

    # Also load messages.json if available
    messages_path = project_root / "data" / "cache" / "messages.json"
    if messages_path.exists():
        idata = load_json(messages_path)
        if idata and "messages" in idata:
             for m in idata["messages"]:
                 msg_id = str(m.get("id"))
                 d = m.get("date").split(" ")[0]
                 msg_date_map[msg_id] = d

    for item in pending_items:
        msg_id = str(item.get("message_id"))
        date = msg_date_map.get(msg_id)
        if not date and msg_id.isdigit() and len(msg_id) > 15:
            try:
                twitter_epoch = 1288834974657
                timestamp_ms = (int(msg_id) >> 22) + twitter_epoch
                dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0)
                date = dt.strftime("%Y-%m-%d")
            except:
                pass

        if date:
            dates_to_fetch.add(date)

    logger.info(f"Fetching scores for dates: {sorted(list(dates_to_fetch))}")
    if not dates_to_fetch:
        logger.warning("No dates found for pending picks. Regrade might fail.")

    scores = DataLoader.fetch_scores(list(dates_to_fetch))
    logger.info(f"Loaded {len(scores)} games.")

    engine = GraderEngine(scores)

    # Run Grading
    logger.info("Running batch grading...")
    graded_results = engine.grade_batch(pending_items)

    # Update Picks
    success_count = 0
    for idx, result in zip(pending_indices, graded_results):
        # Result is GradedPick
        # We replace the original dict with the new one
        # Note: We must preserve meta-data that isn't in GradedPick if any?
        # GradedPick.to_dict returns a clean structure.
        # It's safer to merge?
        # Let's overwrite, assuming GraderEngine preserves essential info in result.pick

        # Check if status changed from PENDING
        if result.grade.value != "PENDING":
            success_count += 1

        new_dict = result.to_dict()
        # Ensure we keep the message_id and other root fields that might not be in GradedPick
        # GradedPick doesn't seem to have message_id in to_dict (it has game_id).
        # We need to preserve 'message_id', 'capper_name', etc.

        original = picks[idx]
        new_dict["message_id"] = original.get("message_id")
        new_dict["capper_name"] = original.get("capper_name")
        new_dict["_source_text"] = original.get("_source_text")
        new_dict["extraction_method"] = original.get("extraction_method")
        # And any others?

        picks[idx] = new_dict

    logger.info(f"Regrade complete. Resolved {success_count}/{count} pending picks.")

    # Save back
    save_json(picks_cache_path, picks)

if __name__ == "__main__":
    main()
