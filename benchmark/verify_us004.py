import json
import os
import sys
import logging

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.extraction_pipeline import ExtractionPipeline
import benchmark.run_autotest as autotest


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    ocr_path = os.path.join(BASE_DIR, "benchmark", "dataset", "ocr_golden_set.json")
    gold_path = os.path.join(BASE_DIR, "benchmark", "dataset", "parsing_golden_set.json")

    with open(ocr_path, "r", encoding="utf-8") as f:
        ocr_data = json.load(f)

    with open(gold_path, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    messages = []
    for img_name, text in ocr_data.items():
        messages.append(
            {"id": img_name, "text": "", "ocr_text": text, "author": f"Capper_{img_name}", "date": "2026-01-24"}
        )

    print(f"Running pipeline on {len(messages)} OCR samples...")
    picks = ExtractionPipeline.run(messages, target_date="2026-01-24")

    # Adapt gold_data to autotest format
    judgments = []
    for img_name, expected_picks in gold_data.items():
        picks_list = []
        for p in expected_picks:
            picks_list.append(p.get("p", ""))

        judgments.append(
            {
                "message_id": img_name,
                "has_picks": len(picks_list) > 0,
                "picks": picks_list,
                "capper": f"Capper_{img_name}",
            }
        )

    comparison = autotest.run_comparison({"judgments": judgments}, picks)
    autotest.print_report(comparison)

    acc = comparison["metrics"]["recall"]
    print(f"\nFINAL RECALL: {acc}%")

    if acc >= 95.0:
        print("SUCCESS: Accuracy is 95% or higher!")
    else:
        print("FAILURE: Accuracy is below 95%.")


if __name__ == "__main__":
    main()
