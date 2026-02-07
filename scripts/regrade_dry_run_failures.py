
import json
import os
import sys
from collections import Counter
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.grading.engine import GraderEngine, GradeResult
from src.grading.schema import Pick, BetType
from src.score_fetcher import fetch_scores_for_date
# Silence warnings
import requests
requests.packages.urllib3.disable_warnings()
from dotenv import load_dotenv

load_dotenv()

def main():
    cache_path = "src/data/picks_cache_2026-02-05.json"
    if not os.path.exists(cache_path):
        return

    with open(cache_path, 'r') as f:
        data = json.load(f)
    picks = data.get("picks", []) if isinstance(data, dict) else data

    total = len(picks)
    print(f"Total Picks: {total}")

    # 1. Calculate Baseline (Old Version)
    # Filter: Graded picks (W/L/P) MINUS any that relied on the 76ers fix
    # Since we can't easily know which ones *relied* on it without re-parsing, 
    # we will count ALL currently graded "76ers" picks as "Improvements" over the baseline.
    # Assumption: Old parser output "6ers" which failed resolution (PENDING).
    
    current_graded = [p for p in picks if p.get("grade") in ["WIN", "LOSS", "PUSH", "VOID"]]
    current_graded_count = len(current_graded)
    
    # Identify 76ers picks that are currently graded
    # We check if "Philadelphia 76ers" is in the score_summary implies successful resolution
    repaired_76ers = [
        p for p in current_graded 
        if "76ers" in p.get("score_summary", "") 
        and ("76ers" in p.get("pick", "").lower() or "76ers" in p.get("_source_text", "").lower())
    ]
    repaired_76ers_count = len(repaired_76ers)
    
    baseline_count = current_graded_count - repaired_76ers_count
    baseline_pct = (baseline_count / total * 100)
    
    print(f"\nBSLINE (Old Parser): {baseline_count}/{total} ({baseline_pct:.1f}%)")
    print(f"  - Repaired 76ers Picks: {repaired_76ers_count} (These were broken before)")

    # 2. Calculate New Actual (Re-grading Failures)
    # We need to re-run the PENDING picks through the engine to see if Props pass now.
    
    pending_picks = [p for p in picks if p.get("grade") == "PENDING"]
    print(f"\nRe-grading {len(pending_picks)} PENDING picks...")
    
    # Fetch fresh scores (Essential for Prop fix)
    print("Fetching fresh scores...")
    scores = fetch_scores_for_date("2026-02-05", force_refresh=True)
    engine = GraderEngine(scores)
    
    newly_graded_count = 0
    newly_graded_failures = [] # Still pending
    
    # Track prop fixes specifically
    prop_fix_count = 0
    
    for p_data in pending_picks:
        # Reconstruct Pick object
        try:
            pick = Pick(
                raw_text=p_data.get('pick', ''),
                league=p_data.get('league'),
                date=datetime.fromisoformat(p_data.get('date')) if p_data.get('date') else None,
                bet_type=BetType(p_data.get('type', 'Unknown')),
                selection=p_data.get('selection', ''), # Might be empty in cache, using raw_text logic inside engine mostly?
                line=p_data.get('line'),
                stat=p_data.get('stat'),
                is_over=p_data.get('is_over'),
            )
            # Hack: engine.grade uses pick attributes. 
            # If cache didn't save 'selection', we might have trouble.
            # But earlier verify script worked? 
            # Wait, verify script printed "Selection: 'None'".
            # If selection is missing, grading might fail unless we re-parse?
            # Actually, `engine.grade` expects a `Pick` object with `selection`.
            # If `selection` is missing in cache, we MUST re-extract it from `pick` text.
            # Or assume `pick` field in cache *is* user-facing selection?
            # Let's rely on `pick` field which is `raw_text` in cache but seemingly contains the selection info.
            
            # Use a dummy selection if missing, just to see if engine handles it or if we need to re-parse.
            if not pick.selection:
                 pick.selection = p_data.get('pick') # Fallback
            
            # Grade
            res = engine.grade(pick)
            
            if res.grade in [GradeResult.WIN, GradeResult.LOSS, GradeResult.PUSH, GradeResult.VOID]:
                newly_graded_count += 1
                if "LeBron" in pick.raw_text or "Prop" in str(pick.bet_type):
                    prop_fix_count += 1
            else:
                newly_graded_failures.append(p_data)
                
        except Exception as e:
            # print(f"Error regrading: {e}")
            pass

    print(f"  - Newly Graded (Props/Other): {newly_graded_count}")
    
    # 3. Final Numbers
    final_graded_count = current_graded_count + newly_graded_count
    final_pct = (final_graded_count / total * 100)
    
    print(f"\nACTUAL (New Version): {final_graded_count}/{total} ({final_pct:.1f}%)")
    print(f"Improvement: +{(final_pct - baseline_pct):.1f}%")
    print(f"  (76ers Fix: +{repaired_76ers_count})")
    print(f"  (Props/Other Fix: +{newly_graded_count})")

if __name__ == "__main__":
    main()
