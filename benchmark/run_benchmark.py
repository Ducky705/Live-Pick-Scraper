#!/usr/bin/env python
# run_benchmark.py
"""
Model Benchmark CLI - Test OpenRouter AI models on pick extraction accuracy.

Usage:
    python run_benchmark.py                         # Run all 38 models
    python run_benchmark.py --quick                 # Quick test (2 models, 3 cases, 1 run)
    python run_benchmark.py --models "google/*"     # Pattern match models
    python run_benchmark.py --runs 5                # Custom runs per case
    python run_benchmark.py --cases 5               # Limit test cases
    python run_benchmark.py --report-only           # Just regenerate HTML report
"""

import argparse
import fnmatch
import sys
from pathlib import Path

# Add parent's parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from benchmark.config import MODELS_TO_TEST, QUICK_TEST_MODELS, DEFAULT_RUNS
from benchmark.runner import run_benchmark, BenchmarkRunner
from benchmark.report import generate_report


def filter_models(pattern: str) -> list:
    """Filter models by glob pattern."""
    if not pattern:
        return MODELS_TO_TEST
    return [m for m in MODELS_TO_TEST if fnmatch.fnmatch(m, pattern)]


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark OpenRouter AI models on pick extraction accuracy",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--models", "-m",
        type=str,
        default=None,
        help="Glob pattern to filter models (e.g., 'google/*', '*mistral*')"
    )
    
    parser.add_argument(
        "--runs", "-r",
        type=int,
        default=DEFAULT_RUNS,
        help=f"Number of runs per test case for variance (default: {DEFAULT_RUNS})"
    )
    
    parser.add_argument(
        "--cases", "-c",
        type=int,
        default=None,
        help="Limit number of test cases to run (default: all)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="benchmark_results",
        help="Output directory for results (default: benchmark_results)"
    )
    
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick test: 2 models, 3 cases, 1 run"
    )
    
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only regenerate HTML report from existing results"
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all available models and exit"
    )
    
    args = parser.parse_args()
    
    # List models
    if args.list_models:
        print(f"📋 Available models ({len(MODELS_TO_TEST)}):\n")
        for i, m in enumerate(MODELS_TO_TEST, 1):
            print(f"  {i:2}. {m}")
        return
    
    # Report only mode
    if args.report_only:
        print("📊 Regenerating report from existing results...")
        try:
            report_path = generate_report(
                f"{args.output}/raw_results.json",
                f"{args.output}/report.html"
            )
            print(f"✅ Report saved to: {report_path}")
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            print("   Run the benchmark first to generate results.")
            sys.exit(1)
        return
    
    # Determine models to test
    if args.quick:
        models = QUICK_TEST_MODELS
        runs = 1
        cases = 3
        print("⚡ Quick mode: 2 models, 3 cases, 1 run each")
    else:
        models = filter_models(args.models) if args.models else MODELS_TO_TEST
        runs = args.runs
        cases = args.cases
    
    if not models:
        print(f"❌ No models match pattern: {args.models}")
        print("   Use --list-models to see available models")
        sys.exit(1)
    
    print(f"\n🚀 Model Benchmark")
    print(f"   Models: {len(models)}")
    print(f"   Runs per case: {runs}")
    print(f"   Test cases: {cases or 'all'}")
    print(f"   Output: {args.output}/")
    print()
    
    # Run benchmark
    try:
        results = run_benchmark(
            models=models,
            runs=runs,
            cases=cases,
            output_dir=args.output
        )
        
        # Generate report
        print("\n📊 Generating HTML report...")
        report_path = generate_report(
            f"{args.output}/raw_results.json",
            f"{args.output}/report.html"
        )
        
        # Print top 5
        print("\n🏆 Top 5 Models by Composite Score:")
        print("-" * 60)
        
        from benchmark.metrics import calculate_composite_score
        ranked = sorted(results.items(), key=lambda x: calculate_composite_score(x[1]), reverse=True)
        
        for i, (model, result) in enumerate(ranked[:5], 1):
            score = calculate_composite_score(result)
            print(f"  {i}. {model}")
            print(f"     Score: {score:.2f} | F1: {result.avg_f1:.3f} | Time: {result.avg_response_time_ms:.0f}ms")
        
        print(f"\n✅ Full report: {report_path.absolute()}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted. Partial results may be saved.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
