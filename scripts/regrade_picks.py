#!/usr/bin/env python3
"""
Regrade Picks Script - Uses new grading system V3

This script:
1. Fetches picks from Supabase where:
   - pick_date >= 2025-12-01 (last 2 months)
   - source_url IS NULL
2. Grades them using the new grading system
3. Updates the results back to Supabase

Usage:
    python scripts/regrade_picks.py --dry-run        # Preview what would be updated
    python scripts/regrade_picks.py --limit 10       # Test with 10 picks
    python scripts/regrade_picks.py                  # Full regrade
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables for Supabase credentials
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client():
    """Create Supabase client from environment variables."""
    try:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

        if not url or not key:
            print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
            return None

        return create_client(url, key)
    except Exception as e:
        print(f"ERROR: Failed to create Supabase client: {e}")
        return None


def fetch_picks_to_regrade(supabase, limit=None):
    """
    Fetch picks that need regrading with pagination to handle Supabase 1000 row limit.

    Criteria:
    - pick_date >= 2025-12-01
    - source_url IS NULL
    """
    print("Fetching picks to regrade...")

    all_picks = []
    batch_size = 1000
    offset = 0

    while True:
        query = (
            supabase.table("picks")
            .select("id, pick_value, pick_date, result, grading_notes, league_id")
            .gte("pick_date", "2025-12-01")
            .is_("source_url", "null")
            .order("pick_date", desc=True)
            .range(offset, offset + batch_size - 1)
        )

        result = query.execute()
        batch = result.data

        if not batch:
            break

        all_picks.extend(batch)
        print(f"  Fetched batch: {len(batch)} picks (total: {len(all_picks)})")

        # Check if we got less than batch_size (means we're done)
        if len(batch) < batch_size:
            break

        offset += batch_size

        # Safety limit to prevent infinite loops
        if offset > 50000:
            print("  Warning: Hit safety limit of 50,000 picks")
            break

    # Apply limit if specified
    if limit and len(all_picks) > limit:
        all_picks = all_picks[:limit]

    print(f"Found {len(all_picks)} picks to regrade")
    return all_picks


def fetch_league_map(supabase):
    """Fetch league ID to name mapping."""
    result = supabase.table("leagues").select("id, name").execute()
    return {item["id"]: item["name"] for item in result.data}


def grade_picks_batch(picks, league_map, date):
    """
    Grade a batch of picks for a specific date using the new grading system.
    """
    from src.grading.engine import GraderEngine
    from src.grading.parser import PickParser
    from src.score_fetcher import fetch_scores_for_date

    # Fetch scores for this date
    scores = fetch_scores_for_date(date)
    if not scores:
        return {}

    engine = GraderEngine(scores)
    results = {}

    for pick in picks:
        pick_id = pick["id"]
        pick_text = pick["pick_value"]
        league_id = pick.get("league_id")
        league_name = league_map.get(league_id, "other")

        try:
            parsed = PickParser.parse(pick_text, league_name, date)
            graded = engine.grade(parsed)

            results[pick_id] = {
                "grade": graded.grade.value,
                "score_summary": graded.score_summary or graded.details or "",
                "details": graded.details or "",
            }
        except Exception as e:
            results[pick_id] = {"grade": "ERROR", "score_summary": "", "details": str(e)}

    return results


def update_picks_in_supabase(supabase, updates, dry_run=False):
    """
    Update picks in Supabase with new grades.
    """
    if dry_run:
        print("\n[DRY RUN] Would update the following picks:")
        for pick_id, data in updates.items():
            print(f"  ID {pick_id}: {data['grade']} - {data['score_summary'][:50]}")
        return

    success_count = 0
    error_count = 0

    for pick_id, data in updates.items():
        try:
            # Map grade to result value
            result_map = {"WIN": "win", "LOSS": "loss", "PUSH": "push", "PENDING": None, "ERROR": None}

            result_val = result_map.get(data["grade"])
            status_val = "graded" if result_val else "pending_grading"

            update_data = {
                "result": result_val,
                "status": status_val,
                "grading_notes": data["score_summary"],
                "updated_at": datetime.now().isoformat(),
            }

            supabase.table("picks").update(update_data).eq("id", pick_id).execute()
            success_count += 1

        except Exception as e:
            print(f"  ERROR updating pick {pick_id}: {e}")
            error_count += 1

    print(f"\nUpdated {success_count} picks, {error_count} errors")


def main():
    parser = argparse.ArgumentParser(description="Regrade picks using new grading system V3")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without updating")
    parser.add_argument("--limit", type=int, help="Limit number of picks to process")
    parser.add_argument("--date", type=str, help="Regrade only picks from this date (YYYY-MM-DD)")
    args = parser.parse_args()

    print("=" * 70)
    print("PICK REGRADING SCRIPT - Grading System V3")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    # Connect to Supabase
    supabase = get_supabase_client()
    if not supabase:
        return 1

    # Fetch league mapping
    league_map = fetch_league_map(supabase)
    print(f"Loaded {len(league_map)} leagues")

    # Fetch picks to regrade
    picks = fetch_picks_to_regrade(supabase, limit=args.limit)
    if not picks:
        print("No picks to regrade")
        return 0

    # Group picks by date for efficient score fetching
    picks_by_date = defaultdict(list)
    for pick in picks:
        pick_date = pick["pick_date"]
        if args.date and pick_date != args.date:
            continue
        picks_by_date[pick_date].append(pick)

    print(f"\nGrouped into {len(picks_by_date)} unique dates")

    # Process each date
    all_updates = {}
    stats = defaultdict(int)

    for date in sorted(picks_by_date.keys(), reverse=True):
        date_picks = picks_by_date[date]
        print(f"\n--- Processing {date} ({len(date_picks)} picks) ---")

        results = grade_picks_batch(date_picks, league_map, date)

        for pick_id, data in results.items():
            all_updates[pick_id] = data
            stats[data["grade"]] += 1

    # Print summary
    print("\n" + "=" * 70)
    print("GRADING SUMMARY")
    print("=" * 70)
    for grade, count in sorted(stats.items()):
        print(f"  {grade}: {count}")

    total_graded = stats.get("WIN", 0) + stats.get("LOSS", 0) + stats.get("PUSH", 0)
    total_pending = stats.get("PENDING", 0) + stats.get("ERROR", 0)
    print(f"\n  Graded: {total_graded}, Pending: {total_pending}")

    # Update Supabase
    if all_updates:
        update_picks_in_supabase(supabase, all_updates, dry_run=args.dry_run)

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
