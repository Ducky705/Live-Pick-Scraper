#!/usr/bin/env python3
"""
Golden Set Evaluation Harness
=============================
Evaluates AI parser accuracy against annotated ground-truth data.

Usage:
    python tools/evaluate_golden_set.py golden_set.jsonl --model gpt-4o

Metrics:
- Field accuracy (league, type, pick, odds, subject, market, line, prop_side)
- Pick detection rate (found vs missed)
- False positive rate (hallucinated picks)
"""

import argparse
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from difflib import SequenceMatcher

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class FieldMetrics:
    """Tracks accuracy for a single field."""
    correct: int = 0
    total: int = 0
    errors: list = field(default_factory=list)
    
    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total > 0 else 0.0
    
    def record(self, expected: any, actual: any, context: str = ""):
        self.total += 1
        if self._compare(expected, actual):
            self.correct += 1
        else:
            self.errors.append({
                "expected": expected,
                "actual": actual,
                "context": context
            })
    
    def _compare(self, expected: any, actual: any) -> bool:
        """Flexible comparison with normalization."""
        if expected is None and actual is None:
            return True
        if expected is None or actual is None:
            return False
        
        # Normalize strings
        if isinstance(expected, str) and isinstance(actual, str):
            return self._normalize(expected) == self._normalize(actual)
        
        # Numeric comparison with tolerance
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return abs(expected - actual) < 0.01
        
        return expected == actual
    
    def _normalize(self, s: str) -> str:
        """Normalize string for comparison."""
        return s.lower().strip().replace("  ", " ")


@dataclass  
class EvaluationResult:
    """Aggregated evaluation results."""
    total_images: int = 0
    total_expected_picks: int = 0
    total_actual_picks: int = 0
    true_positives: int = 0  # Matched picks
    false_positives: int = 0  # Extra picks not in expected
    false_negatives: int = 0  # Missing picks
    
    # Field-level metrics
    league: FieldMetrics = field(default_factory=FieldMetrics)
    bet_type: FieldMetrics = field(default_factory=FieldMetrics)
    pick: FieldMetrics = field(default_factory=FieldMetrics)
    odds: FieldMetrics = field(default_factory=FieldMetrics)
    subject: FieldMetrics = field(default_factory=FieldMetrics)
    market: FieldMetrics = field(default_factory=FieldMetrics)
    line: FieldMetrics = field(default_factory=FieldMetrics)
    prop_side: FieldMetrics = field(default_factory=FieldMetrics)
    
    @property
    def precision(self) -> float:
        """Of picks we returned, how many were correct?"""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0
    
    @property
    def recall(self) -> float:
        """Of expected picks, how many did we find?"""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0
    
    @property
    def f1(self) -> float:
        """Harmonic mean of precision and recall."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)


def normalize_pick(pick: str) -> str:
    """Normalize pick string for matching."""
    if not pick:
        return ""
    # Lowercase, strip, remove extra spaces
    s = pick.lower().strip()
    s = " ".join(s.split())
    # Remove common variations
    s = s.replace("los angeles ", "la ")
    s = s.replace("new york ", "ny ")
    s = s.replace("golden state ", "gs ")
    return s


def similarity(s1: str, s2: str) -> float:
    """Calculate string similarity (0-1)."""
    return SequenceMatcher(None, normalize_pick(s1), normalize_pick(s2)).ratio()


def match_picks(expected: list[dict], actual: list[dict], threshold: float = 0.75) -> tuple[list, list, list]:
    """
    Match actual picks to expected picks.
    Returns: (matched_pairs, unmatched_expected, unmatched_actual)
    """
    matched = []
    unmatched_expected = list(expected)
    unmatched_actual = list(actual)
    
    for exp in expected:
        exp_pick = exp.get("pick", "")
        best_match = None
        best_score = 0
        
        for act in unmatched_actual:
            act_pick = act.get("p") or act.get("pick", "")
            score = similarity(exp_pick, act_pick)
            
            # Also check if league + type match for bonus
            if exp.get("league") == (act.get("lg") or act.get("league")):
                score += 0.1
            if exp.get("type") == (act.get("ty") or act.get("type")):
                score += 0.1
            
            if score > best_score:
                best_score = score
                best_match = act
        
        if best_match and best_score >= threshold:
            matched.append((exp, best_match))
            unmatched_expected.remove(exp)
            unmatched_actual.remove(best_match)
    
    return matched, unmatched_expected, unmatched_actual


def evaluate_image(expected_picks: list[dict], actual_picks: list[dict], result: EvaluationResult):
    """Evaluate parser output for a single image."""
    result.total_images += 1
    result.total_expected_picks += len(expected_picks)
    result.total_actual_picks += len(actual_picks)
    
    # Match picks
    matched, missed, extra = match_picks(expected_picks, actual_picks)
    
    result.true_positives += len(matched)
    result.false_negatives += len(missed)
    result.false_positives += len(extra)
    
    # Evaluate field accuracy for matched picks
    for exp, act in matched:
        ctx = exp.get("pick", "")[:50]
        
        # Core fields
        result.league.record(
            exp.get("league"),
            act.get("lg") or act.get("league"),
            ctx
        )
        result.bet_type.record(
            exp.get("type"),
            act.get("ty") or act.get("type"),
            ctx
        )
        result.pick.record(
            exp.get("pick"),
            act.get("p") or act.get("pick"),
            ctx
        )
        result.odds.record(
            exp.get("odds"),
            act.get("od") or act.get("odds"),
            ctx
        )
        
        # Structured fields
        result.subject.record(
            exp.get("subject"),
            act.get("sub") or act.get("subject"),
            ctx
        )
        result.market.record(
            exp.get("market"),
            act.get("mkt") or act.get("market"),
            ctx
        )
        result.line.record(
            exp.get("line"),
            act.get("ln") or act.get("line"),
            ctx
        )
        result.prop_side.record(
            exp.get("prop_side"),
            act.get("side") or act.get("prop_side"),
            ctx
        )


def load_golden_set(path: Path) -> list[dict]:
    """Load golden set from JSONL file."""
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def print_report(result: EvaluationResult, verbose: bool = False):
    """Print evaluation report."""
    print("\n" + "=" * 60)
    print("GOLDEN SET EVALUATION REPORT")
    print("=" * 60)
    
    print(f"\n{'DETECTION METRICS':-^60}")
    print(f"  Images evaluated:     {result.total_images}")
    print(f"  Expected picks:       {result.total_expected_picks}")
    print(f"  Returned picks:       {result.total_actual_picks}")
    print(f"  Matched (TP):         {result.true_positives}")
    print(f"  Missed (FN):          {result.false_negatives}")
    print(f"  Extra (FP):           {result.false_positives}")
    print(f"  Precision:            {result.precision:.1%}")
    print(f"  Recall:               {result.recall:.1%}")
    print(f"  F1 Score:             {result.f1:.1%}")
    
    print(f"\n{'FIELD ACCURACY (on matched picks)':-^60}")
    fields = [
        ("League", result.league),
        ("Type", result.bet_type),
        ("Pick", result.pick),
        ("Odds", result.odds),
        ("Subject", result.subject),
        ("Market", result.market),
        ("Line", result.line),
        ("Prop Side", result.prop_side),
    ]
    
    for name, metrics in fields:
        if metrics.total > 0:
            bar = "#" * int(metrics.accuracy * 20)
            print(f"  {name:<12} {metrics.accuracy:>6.1%} ({metrics.correct}/{metrics.total}) [{bar:<20}]")
    
    if verbose:
        print(f"\n{'ERRORS (sample)':-^60}")
        for name, metrics in fields:
            if metrics.errors:
                print(f"\n{name}:")
                for err in metrics.errors[:3]:
                    print(f"  Expected: {err['expected']}")
                    print(f"  Actual:   {err['actual']}")
                    print(f"  Context:  {err['context']}")
                    print()


def main():
    parser = argparse.ArgumentParser(description="Evaluate AI parser against golden set")
    parser.add_argument("golden_set", type=Path, help="Path to golden_set.jsonl")
    parser.add_argument("--predictions", type=Path, help="Path to predictions JSONL (if already generated)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed errors")
    parser.add_argument("--output", "-o", type=Path, help="Save JSON report to file")
    args = parser.parse_args()
    
    if not args.golden_set.exists():
        print(f"Error: Golden set file not found: {args.golden_set}")
        sys.exit(1)
    
    # Load golden set
    golden_items = load_golden_set(args.golden_set)
    print(f"Loaded {len(golden_items)} items from golden set")
    
    # Load or generate predictions
    if args.predictions:
        if not args.predictions.exists():
            print(f"Error: Predictions file not found: {args.predictions}")
            sys.exit(1)
        predictions = load_golden_set(args.predictions)
        print(f"Loaded {len(predictions)} predictions")
    else:
        # TODO: Run parser on images
        print("Error: --predictions required (auto-generation not yet implemented)")
        print("\nTo generate predictions, run the parser on golden set images:")
        print("  1. Extract image paths from golden_set.jsonl")
        print("  2. Run your AI parser on each image")
        print("  3. Save results as JSONL with same image_path keys")
        sys.exit(1)
    
    # Build lookup for predictions by image path
    pred_lookup = {}
    for item in predictions:
        path = item.get("image_path", "")
        if path not in pred_lookup:
            pred_lookup[path] = []
        picks = item.get("picks", [])
        if isinstance(picks, list):
            pred_lookup[path].extend(picks)
    
    # Evaluate
    result = EvaluationResult()
    
    for item in golden_items:
        image_path = item.get("image_path", "")
        expected = item.get("expected_picks", [])
        actual = pred_lookup.get(image_path, [])
        
        evaluate_image(expected, actual, result)
    
    # Print report
    print_report(result, verbose=args.verbose)
    
    # Save JSON report
    if args.output:
        report = {
            "total_images": result.total_images,
            "total_expected": result.total_expected_picks,
            "total_actual": result.total_actual_picks,
            "precision": result.precision,
            "recall": result.recall,
            "f1": result.f1,
            "field_accuracy": {
                "league": result.league.accuracy,
                "type": result.bet_type.accuracy,
                "pick": result.pick.accuracy,
                "odds": result.odds.accuracy,
                "subject": result.subject.accuracy,
                "market": result.market.accuracy,
                "line": result.line.accuracy,
                "prop_side": result.prop_side.accuracy,
            }
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
