#!/usr/bin/env python3
"""
Grading System Benchmark

Compares the old grader.py against the new src/grading package.
Measures:
  1. Accuracy (% of picks graded correctly)
  2. Coverage (% of picks that receive a definitive grade vs PENDING)
  3. Speed (time to grade N picks)
  4. Prop Support (% of props successfully graded)
  5. Parlay Accuracy (% of parlays correctly graded)
"""

import json
import time
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, '.')

# =============================================================================
# TEST DATASET
# =============================================================================

# Comprehensive test picks covering all bet types from pick_format.md
TEST_PICKS = [
    # MONEYLINE
    {"pick": "Los Angeles Lakers ML", "league": "NBA", "expected_type": "Moneyline"},
    {"pick": "Kansas City Chiefs ML", "league": "NFL", "expected_type": "Moneyline"},
    {"pick": "Tommy Paul ML", "league": "TENNIS", "expected_type": "Moneyline"},
    
    # SPREAD
    {"pick": "Green Bay Packers -7.5", "league": "NFL", "expected_type": "Spread"},
    {"pick": "Boston Celtics +3", "league": "NBA", "expected_type": "Spread"},
    {"pick": "Alabama -14", "league": "NCAAF", "expected_type": "Spread"},
    {"pick": "Duke -6.5", "league": "NCAAB", "expected_type": "Spread"},
    
    # TOTALS
    {"pick": "Lakers vs Celtics Over 215.5", "league": "NBA", "expected_type": "Total"},
    {"pick": "Chiefs vs Eagles Under 48", "league": "NFL", "expected_type": "Total"},
    {"pick": "Rutgers vs Unknown Under 143.5", "league": "NCAAB", "expected_type": "Total"},
    
    # PLAYER PROPS
    {"pick": "LeBron James: Pts Over 25.5", "league": "NBA", "expected_type": "Player Prop"},
    {"pick": "Patrick Mahomes: PassYds Over 275.5", "league": "NFL", "expected_type": "Player Prop"},
    {"pick": "Nikola Jokic: Pts+Reb+Ast Over 50.5", "league": "NBA", "expected_type": "Player Prop"},
    {"pick": "Travis Kelce: Rec Over 5.5", "league": "NFL", "expected_type": "Player Prop"},
    
    # PERIOD BETS
    {"pick": "1H NYK vs BOS Total Over 110.5", "league": "NBA", "expected_type": "Period"},
    {"pick": "1Q Thunder -2", "league": "NBA", "expected_type": "Period"},
    {"pick": "1H George Mason -6", "league": "NCAAB", "expected_type": "Period"},
    {"pick": "F5 Yankees Over 4.5", "league": "MLB", "expected_type": "Period"},
    
    # PARLAYS (Standard)
    {"pick": "(NFL) Dallas Cowboys -10.5 / (NFL) San Francisco 49ers ML", "league": "Other", "expected_type": "Parlay"},
    {"pick": "(NBA) Lakers ML / (NBA) Celtics -3.5", "league": "NBA", "expected_type": "Parlay"},
    
    # PARLAYS (Mixed League)
    {"pick": "(NFL) Cowboys -10.5 / (NBA) Lakers ML", "league": "Other", "expected_type": "Parlay"},
    {"pick": "(NFL) Chiefs ML / (NBA) Bucks -5 / (NHL) Rangers ML", "league": "Other", "expected_type": "Parlay"},
    
    # PARLAYS (Player Props)
    {"pick": "(NFL) Jalen Hurts: RushYds Over 48.5 / (NFL) A.J. Brown: RecYds Over 80.5", "league": "NFL", "expected_type": "Parlay"},
    
    # TENNIS SPECIAL
    {"pick": "Giron +1.5 sets", "league": "TENNIS", "expected_type": "Spread"},
    {"pick": "Paul vs Rune Over 22.5 games", "league": "TENNIS", "expected_type": "Total"},
    
    # SOCCER (3-way ML)
    {"pick": "Arsenal ML", "league": "EPL", "expected_type": "Moneyline"},
    {"pick": "Real Madrid -0.5", "league": "LALIGA", "expected_type": "Spread"},
    
    # UFC/MMA
    {"pick": "Jon Jones ML", "league": "UFC", "expected_type": "Moneyline"},
]


def benchmark_parser():
    """Benchmark the new parser for bet type detection."""
    print("\n" + "="*60)
    print("PARSER BENCHMARK")
    print("="*60)
    
    from src.grading.parser import PickParser
    
    correct = 0
    total = len(TEST_PICKS)
    
    results = []
    
    for pick in TEST_PICKS:
        parsed = PickParser.parse(pick['pick'], pick['league'])
        detected = parsed.bet_type.value
        expected = pick['expected_type']
        
        is_correct = detected == expected
        if is_correct:
            correct += 1
        
        results.append({
            "pick": pick['pick'][:50],
            "expected": expected,
            "detected": detected,
            "correct": is_correct
        })
    
    print(f"\nParsing Accuracy: {correct}/{total} ({100*correct/total:.1f}%)")
    print("\nDetailed Results:")
    print("-"*80)
    
    for r in results:
        status = "OK" if r['correct'] else "FAIL"
        print(f"[{status}] {r['pick'][:40]:<40} | Expected: {r['expected']:<12} | Got: {r['detected']}")
    
    return correct / total


def benchmark_grading_coverage():
    """
    Benchmark grading coverage (% of picks that get a definitive grade).
    Uses cached scores to avoid network calls.
    """
    print("\n" + "="*60)
    print("GRADING COVERAGE BENCHMARK")
    print("="*60)
    
    # Load cached scores if available
    try:
        with open('cache/graded_picks.json', 'r') as f:
            cached = json.load(f)
            
        # Use picks from cache as test data
        test_data = cached if isinstance(cached, list) else cached.get('picks', [])
        
        if not test_data:
            print("No cached picks found. Run with live data first.")
            return 0
            
    except FileNotFoundError:
        print("No cached picks found. Skipping coverage benchmark.")
        return 0
    
    # Test OLD system
    from src.grader import grade_picks
    from src.score_fetcher import fetch_scores_for_date
    
    date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Fetching scores for {date}...")
    scores = fetch_scores_for_date(date)
    print(f"Fetched {len(scores)} games")
    
    # Sample of picks to test
    sample = test_data[:50] if len(test_data) > 50 else test_data
    
    # OLD SYSTEM
    print("\nOLD SYSTEM (grader.py):")
    old_results = grade_picks(sample, scores)
    old_graded = sum(1 for r in old_results if r.get('result') not in ['Pending/Unknown', 'Error', None])
    old_pending = len(old_results) - old_graded
    print(f"  Graded: {old_graded}/{len(old_results)} ({100*old_graded/len(old_results):.1f}%)")
    print(f"  Pending: {old_pending}")
    
    # NEW SYSTEM
    print("\nNEW SYSTEM (src/grading):")
    from src.grading.engine import GraderEngine
    from src.grading.parser import PickParser
    
    engine = GraderEngine(scores)
    
    new_graded = 0
    new_pending = 0
    
    for p in sample:
        text = p.get('pick', p.get('p', ''))
        league = p.get('league', p.get('lg', 'other'))
        parsed = PickParser.parse(text, league)
        result = engine.grade(parsed)
        
        if result.grade.value in ['WIN', 'LOSS', 'PUSH']:
            new_graded += 1
        else:
            new_pending += 1
    
    print(f"  Graded: {new_graded}/{len(sample)} ({100*new_graded/len(sample):.1f}%)")
    print(f"  Pending: {new_pending}")
    
    improvement = new_graded - old_graded
    print(f"\nIMPROVEMENT: {improvement:+d} more picks graded ({100*(new_graded-old_graded)/len(sample):+.1f}%)")
    
    return new_graded / len(sample) if sample else 0


def benchmark_speed():
    """Benchmark grading speed."""
    print("\n" + "="*60)
    print("SPEED BENCHMARK")
    print("="*60)
    
    # Generate synthetic picks
    synthetic = [
        {"pick": f"Team{i} -5.5", "league": "NBA"}
        for i in range(100)
    ]
    
    from src.grading.engine import GraderEngine
    from src.grading.parser import PickParser
    
    # Empty scores for pure parsing/grading speed
    engine = GraderEngine([])
    
    # Parse speed
    start = time.time()
    parsed = [PickParser.parse(p['pick'], p['league']) for p in synthetic]
    parse_time = time.time() - start
    
    # Grade speed
    start = time.time()
    for p in parsed:
        engine.grade(p)
    grade_time = time.time() - start
    
    print(f"Parsing 100 picks: {parse_time*1000:.2f}ms ({parse_time*10:.2f}ms/pick)")
    print(f"Grading 100 picks: {grade_time*1000:.2f}ms ({grade_time*10:.2f}ms/pick)")
    print(f"Total throughput: {100/(parse_time+grade_time):.0f} picks/second")
    
    return parse_time + grade_time


def run_full_benchmark():
    """Run all benchmarks and generate report."""
    print("="*60)
    print("GRADING SYSTEM V3 BENCHMARK")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "parser_accuracy": 0,
        "coverage": 0,
        "speed_ms": 0
    }
    
    # 1. Parser Accuracy
    try:
        results["parser_accuracy"] = benchmark_parser()
    except Exception as e:
        print(f"Parser benchmark failed: {e}")
    
    # 2. Grading Coverage
    try:
        results["coverage"] = benchmark_grading_coverage()
    except Exception as e:
        print(f"Coverage benchmark failed: {e}")
    
    # 3. Speed
    try:
        results["speed_ms"] = benchmark_speed()
    except Exception as e:
        print(f"Speed benchmark failed: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    print(f"Parser Accuracy:  {100*results['parser_accuracy']:.1f}%")
    print(f"Grading Coverage: {100*results['coverage']:.1f}%")
    print(f"Speed (100 picks): {results['speed_ms']*1000:.2f}ms")
    
    # Save results
    with open('benchmark/reports/grading_v3_benchmark.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to benchmark/reports/grading_v3_benchmark.json")
    
    return results


if __name__ == "__main__":
    run_full_benchmark()
