"""
Auto Test Runner - Compare Scraper Output vs Judge Golden Set
==============================================================
Compares the scraper's parsed picks against the Judge's ground truth
to identify accuracy issues, false negatives, and false positives.

This enables data-driven optimization without manual review.

Usage:
    python -m benchmark.run_autotest [--golden FILE] [--scraper FILE]
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from collections import defaultdict

# Setup paths
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def similarity(a: str, b: str) -> float:
    """Calculate string similarity ratio (0-1)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def normalize_pick(pick: str) -> str:
    """Normalize a pick string for comparison."""
    if not pick:
        return ""
    # Remove common noise
    normalized = pick.lower().strip()
    # Remove odds patterns
    normalized = normalized.replace("-110", "").replace("+100", "")
    # Remove extra whitespace
    normalized = " ".join(normalized.split())
    return normalized


def find_best_match(pick: str, candidates: List[str], threshold: float = 0.6) -> Optional[Tuple[str, float]]:
    """Find the best matching pick from candidates."""
    if not pick or not candidates:
        return None
    
    normalized_pick = normalize_pick(pick)
    best_match = None
    best_score = 0.0
    
    for candidate in candidates:
        normalized_candidate = normalize_pick(candidate)
        score = similarity(normalized_pick, normalized_candidate)
        if score > best_score:
            best_score = score
            best_match = candidate
    
    if best_score >= threshold:
        return (best_match, best_score)
    return None


def load_golden_set(path: str) -> Dict:
    """Load the Judge's golden set."""
    if not os.path.exists(path):
        logging.error(f"Golden set not found: {path}")
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def load_scraper_output(path: str) -> List[Dict]:
    """Load the scraper's parsed picks."""
    if not os.path.exists(path):
        logging.error(f"Scraper output not found: {path}")
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both direct list and wrapped format
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        # Try common keys: graded, picks, graded_picks
        return data.get('graded', data.get('picks', data.get('graded_picks', [])))
    
    return []


def build_message_id_map(scraper_picks: List[Dict]) -> Dict[Any, List[Dict]]:
    """Group scraper picks by message_id."""
    by_message = defaultdict(list)
    for pick in scraper_picks:
        msg_id = pick.get('message_id') or pick.get('id')
        if msg_id:
            by_message[msg_id].append(pick)
    return dict(by_message)


def compare_message(
    judgment: Dict, 
    scraper_picks: List[Dict]
) -> Dict:
    """
    Compare Judge's judgment for a message against scraper's picks.
    Returns detailed comparison results.
    """
    msg_id = judgment.get('message_id')
    judge_has_picks = judgment.get('has_picks')
    judge_picks = judgment.get('picks', [])
    judge_capper = judgment.get('capper')
    
    # Build list of scraper pick strings for this message
    scraper_pick_strs = []
    scraper_cappers = set()
    for sp in scraper_picks:
        pick_val = sp.get('pick') or sp.get('pick_value') or sp.get('p')
        if pick_val:
            scraper_pick_strs.append(pick_val)
        capper = sp.get('capper_name') or sp.get('capper') or sp.get('cn')
        if capper:
            scraper_cappers.add(capper)
    
    result = {
        "message_id": msg_id,
        "judge_has_picks": judge_has_picks,
        "judge_picks": judge_picks,
        "judge_capper": judge_capper,
        "scraper_picks": scraper_pick_strs,
        "scraper_cappers": list(scraper_cappers),
        "matched_picks": [],
        "false_negatives": [],  # Judge found, scraper missed
        "false_positives": [],  # Scraper found, Judge didn't
        "status": "unknown"
    }
    
    # Case 1: Judge says no picks
    if judge_has_picks is False:
        if len(scraper_pick_strs) > 0:
            result["status"] = "false_positive"
            result["false_positives"] = scraper_pick_strs
        else:
            result["status"] = "true_negative"
        return result
    
    # Case 2: Judge failed (None)
    if judge_has_picks is None:
        result["status"] = "judge_failed"
        return result
    
    # Case 3: Judge found picks
    if judge_has_picks is True:
        if len(scraper_pick_strs) == 0:
            result["status"] = "false_negative"
            result["false_negatives"] = judge_picks
            return result
        
        # Match picks
        unmatched_judge = list(judge_picks)
        unmatched_scraper = list(scraper_pick_strs)
        matched = []
        
        for jp in judge_picks:
            match = find_best_match(jp, unmatched_scraper, threshold=0.5)
            if match:
                matched.append({"judge": jp, "scraper": match[0], "similarity": match[1]})
                if match[0] in unmatched_scraper:
                    unmatched_scraper.remove(match[0])
                if jp in unmatched_judge:
                    unmatched_judge.remove(jp)
        
        result["matched_picks"] = matched
        result["false_negatives"] = unmatched_judge
        result["false_positives"] = unmatched_scraper
        
        if len(unmatched_judge) == 0 and len(unmatched_scraper) == 0:
            result["status"] = "perfect_match"
        elif len(unmatched_judge) > 0 and len(unmatched_scraper) > 0:
            result["status"] = "partial_match"
        elif len(unmatched_judge) > 0:
            result["status"] = "missed_picks"
        else:
            result["status"] = "extra_picks"
        
        return result
    
    return result


def run_comparison(golden_set: Dict, scraper_picks: List[Dict]) -> Dict:
    """
    Run full comparison between golden set and scraper output.
    Returns comprehensive accuracy report.
    """
    judgments = golden_set.get('judgments', [])
    scraper_by_msg = build_message_id_map(scraper_picks)
    
    results = {
        "total_messages": len(judgments),
        "comparisons": [],
        "summary": {
            "perfect_match": 0,
            "partial_match": 0,
            "missed_picks": 0,
            "extra_picks": 0,
            "false_negative": 0,
            "false_positive": 0,
            "true_negative": 0,
            "judge_failed": 0,
        },
        "all_false_negatives": [],  # Critical: picks we missed entirely
        "all_false_positives": [],  # Noise we incorrectly extracted
    }
    
    for judgment in judgments:
        msg_id = judgment.get('message_id')
        scraper_for_msg = scraper_by_msg.get(msg_id, [])
        
        comparison = compare_message(judgment, scraper_for_msg)
        results["comparisons"].append(comparison)
        
        # Update summary
        status = comparison.get("status", "unknown")
        if status in results["summary"]:
            results["summary"][status] += 1
        
        # Collect all false negatives/positives
        for fn in comparison.get("false_negatives", []):
            results["all_false_negatives"].append({
                "message_id": msg_id,
                "pick": fn,
                "judge_capper": comparison.get("judge_capper")
            })
        
        for fp in comparison.get("false_positives", []):
            results["all_false_positives"].append({
                "message_id": msg_id,
                "pick": fp
            })
    
    # Calculate accuracy metrics
    total_with_picks = sum(1 for j in judgments if j.get('has_picks'))
    total_correct = results["summary"]["perfect_match"] + results["summary"]["true_negative"]
    total_evaluated = len(judgments) - results["summary"]["judge_failed"]
    
    results["metrics"] = {
        "accuracy": round(total_correct / max(total_evaluated, 1) * 100, 2),
        "recall": round(
            (total_with_picks - len(results["all_false_negatives"])) / max(total_with_picks, 1) * 100, 2
        ),
        "precision": round(
            len([c for c in results["comparisons"] if c["matched_picks"]]) / 
            max(len([c for c in results["comparisons"] if c["scraper_picks"]]), 1) * 100, 2
        ),
        "total_picks_expected": sum(len(j.get('picks', [])) for j in judgments if j.get('has_picks')),
        "total_picks_found": sum(len(c.get('scraper_picks', [])) for c in results["comparisons"]),
        "total_missed": len(results["all_false_negatives"]),
        "total_false_positives": len(results["all_false_positives"]),
    }
    
    return results


def print_report(results: Dict):
    """Print a human-readable accuracy report."""
    print("\n" + "=" * 60)
    print("SCRAPER ACCURACY REPORT")
    print("=" * 60)
    
    summary = results.get("summary", {})
    metrics = results.get("metrics", {})
    
    print(f"\nTotal Messages Analyzed: {results['total_messages']}")
    print(f"\nStatus Breakdown:")
    print(f"  Perfect Match:    {summary.get('perfect_match', 0)}")
    print(f"  Partial Match:    {summary.get('partial_match', 0)}")
    print(f"  Missed Picks:     {summary.get('missed_picks', 0)}")
    print(f"  Extra Picks:      {summary.get('extra_picks', 0)}")
    print(f"  False Negative:   {summary.get('false_negative', 0)} (HAD picks but scraper found NONE)")
    print(f"  False Positive:   {summary.get('false_positive', 0)} (NO picks but scraper found some)")
    print(f"  True Negative:    {summary.get('true_negative', 0)}")
    print(f"  Judge Failed:     {summary.get('judge_failed', 0)}")
    
    print(f"\nAccuracy Metrics:")
    print(f"  Overall Accuracy: {metrics.get('accuracy', 0)}%")
    print(f"  Recall:           {metrics.get('recall', 0)}% (of real picks, how many did we find?)")
    print(f"  Precision:        {metrics.get('precision', 0)}% (of found picks, how many are real?)")
    print(f"  Total Expected:   {metrics.get('total_picks_expected', 0)} picks")
    print(f"  Total Found:      {metrics.get('total_picks_found', 0)} picks")
    print(f"  Total MISSED:     {metrics.get('total_missed', 0)} picks")
    print(f"  False Positives:  {metrics.get('total_false_positives', 0)} picks")
    
    # Show sample false negatives (most critical issue)
    false_negs = results.get("all_false_negatives", [])
    if false_negs:
        print(f"\n" + "-" * 60)
        print("CRITICAL: Sample MISSED PICKS (False Negatives)")
        print("-" * 60)
        for fn in false_negs[:10]:
            print(f"  MSG {fn['message_id']}: \"{fn['pick']}\" (Capper: {fn.get('judge_capper', 'Unknown')})")
        if len(false_negs) > 10:
            print(f"  ... and {len(false_negs) - 10} more missed picks")
    
    # Show sample false positives
    false_pos = results.get("all_false_positives", [])
    if false_pos:
        print(f"\n" + "-" * 60)
        print("WARNING: Sample FALSE POSITIVES (Noise)")
        print("-" * 60)
        for fp in false_pos[:5]:
            print(f"  MSG {fp['message_id']}: \"{fp['pick']}\"")
    
    print("\n" + "=" * 60)


def save_report(results: Dict, output_path: str):
    """Save full report to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logging.info(f"Full report saved to {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare scraper output vs Judge golden set")
    parser.add_argument("--golden", type=str, default=None, help="Path to golden set JSON")
    parser.add_argument("--scraper", type=str, default=None, help="Path to scraper output JSON")
    parser.add_argument("--output", type=str, default=None, help="Path to save detailed report")
    args = parser.parse_args()
    
    # Default paths
    golden_path = args.golden or os.path.join(BASE_DIR, "benchmark", "reports", "auto_golden_set.json")
    scraper_path = args.scraper or os.path.join(BASE_DIR, "cache", "graded_picks.json")
    output_path = args.output or os.path.join(BASE_DIR, "benchmark", "reports", "accuracy_report.json")
    
    # Load data
    golden_set = load_golden_set(golden_path)
    if not golden_set:
        print("ERROR: Could not load golden set. Run 'python -m benchmark.auto_judge' first.")
        return
    
    scraper_picks = load_scraper_output(scraper_path)
    logging.info(f"Loaded {len(golden_set.get('judgments', []))} judgments and {len(scraper_picks)} scraper picks")
    
    # Run comparison
    results = run_comparison(golden_set, scraper_picks)
    
    # Output
    print_report(results)
    save_report(results, output_path)
    
    print(f"\nDetailed report saved to: {output_path}")


if __name__ == "__main__":
    main()
