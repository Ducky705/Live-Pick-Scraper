#!/usr/bin/env python3
"""
Regrade Pending Picks - Fast Parallel Regrading

This script:
1. Fetches ALL picks from Supabase where result is NOT 'win', 'loss', or 'push'
2. Grades them in parallel using multi-threading
3. Batch updates results back to Supabase

Optimizations:
- Parallel score fetching for all dates at once
- Concurrent pick grading with ThreadPoolExecutor
- Batch updates (50 picks per batch) to minimize API calls
- Score caching to avoid refetching

Usage:
    python scripts/regrade_pending.py --dry-run        # Preview what would be updated
    python scripts/regrade_pending.py --limit 100      # Test with 100 picks
    python scripts/regrade_pending.py                  # Full regrade
    python scripts/regrade_pending.py --workers 8      # Use 8 threads
"""

import sys
import os
import argparse
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Thread-safe score cache
_score_cache = {}
_score_cache_lock = threading.Lock()


def get_supabase_client():
    """Create Supabase client from environment variables."""
    try:
        from supabase import create_client
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
            return None
        
        return create_client(url, key)
    except Exception as e:
        print(f"ERROR: Failed to create Supabase client: {e}")
        return None


def fetch_pending_picks(supabase, limit=None):
    """
    Fetch all picks where result is NOT win/loss/push.
    Uses pagination to handle Supabase 1000 row limit.
    """
    print("Fetching pending picks (result != win/loss/push)...")
    
    all_picks = []
    batch_size = 1000
    offset = 0
    
    # Valid results we want to EXCLUDE
    graded_results = ['win', 'loss', 'push']
    
    while True:
        # Fetch picks where result is NULL or not in graded_results
        # We need to do this in two queries since Supabase doesn't support NOT IN easily
        
        # Query 1: result is NULL
        query = supabase.table('picks').select(
            'id, pick_value, pick_date, result, grading_notes, league_id'
        ).is_(
            'result', 'null'
        ).order('pick_date', desc=True).range(offset, offset + batch_size - 1)
        
        result = query.execute()
        batch = result.data
        
        if not batch:
            break
            
        all_picks.extend(batch)
        
        if len(batch) < batch_size:
            break
            
        offset += batch_size
        
        if offset > 100000:
            print("  Warning: Hit safety limit of 100,000 picks")
            break
    
    # Also fetch picks with non-standard results (pending, error, etc.)
    offset = 0
    while True:
        query = supabase.table('picks').select(
            'id, pick_value, pick_date, result, grading_notes, league_id'
        ).not_.in_('result', graded_results).order('pick_date', desc=True).range(offset, offset + batch_size - 1)
        
        try:
            result = query.execute()
            batch = result.data
            
            if not batch:
                break
            
            # Avoid duplicates (in case null was included)
            existing_ids = {p['id'] for p in all_picks}
            new_picks = [p for p in batch if p['id'] not in existing_ids]
            all_picks.extend(new_picks)
            
            if len(batch) < batch_size:
                break
                
            offset += batch_size
            
            if offset > 100000:
                break
        except Exception as e:
            # If the NOT IN query fails, just use what we have
            print(f"  Note: Extended query failed ({e}), using null results only")
            break
    
    # Apply limit if specified
    if limit and len(all_picks) > limit:
        all_picks = all_picks[:limit]
    
    print(f"Found {len(all_picks)} pending picks to regrade")
    return all_picks


def fetch_league_map(supabase):
    """Fetch league ID to name mapping."""
    result = supabase.table('leagues').select('id, name').execute()
    return {item['id']: item['name'] for item in result.data}


def prefetch_all_scores(dates):
    """
    Prefetch scores for all dates in parallel.
    Returns a dict of date -> scores.
    """
    from src.score_fetcher import fetch_scores_for_date
    
    print(f"Prefetching scores for {len(dates)} dates in parallel...")
    
    scores_by_date = {}
    
    def fetch_date(date):
        try:
            scores = fetch_scores_for_date(date)
            return date, scores
        except Exception as e:
            print(f"  Error fetching scores for {date}: {e}")
            return date, []
    
    # Use 10 workers for parallel score fetching
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_date, d): d for d in dates}
        
        for future in as_completed(futures):
            date, scores = future.result()
            scores_by_date[date] = scores
            with _score_cache_lock:
                _score_cache[date] = scores
    
    total_games = sum(len(s) for s in scores_by_date.values())
    print(f"Prefetched {total_games} games across {len(dates)} dates")
    
    return scores_by_date


def get_cached_scores(date):
    """Get scores from cache or fetch if not present."""
    with _score_cache_lock:
        if date in _score_cache:
            return _score_cache[date]
    
    # Fetch if not cached
    from src.score_fetcher import fetch_scores_for_date
    scores = fetch_scores_for_date(date)
    
    with _score_cache_lock:
        _score_cache[date] = scores
    
    return scores


def grade_single_pick(pick, league_map):
    """
    Grade a single pick. Thread-safe.
    Returns (pick_id, result_dict).
    """
    from src.grading.engine import GraderEngine
    from src.grading.parser import PickParser
    
    pick_id = pick['id']
    pick_text = pick['pick_value']
    pick_date = pick['pick_date']
    league_id = pick.get('league_id')
    league_name = league_map.get(league_id, 'other')
    
    try:
        # Get cached scores
        scores = get_cached_scores(pick_date)
        if not scores:
            return pick_id, {
                'grade': 'PENDING',
                'score_summary': 'No scores available for this date',
                'details': ''
            }
        
        engine = GraderEngine(scores)
        parsed = PickParser.parse(pick_text, league_name, pick_date)
        graded = engine.grade(parsed)
        
        return pick_id, {
            'grade': graded.grade.value,
            'score_summary': graded.score_summary or graded.details or '',
            'details': graded.details or ''
        }
    except Exception as e:
        return pick_id, {
            'grade': 'ERROR',
            'score_summary': '',
            'details': str(e)[:200]
        }


def grade_picks_parallel(picks, league_map, max_workers=4):
    """
    Grade all picks in parallel using ThreadPoolExecutor.
    """
    print(f"Grading {len(picks)} picks with {max_workers} workers...")
    
    results = {}
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(grade_single_pick, pick, league_map): pick['id']
            for pick in picks
        }
        
        for future in as_completed(futures):
            pick_id, result = future.result()
            results[pick_id] = result
            completed += 1
            
            if completed % 100 == 0:
                print(f"  Graded {completed}/{len(picks)} picks...")
    
    return results


def batch_update_supabase(supabase, updates, dry_run=False, batch_size=50):
    """
    Batch update picks in Supabase for efficiency.
    """
    if dry_run:
        print(f"\n[DRY RUN] Would update {len(updates)} picks:")
        
        # Show summary by grade
        grade_counts = defaultdict(int)
        for data in updates.values():
            grade_counts[data['grade']] += 1
        
        for grade, count in sorted(grade_counts.items()):
            print(f"  {grade}: {count}")
        
        # Show sample updates
        print("\nSample updates:")
        for i, (pick_id, data) in enumerate(list(updates.items())[:10]):
            summary = data['score_summary'][:60] if data['score_summary'] else ''
            print(f"  ID {pick_id}: {data['grade']} - {summary}")
        
        if len(updates) > 10:
            print(f"  ... and {len(updates) - 10} more")
        
        return
    
    print(f"\nUpdating {len(updates)} picks in batches of {batch_size}...")
    
    success_count = 0
    error_count = 0
    
    # Convert to list for batching
    update_list = list(updates.items())
    
    for i in range(0, len(update_list), batch_size):
        batch = update_list[i:i + batch_size]
        
        for pick_id, data in batch:
            try:
                # Map grade to result value
                result_map = {
                    'WIN': 'win',
                    'LOSS': 'loss',
                    'PUSH': 'push',
                    'PENDING': None,
                    'ERROR': None
                }
                
                result_val = result_map.get(data['grade'])
                status_val = 'graded' if result_val else 'pending_grading'
                
                update_data = {
                    'result': result_val,
                    'status': status_val,
                    'grading_notes': data['score_summary'][:500] if data['score_summary'] else None,
                    'updated_at': datetime.now().isoformat()
                }
                
                supabase.table('picks').update(update_data).eq('id', pick_id).execute()
                success_count += 1
                
            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"  ERROR updating pick {pick_id}: {e}")
        
        # Progress update
        processed = min(i + batch_size, len(update_list))
        print(f"  Updated {processed}/{len(updates)} picks...")
    
    print(f"\nCompleted: {success_count} success, {error_count} errors")


def main():
    parser = argparse.ArgumentParser(description='Regrade all pending picks (result != win/loss/push)')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without updating')
    parser.add_argument('--limit', type=int, help='Limit number of picks to process')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers (default: 4)')
    parser.add_argument('--date', type=str, help='Regrade only picks from this date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print("=" * 70)
    print("PENDING PICKS REGRADER - Fast Parallel Processing")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Workers: {args.workers}")
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
    
    # Fetch pending picks
    picks = fetch_pending_picks(supabase, limit=args.limit)
    if not picks:
        print("No pending picks to regrade")
        return 0
    
    # Filter by date if specified
    if args.date:
        picks = [p for p in picks if p['pick_date'] == args.date]
        print(f"Filtered to {len(picks)} picks for date {args.date}")
    
    if not picks:
        print("No picks to process after filtering")
        return 0
    
    # Get unique dates
    unique_dates = list(set(p['pick_date'] for p in picks))
    print(f"Picks span {len(unique_dates)} unique dates")
    
    # Prefetch all scores in parallel
    prefetch_all_scores(unique_dates)
    
    # Grade all picks in parallel
    results = grade_picks_parallel(picks, league_map, max_workers=args.workers)
    
    # Calculate stats
    stats = defaultdict(int)
    for data in results.values():
        stats[data['grade']] += 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("GRADING SUMMARY")
    print("=" * 70)
    for grade, count in sorted(stats.items()):
        pct = (count / len(results) * 100) if results else 0
        print(f"  {grade}: {count} ({pct:.1f}%)")
    
    total_graded = stats.get('WIN', 0) + stats.get('LOSS', 0) + stats.get('PUSH', 0)
    total_pending = stats.get('PENDING', 0) + stats.get('ERROR', 0)
    print(f"\n  Total Graded: {total_graded}")
    print(f"  Still Pending: {total_pending}")
    
    # Filter to only picks that changed to a definitive result
    updates_to_apply = {
        pick_id: data for pick_id, data in results.items()
        if data['grade'] in ('WIN', 'LOSS', 'PUSH')
    }
    
    print(f"\n  Picks to update in Supabase: {len(updates_to_apply)}")
    
    # Update Supabase
    if updates_to_apply:
        batch_update_supabase(supabase, updates_to_apply, dry_run=args.dry_run)
    else:
        print("  No picks need updating (all still pending)")
    
    # Timing
    elapsed = (datetime.now() - start_time).total_seconds()
    picks_per_sec = len(picks) / elapsed if elapsed > 0 else 0
    
    print("\n" + "=" * 70)
    print(f"Completed in {elapsed:.1f}s ({picks_per_sec:.1f} picks/sec)")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
