#!/usr/bin/env python3
"""
Benchmark script for ESPN Grader performance.
Measures time for score fetching, grading, and full pipeline.

Usage:
    python tools/benchmark_grader.py [--date YYYY-MM-DD] [--iterations N]
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def log(msg: str, color: str = Colors.WHITE):
    print(f"{color}{msg}{Colors.RESET}")


def log_header(title: str):
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")


def log_metric(label: str, value: float, unit: str = "s"):
    bar_len = min(int(value * 2), 40)
    bar = "#" * bar_len
    color = Colors.GREEN if value < 5 else Colors.YELLOW if value < 15 else Colors.RED
    print(f"  {label:30s} {color}{value:7.2f}{unit}{Colors.RESET} |{bar}")


def get_sample_picks() -> list[dict[str, Any]]:
    """Generate a representative sample of picks for benchmarking."""
    return [
        # NBA
        {"pick": "Lakers -5.5", "league": "nba"},
        {"pick": "Celtics ML", "league": "nba"},
        {"pick": "Lakers vs Celtics Over 220.5", "league": "nba"},
        {"pick": "LeBron James: Pts Over 25.5", "league": "nba"},
        # NFL
        {"pick": "Chiefs -7", "league": "nfl"},
        {"pick": "Bills ML", "league": "nfl"},
        {"pick": "Patrick Mahomes: Pass Yds Over 275.5", "league": "nfl"},
        # NCAAB
        {"pick": "Duke -3.5", "league": "ncaab"},
        {"pick": "Kentucky ML", "league": "ncaab"},
        # NHL
        {"pick": "Rangers ML", "league": "nhl"},
        {"pick": "Bruins -1.5", "league": "nhl"},
        # MLB (if in season)
        {"pick": "Yankees -1.5", "league": "mlb"},
    ]


def benchmark_score_fetching(date_str: str, iterations: int = 1) -> dict[str, float]:
    """Benchmark score fetching with different configurations."""
    from src.score_cache import clear_cache
    from src.score_fetcher import fetch_scores_for_date

    results = {}

    # Clear cache to get accurate baseline
    log("\n  Clearing cache for fresh baseline...", Colors.YELLOW)
    clear_cache()

    # Test 1: Fetch ALL leagues (force refresh to measure actual network time)
    log("\n  [1/4] Fetching ALL leagues (fresh, no cache)...", Colors.YELLOW)
    times = []
    scores = []
    for i in range(iterations):
        start = time.perf_counter()
        scores = fetch_scores_for_date(date_str, force_refresh=True)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        log(f"        Iteration {i + 1}: {elapsed:.2f}s ({len(scores)} games)", Colors.WHITE)

    results["all_leagues_fresh"] = sum(times) / len(times)
    results["all_leagues_games"] = len(scores)

    # Test 1b: Fetch ALL leagues again (should hit cache)
    log("\n  [1b/4] Fetching ALL leagues (cached)...", Colors.YELLOW)
    start = time.perf_counter()
    scores = fetch_scores_for_date(date_str)  # No force_refresh
    elapsed = time.perf_counter() - start
    results["all_leagues_cached"] = elapsed
    log(f"        Cached: {elapsed:.3f}s ({len(scores)} games)", Colors.GREEN)

    # Test 2: Fetch only NBA + NFL (common case)
    log("\n  [2/4] Fetching NBA + NFL only...", Colors.YELLOW)
    times = []
    scores = []
    for i in range(iterations):
        start = time.perf_counter()
        scores = fetch_scores_for_date(date_str, requested_leagues=["nba", "nfl"], force_refresh=True)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        log(f"        Iteration {i + 1}: {elapsed:.2f}s ({len(scores)} games)", Colors.WHITE)

    results["nba_nfl_only"] = sum(times) / len(times)
    results["nba_nfl_games"] = len(scores)

    # Test 3: Fetch only NCAAB (worst case - 32 conference calls)
    log("\n  [3/4] Fetching NCAAB only (32 conferences, fresh)...", Colors.YELLOW)
    times = []
    scores = []
    for i in range(iterations):
        start = time.perf_counter()
        scores = fetch_scores_for_date(date_str, requested_leagues=["ncaab"], force_refresh=True)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        log(f"        Iteration {i + 1}: {elapsed:.2f}s ({len(scores)} games)", Colors.WHITE)

    results["ncaab_only_fresh"] = sum(times) / len(times)
    results["ncaab_games"] = len(scores)

    # Test 3b: NCAAB cached
    log("\n  [3b/4] Fetching NCAAB only (cached)...", Colors.YELLOW)
    start = time.perf_counter()
    scores = fetch_scores_for_date(date_str, requested_leagues=["ncaab"])
    elapsed = time.perf_counter() - start
    results["ncaab_only_cached"] = elapsed
    log(f"        Cached: {elapsed:.3f}s ({len(scores)} games)", Colors.GREEN)

    return results


def benchmark_grading(date_str: str, picks: list[dict], iterations: int = 1) -> dict[str, float]:
    """Benchmark the grading engine."""
    from src.grader import grade_picks
    from src.score_fetcher import fetch_scores_for_date

    results = {}

    # Pre-fetch scores once for grading benchmarks
    log("\n  Pre-fetching scores for grading tests...", Colors.YELLOW)
    scores = fetch_scores_for_date(date_str)
    log(f"  Fetched {len(scores)} games", Colors.WHITE)

    # Test grading
    log(f"\n  Grading {len(picks)} picks...", Colors.YELLOW)
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        graded = grade_picks(picks, scores)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

        wins = sum(1 for p in graded if p.get("result") == "Win")
        losses = sum(1 for p in graded if p.get("result") == "Loss")
        pending = sum(1 for p in graded if p.get("result") in ["Pending", None, ""])
        log(f"        Iteration {i + 1}: {elapsed:.3f}s (W:{wins} L:{losses} P:{pending})", Colors.WHITE)

    results["grading_time"] = sum(times) / len(times)
    results["picks_count"] = len(picks)

    return results


def benchmark_full_pipeline(date_str: str, picks: list[dict]) -> dict[str, float]:
    """Benchmark the full fetch + grade pipeline."""
    from src.grader import grade_picks
    from src.score_fetcher import fetch_scores_for_date

    results = {}

    # Extract leagues from picks (optimized path)
    relevant_leagues = set()
    for p in picks:
        lg = (p.get("league") or p.get("lg") or "").lower()
        if lg:
            relevant_leagues.add(lg)

    # Full pipeline - OPTIMIZED (with league filtering)
    log("\n  [OPTIMIZED] Fetch + Grade with league filtering...", Colors.GREEN)
    start = time.perf_counter()
    scores = fetch_scores_for_date(date_str, requested_leagues=list(relevant_leagues))
    fetch_time = time.perf_counter() - start

    start = time.perf_counter()
    graded = grade_picks(picks, scores)
    grade_time = time.perf_counter() - start

    results["optimized_fetch"] = fetch_time
    results["optimized_grade"] = grade_time
    results["optimized_total"] = fetch_time + grade_time
    results["optimized_games"] = len(scores)

    # Full pipeline - UNOPTIMIZED (fetch all)
    log("\n  [BASELINE] Fetch + Grade without league filtering...", Colors.RED)
    start = time.perf_counter()
    scores = fetch_scores_for_date(date_str)  # No filtering
    fetch_time = time.perf_counter() - start

    start = time.perf_counter()
    graded = grade_picks(picks, scores)
    grade_time = time.perf_counter() - start

    results["baseline_fetch"] = fetch_time
    results["baseline_grade"] = grade_time
    results["baseline_total"] = fetch_time + grade_time
    results["baseline_games"] = len(scores)

    return results


def run_benchmark(date_str: str, iterations: int = 1):
    """Run all benchmarks and display results."""
    log_header(f"ESPN GRADER BENCHMARK - {date_str}")

    picks = get_sample_picks()
    log(f"Sample picks: {len(picks)} ({', '.join(set(p['league'] for p in picks))})")

    all_results = {}

    # 1. Score fetching benchmarks
    log_header("SCORE FETCHING BENCHMARKS")
    fetch_results = benchmark_score_fetching(date_str, iterations)
    all_results["fetch"] = fetch_results

    # 2. Grading benchmarks
    log_header("GRADING BENCHMARKS")
    grade_results = benchmark_grading(date_str, picks, iterations)
    all_results["grade"] = grade_results

    # 3. Full pipeline comparison
    log_header("FULL PIPELINE COMPARISON")
    pipeline_results = benchmark_full_pipeline(date_str, picks)
    all_results["pipeline"] = pipeline_results

    # Summary
    log_header("SUMMARY")

    print(f"\n{Colors.BOLD}Score Fetching (Fresh - No Cache):{Colors.RESET}")
    log_metric("All leagues (fresh)", fetch_results["all_leagues_fresh"])
    log_metric("NBA + NFL only", fetch_results["nba_nfl_only"])
    log_metric("NCAAB only (32 conf)", fetch_results["ncaab_only_fresh"])

    print(f"\n{Colors.BOLD}Score Fetching (Cached):{Colors.RESET}")
    log_metric("All leagues (cached)", fetch_results["all_leagues_cached"])
    log_metric("NCAAB only (cached)", fetch_results["ncaab_only_cached"])

    cache_speedup_all = fetch_results["all_leagues_fresh"] / max(fetch_results["all_leagues_cached"], 0.001)
    cache_speedup_ncaab = fetch_results["ncaab_only_fresh"] / max(fetch_results["ncaab_only_cached"], 0.001)

    print(f"\n{Colors.BOLD}Cache Speedup:{Colors.RESET}")
    print(f"  All leagues: {Colors.GREEN}{cache_speedup_all:.0f}x faster when cached{Colors.RESET}")
    print(f"  NCAAB:       {Colors.GREEN}{cache_speedup_ncaab:.0f}x faster when cached{Colors.RESET}")

    print(f"\n{Colors.BOLD}Full Pipeline:{Colors.RESET}")
    log_metric("BASELINE (all leagues)", pipeline_results["baseline_total"])
    log_metric("OPTIMIZED (filtered)", pipeline_results["optimized_total"])

    speedup = pipeline_results["baseline_total"] / pipeline_results["optimized_total"]
    print(f"\n{Colors.BOLD}{Colors.GREEN}Speedup: {speedup:.2f}x{Colors.RESET}")

    # Save results
    output_file = PROJECT_ROOT / "data" / "cache" / "benchmark_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump({"date": date_str, "timestamp": datetime.now().isoformat(), "results": all_results}, f, indent=2)

    log(f"\nResults saved to: {output_file}", Colors.CYAN)

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Benchmark ESPN Grader performance")
    parser.add_argument("--date", type=str, default=None, help="Date to benchmark (YYYY-MM-DD)")
    parser.add_argument("--iterations", type=int, default=1, help="Number of iterations per test")
    args = parser.parse_args()

    # Default to yesterday Eastern Time
    if args.date is None:
        ET = timezone(timedelta(hours=-5))
        yesterday = datetime.now(ET) - timedelta(days=1)
        args.date = yesterday.strftime("%Y-%m-%d")

    run_benchmark(args.date, args.iterations)


if __name__ == "__main__":
    main()
