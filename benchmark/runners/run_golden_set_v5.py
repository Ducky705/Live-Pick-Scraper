"""
Golden Set v5 Benchmark Runner
===============================
Feeds each golden set entry through the full extraction pipeline (prompt builder → AI → decoder)
and compares AI output against expected picks.

Usage:
    python benchmark/runners/run_golden_set_v5.py [--provider groq|gemini|openrouter] [--limit N]
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load config first (triggers load_dotenv and sets up API keys)
import src.config  # noqa: F401

from src.prompts.core import compress_raw_data, get_reasoning_extraction_prompt
from src.prompts.decoder import normalize_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GOLDEN_SET_PATH = os.path.join("benchmark", "dataset", "golden_set_v5.json")
RESULTS_DIR = os.path.join("benchmark", "reports")


def call_ai_provider(prompt: str, provider: str = "groq") -> str | None:
    """Send prompt to AI provider and get response."""
    try:
        if provider == "groq":
            from src.groq_client import groq_text_completion
            return groq_text_completion(prompt)
        elif provider == "gemini":
            from src.gemini_client import gemini_text_completion
            return gemini_text_completion(prompt)
        elif provider == "openrouter":
            from src.openrouter_client import openrouter_completion
            return openrouter_completion(prompt)
        else:
            logger.error(f"Unknown provider: {provider}")
            return None
    except Exception as e:
        logger.error(f"AI call failed ({provider}): {e}")
        return None


def compare_picks(expected: list[dict], actual: list[dict]) -> dict:
    """
    Compare expected picks against actual extracted picks.
    Returns a match report with per-pick results.
    """
    results = {
        "expected_count": len(expected),
        "actual_count": len(actual),
        "matched": 0,
        "missed": 0,
        "extra": 0,
        "details": [],
    }

    # Track which actual picks were matched
    matched_actual = set()

    for exp in expected:
        exp_sel = (exp.get("selection") or "").lower().strip()
        exp_type = (exp.get("bet_type") or "").lower().strip()
        best_match = None
        best_score = 0

        for i, act in enumerate(actual):
            if i in matched_actual:
                continue

            act_sel = (act.get("pick") or act.get("selection") or "").lower().strip()
            act_type = (act.get("type") or act.get("bet_type") or "").lower().strip()

            # Score: selection similarity + type match
            score = 0

            # Check selection match (fuzzy)
            if exp_sel and act_sel:
                # Extract key parts for matching
                exp_team = exp_sel.split()[0] if exp_sel else ""
                act_team = act_sel.split()[0] if act_sel else ""

                if exp_sel == act_sel:
                    score += 3
                elif exp_team in act_sel or act_team in exp_sel:
                    score += 2
                elif any(word in act_sel for word in exp_sel.split() if len(word) > 3):
                    score += 1

            # Check type match
            type_map = {
                "spread": "spread",
                "moneyline": "moneyline",
                "total": "total",
                "player prop": "player prop",
                "parlay": "parlay",
            }
            exp_type_norm = type_map.get(exp_type, exp_type)
            act_type_norm = type_map.get(act_type, act_type)
            if exp_type_norm == act_type_norm:
                score += 1

            if score > best_score:
                best_score = score
                best_match = (i, act)

        if best_match and best_score >= 2:
            matched_actual.add(best_match[0])
            act = best_match[1]
            results["matched"] += 1
            results["details"].append({
                "status": "MATCH",
                "expected": exp.get("selection"),
                "actual": act.get("pick") or act.get("selection"),
                "exp_type": exp.get("bet_type"),
                "act_type": act.get("type") or act.get("bet_type"),
                "score": best_score,
            })
        else:
            results["missed"] += 1
            results["details"].append({
                "status": "MISS",
                "expected": exp.get("selection"),
                "actual": None,
                "exp_type": exp.get("bet_type"),
            })

    # Count extra picks (actual but not matched)
    for i, act in enumerate(actual):
        if i not in matched_actual:
            results["extra"] += 1
            results["details"].append({
                "status": "EXTRA",
                "expected": None,
                "actual": act.get("pick") or act.get("selection"),
                "act_type": act.get("type") or act.get("bet_type"),
            })

    return results


def run_benchmark(provider: str = "groq", limit: int = 0):
    """Run the golden set benchmark."""
    if not os.path.exists(GOLDEN_SET_PATH):
        logger.error(f"Golden set not found at {GOLDEN_SET_PATH}")
        return

    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        golden = json.load(f)

    entries = golden.get("entries", [])
    if limit > 0:
        entries = entries[:limit]

    logger.info(f"Running Golden Set v5 Benchmark ({len(entries)} entries, provider: {provider})")
    print("=" * 70)

    overall = {
        "total_expected": 0,
        "total_matched": 0,
        "total_missed": 0,
        "total_extra": 0,
        "total_actual": 0,
        "entry_results": [],
    }

    for idx, entry in enumerate(entries):
        msg_id = entry["message_id"]
        text = entry["text"]
        expected = entry["expected_picks"]

        print(f"\n{'─' * 70}")
        print(f"[{idx+1}/{len(entries)}] {msg_id} | Expected: {len(expected)} picks")
        print(f"  Text: {text[:120]}{'...' if len(text) > 120 else ''}")

        # Build the message dict as the pipeline expects
        msg = {
            "id": msg_id,
            "text": text,
            "ocr_text": "",
            "ocr_texts": [],
        }

        # Generate prompt
        compressed = compress_raw_data([msg])
        prompt = get_reasoning_extraction_prompt(
            compressed,
            current_date="2026-02-14",
        )

        # Call AI
        t0 = time.time()
        raw_response = call_ai_provider(prompt, provider)
        elapsed = time.time() - t0

        if not raw_response:
            print(f"  ❌ AI returned no response ({elapsed:.1f}s)")
            overall["total_expected"] += len(expected)
            overall["total_missed"] += len(expected)
            overall["entry_results"].append({
                "msg_id": msg_id,
                "status": "AI_FAILURE",
                "expected_count": len(expected),
                "matched": 0,
            })
            continue

        # Decode response
        valid_ids = [msg_id]
        decoded_picks = normalize_response(
            raw_response,
            expand=True,
            valid_message_ids=valid_ids,
        )

        print(f"  AI response ({elapsed:.1f}s): {len(decoded_picks)} picks extracted")

        # Compare
        comparison = compare_picks(expected, decoded_picks)
        overall["total_expected"] += comparison["expected_count"]
        overall["total_actual"] += comparison["actual_count"]
        overall["total_matched"] += comparison["matched"]
        overall["total_missed"] += comparison["missed"]
        overall["total_extra"] += comparison["extra"]

        # Print per-pick results
        for detail in comparison["details"]:
            if detail["status"] == "MATCH":
                print(f"  ✅ {detail['expected']} → {detail['actual']} [{detail['exp_type']}→{detail['act_type']}]")
            elif detail["status"] == "MISS":
                print(f"  ❌ MISSED: {detail['expected']} [{detail['exp_type']}]")
            elif detail["status"] == "EXTRA":
                print(f"  ⚠️  EXTRA: {detail['actual']} [{detail['act_type']}]")

        overall["entry_results"].append({
            "msg_id": msg_id,
            "expected_count": comparison["expected_count"],
            "actual_count": comparison["actual_count"],
            "matched": comparison["matched"],
            "missed": comparison["missed"],
            "extra": comparison["extra"],
            "elapsed_s": round(elapsed, 1),
            "details": comparison["details"],
        })

        # Rate limit between entries
        time.sleep(0.5)

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("GOLDEN SET v5 BENCHMARK RESULTS")
    print("=" * 70)

    recall = (overall["total_matched"] / overall["total_expected"] * 100) if overall["total_expected"] > 0 else 0
    precision = (overall["total_matched"] / overall["total_actual"] * 100) if overall["total_actual"] > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    print(f"  Provider:   {provider}")
    print(f"  Entries:    {len(entries)}")
    print(f"  Expected:   {overall['total_expected']} picks")
    print(f"  Extracted:  {overall['total_actual']} picks")
    print(f"  Matched:    {overall['total_matched']} picks")
    print(f"  Missed:     {overall['total_missed']} picks")
    print(f"  Extra:      {overall['total_extra']} picks")
    print(f"")
    print(f"  RECALL:     {recall:.1f}%")
    print(f"  PRECISION:  {precision:.1f}%")
    print(f"  F1 SCORE:   {f1:.1f}%")
    print("=" * 70)

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(RESULTS_DIR, f"golden_v5_{provider}_{ts}.json")
    report = {
        "provider": provider,
        "timestamp": ts,
        "summary": {
            "entries": len(entries),
            "total_expected": overall["total_expected"],
            "total_extracted": overall["total_actual"],
            "total_matched": overall["total_matched"],
            "total_missed": overall["total_missed"],
            "total_extra": overall["total_extra"],
            "recall_pct": round(recall, 1),
            "precision_pct": round(precision, 1),
            "f1_pct": round(f1, 1),
        },
        "entries": overall["entry_results"],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Results saved to {out_path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Golden Set v5 Benchmark")
    parser.add_argument("--provider", type=str, default="groq", choices=["groq", "gemini", "openrouter"])
    parser.add_argument("--limit", type=int, default=0, help="Limit number of entries (0=all)")
    args = parser.parse_args()

    run_benchmark(args.provider, args.limit)
