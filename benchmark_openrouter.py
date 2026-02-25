import json
import logging
import os
import sys
import time

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.extraction_pipeline import ExtractionPipeline
logging.basicConfig(level=logging.INFO, format='%(message)s')

def run_benchmark():
    ocr_file = r"benchmark\dataset\ocr_golden_set.json"
    parsing_file = r"benchmark\dataset\parsing_golden_set.json"

    with open(ocr_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)

    with open(parsing_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    messages = []
    for msg_key, text in ocr_data.items():
        msg_id = msg_key.replace("message_", "")
        messages.append({
            "id": msg_id,
            "text": text,
            "ocr_text": "",
            "channel_name": "Benchmark_Channel",
            "date": "2026-02-14",
            "source": "Benchmark"
        })

    print(f"Prepared {len(messages)} messages for processing.")
    
    extracted_picks = ExtractionPipeline.run(
        messages=messages,
        target_date="2026-02-14",
        batch_size=1, 
        strategy="groq"
    )
    
    # Write Out
    with open("stepfun_results.json", "w", encoding="utf-8") as out_f:
        json.dump(extracted_picks, out_f)
    print("Saved stepfun_results.json successfully!")

    # Calculate
    import recalculate_scores
    res = recalculate_scores.grade_file("stepfun_results.json", ground_truth)
    print("\n" + "="*50)
    print("STEPFUN RESULTS")
    print("="*50 + "\n")
    print(f"Recall:    {res['recall']:.2f}% ({res['matches']}/276 expected - True Misses: {res['misses']})")
    print(f"Precision: {res['precision']:.2f}% ({res['matches']}/{res['total_extracted']} extracted)")
    print(f"F1 Score:  {res['f1']:.2f}%")

if __name__ == "__main__":
    run_benchmark()
