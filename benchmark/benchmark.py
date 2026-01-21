"""
Benchmark CLI - One-Command Accuracy Testing
=============================================
Run this to benchmark your scraper against the AI Judge.

Usage:
    python -m benchmark.benchmark [--limit N] [--full]
    
Options:
    --limit N    Process only N messages (default: 30)
    --full       Process ALL messages (may take hours on free tier)
    --quick      Process only 10 messages (fast sanity check)
"""

import os
import sys
import argparse
import subprocess
import time

# Setup paths
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Benchmark the scraper against AI Judge")
    parser.add_argument("--limit", type=int, default=30, help="Number of messages to benchmark")
    parser.add_argument("--full", action="store_true", help="Benchmark ALL messages")
    parser.add_argument("--quick", action="store_true", help="Quick test (10 messages)")
    parser.add_argument("--skip-judge", action="store_true", help="Skip judge, only run comparison")
    args = parser.parse_args()
    
    if args.quick:
        limit = 10
    elif args.full:
        limit = None
    else:
        limit = args.limit
    
    print("=" * 60)
    print("SCRAPER BENCHMARK SUITE")
    print("=" * 60)
    
    # Step 1: Run the Judge (unless skipped)
    if not args.skip_judge:
        print(f"\n[1/2] Running AI Judge on {'ALL' if limit is None else limit} messages...")
        print("     This may take a few minutes on free tier...")
        
        judge_cmd = [sys.executable, "-m", "benchmark.auto_judge"]
        if limit:
            judge_cmd.extend(["--limit", str(limit)])
        
        start = time.time()
        result = subprocess.run(judge_cmd, cwd=BASE_DIR)
        elapsed = time.time() - start
        
        if result.returncode != 0:
            print(f"\n[ERROR] Judge failed with code {result.returncode}")
            return 1
        
        print(f"     Judge completed in {elapsed:.1f}s")
    else:
        print("\n[1/2] Skipping Judge (using existing golden set)")
    
    # Step 2: Run comparison
    print("\n[2/2] Comparing scraper output against golden set...")
    
    test_cmd = [sys.executable, "-m", "benchmark.run_autotest"]
    result = subprocess.run(test_cmd, cwd=BASE_DIR)
    
    if result.returncode != 0:
        print(f"\n[ERROR] Comparison failed with code {result.returncode}")
        return 1
    
    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print("\nReports saved to: benchmark/reports/")
    print("  - auto_golden_set.json  (Judge's ground truth)")
    print("  - accuracy_report.json  (Detailed comparison)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
