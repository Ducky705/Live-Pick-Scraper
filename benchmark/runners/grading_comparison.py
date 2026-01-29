#!/usr/bin/env python3
"""
Comprehensive Grading System Comparison Benchmark

Compares OLD (grader.py) vs NEW (src/grading) on real pick data.
"""

import json
import sys
import time
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, ".")


def run_comparison_benchmark():
    """Compare old and new grading systems on real data."""

    print("=" * 70)
    print("GRADING SYSTEM V3 - COMPREHENSIVE COMPARISON BENCHMARK")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Load real picks
    try:
        with open("picks_2026-01-20.json") as f:
            picks = json.load(f)
        print(f"\nLoaded {len(picks)} picks from picks_2026-01-20.json")
    except FileNotFoundError:
        print("No pick file found!")
        return

    # Fetch scores once
    print("\nFetching scores from ESPN...")
    from src.score_fetcher import fetch_scores_for_date

    scores = fetch_scores_for_date("2026-01-20")
    print(f"Fetched {len(scores)} games")

    # =========================================================================
    # OLD SYSTEM BENCHMARK
    # =========================================================================
    print("\n" + "=" * 70)
    print("OLD SYSTEM (src/grader.py)")
    print("=" * 70)

    from src.grader import grade_picks as old_grade_picks

    start = time.time()
    old_results = old_grade_picks(picks, scores)
    old_time = time.time() - start

    old_stats = analyze_results(old_results, key="result")
    print_stats("OLD", old_stats, old_time)

    # =========================================================================
    # NEW SYSTEM BENCHMARK
    # =========================================================================
    print("\n" + "=" * 70)
    print("NEW SYSTEM (src/grading)")
    print("=" * 70)

    from src.grading.engine import GraderEngine
    from src.grading.parser import PickParser

    engine = GraderEngine(scores)

    start = time.time()
    new_results = []
    for p in picks:
        text = p.get("pick", "")
        league = p.get("league", "other")
        parsed = PickParser.parse(text, league, "2026-01-20")
        graded = engine.grade(parsed)
        new_results.append(graded)
    new_time = time.time() - start

    new_stats = analyze_results_new(new_results)
    print_stats("NEW", new_stats, new_time)

    # =========================================================================
    # COMPARISON
    # =========================================================================
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    print(f"\n{'Metric':<25} {'OLD':>12} {'NEW':>12} {'Diff':>12}")
    print("-" * 53)

    old_graded = old_stats.get("Win", 0) + old_stats.get("Loss", 0) + old_stats.get("PUSH", 0)
    new_graded = new_stats.get("WIN", 0) + new_stats.get("LOSS", 0) + new_stats.get("PUSH", 0)
    total = len(picks)

    print(f"{'Picks Graded':<25} {old_graded:>12} {new_graded:>12} {new_graded - old_graded:>+12}")
    print(
        f"{'Coverage %':<25} {100 * old_graded / total:>11.1f}% {100 * new_graded / total:>11.1f}% {100 * (new_graded - old_graded) / total:>+11.1f}%"
    )
    print(
        f"{'Pending/Unknown':<25} {old_stats.get('Pending', 0):>12} {new_stats.get('PENDING', 0):>12} {new_stats.get('PENDING', 0) - old_stats.get('Pending', 0):>+12}"
    )
    print(f"{'Processing Time (s)':<25} {old_time:>12.3f} {new_time:>12.3f} {new_time - old_time:>+12.3f}")

    # Breakdown by type
    print(f"\n{'Bet Type Breakdown':<25}")
    print("-" * 53)

    for bet_type in ["Spread", "Moneyline", "Total", "Player Prop", "Parlay", "Period"]:
        old_count = sum(1 for p in picks if p.get("type") == bet_type)
        if old_count > 0:
            # Count graded for each type in new system
            new_graded_type = sum(
                1
                for i, r in enumerate(new_results)
                if picks[i].get("type") == bet_type and r.grade.value in ["WIN", "LOSS", "PUSH"]
            )
            print(
                f"  {bet_type:<23} {old_count:>5} picks, {new_graded_type:>5} graded ({100 * new_graded_type / old_count:.0f}%)"
            )

    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_picks": total,
        "old_system": {
            "graded": old_graded,
            "pending": old_stats["Pending"],
            "coverage_pct": 100 * old_graded / total,
            "time_sec": old_time,
        },
        "new_system": {
            "graded": new_graded,
            "pending": new_stats["PENDING"],
            "coverage_pct": 100 * new_graded / total,
            "time_sec": new_time,
        },
        "improvement": {
            "graded_diff": new_graded - old_graded,
            "coverage_diff_pct": 100 * (new_graded - old_graded) / total,
            "time_diff_sec": new_time - old_time,
        },
    }

    with open("benchmark/reports/grading_comparison.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n\nResults saved to benchmark/reports/grading_comparison.json")

    return report


def analyze_results(results, key="result"):
    """Analyze old system results."""
    stats = defaultdict(int)
    for r in results:
        result = r.get(key, "Unknown")
        if result in ["Win", "WIN"]:
            stats["Win"] += 1
        elif result in ["Loss", "LOSS"]:
            stats["Loss"] += 1
        elif result in ["PUSH", "Push"]:
            stats["PUSH"] += 1
        elif "Pending" in str(result) or "Unknown" in str(result) or result is None:
            stats["Pending"] += 1
        else:
            stats["Other"] += 1
    return dict(stats)


def analyze_results_new(results):
    """Analyze new system results."""
    stats = defaultdict(int)
    for r in results:
        stats[r.grade.value] += 1
    return dict(stats)


def print_stats(name, stats, time_taken):
    """Print statistics."""
    total = sum(stats.values())
    graded = (
        stats.get("Win", 0) + stats.get("Loss", 0) + stats.get("PUSH", 0) + stats.get("WIN", 0) + stats.get("LOSS", 0)
    )

    print(f"\nResults ({total} picks, {time_taken:.2f}s):")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v} ({100 * v / total:.1f}%)")
    print(f"  Coverage: {graded}/{total} ({100 * graded / total:.1f}%)")


if __name__ == "__main__":
    run_comparison_benchmark()
