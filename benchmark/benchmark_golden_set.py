import json
import logging
import os
import sys
import time
from collections import defaultdict

# Setup path to project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

from src.extraction_pipeline import ExtractionPipeline
from src.grading.engine import GraderEngine
from src.score_fetcher import fetch_scores_for_date
from src.grading.parser import PickParser

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Benchmark")

def normalize_string(s):
    if not s:
        return ""
    s = str(s).lower()
    s = s.replace("/", " ").replace("-", " ").replace(":", " ").replace("|", " ")
    s = s.replace("'", "").replace('"', "").replace("“", "").replace("”", "").replace("(", "").replace(")", "")
    s = s.replace(" vs ", " ").replace(" versus ", " ").replace(" @ ", " ").replace(" games", "")
    s = s.replace("dnb", "draw no bet")
    s = s.replace("ah", "asian handicap")
    # Normalize common abbreviations
    s = s.replace("st.", "st")
    # Handle acronym names properly (L.Samsonova to L Samsonova)
    s = s.replace(".", " ")
    # Expand common state abbreviations for matching
    import re as _re
    s = _re.sub(r'\biowa st\b', 'iowa state', s)
    s = _re.sub(r'\bnc st\b', 'nc state', s)
    s = _re.sub(r'\bohio st\b', 'ohio state', s)
    s = _re.sub(r'\bmontana st\b', 'montana state', s)
    s = _re.sub(r'\btennessee st\b', 'tennessee state', s)
    s = _re.sub(r'\bs dakota st\b', 'south dakota state', s)
    s = _re.sub(r'\bsouth dakota st\b', 'south dakota state', s)
    s = _re.sub(r'\bmiss valley st\b', 'miss valley state', s)
    s = _re.sub(r'\blowa\b', 'iowa', s)  # OCR error: lowa -> iowa
    s = _re.sub(r'\bteam total\b', 'tt', s)
    return s.strip()

def fuzzy_match(expected, actual):
    # Core fields to check
    # 1. Pick (Most important)
    exp_pick_raw = normalize_string(expected.get("p")) # 'p' from golden set compact format
    act_pick_raw = normalize_string(actual.get("pick")) # 'pick' from pipeline format

    if not exp_pick_raw or not act_pick_raw:
        return False

    # Tokenize
    exp_tokens = set(exp_pick_raw.split())
    act_tokens = set(act_pick_raw.split())

    # Remove common filler words
    stop_words = {
        "the", "a", "an", "bet", "pick", "prediction", "of", "in", "ml", "moneyline",
        "spread", "total", "over", "under", "money", "line",
        # Mascot names that cause token mismatch
        "cyclones", "wolfpack", "tigers", "hawkeyes", "gators", "ducks",
        "cowboys", "wolverines", "bobcats", "pegasus", "promy", "egis",
        "cavs", "friars", "wildcats", "bulldogs", "cardinals",
        "sonicboom", "sakers", "gunners", "phoebus",
        # Common formatting words
        "content", "win", "alternate", "games", "set", "pts", "points",
        "rebounds", "assists", "pra",
    }
    exp_tokens -= stop_words
    act_tokens -= stop_words

    # Check for name overlap (Crucial)
    intersection = exp_tokens.intersection(act_tokens)

    # Calculate overlap ratio relative to expected length
    if not exp_tokens:
        pick_match = exp_pick_raw == act_pick_raw
    else:
        ratio = len(intersection) / len(exp_tokens)
        pick_match = (ratio >= 0.5) or (exp_pick_raw in act_pick_raw) or (act_pick_raw in exp_pick_raw)

    # 2. Odds match (if present)
    odds_match = True
    exp_odd = expected.get("od")
    act_odd = actual.get("odds")
    
    if exp_odd and act_odd:
        try:
            e_o = float(exp_odd)
            a_o = float(act_odd)
            if abs(e_o) > 5.0:  # Likely American
                odds_match = abs(e_o - a_o) <= 10.0
            else:
                odds_match = abs(e_o - a_o) <= 0.1
        except:
            pass

    return pick_match and odds_match

def run_benchmark():
    ocr_file = os.path.join(PROJECT_ROOT, "benchmark", "dataset", "ocr_golden_set.json")
    parsing_file = os.path.join(PROJECT_ROOT, "benchmark", "dataset", "parsing_golden_set.json")

    print(f"Loading OCR Data from {ocr_file}...")
    if not os.path.exists(ocr_file):
        print("OCR file not found.")
        return
        
    with open(ocr_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)

    print(f"Loading Ground Truth from {parsing_file}...")
    if not os.path.exists(parsing_file):
        print("Parsing file not found.")
        return

    with open(parsing_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    # Prepare Messages
    messages = []
    for msg_key, text in ocr_data.items():
        # msg_key format: "message_12345"
        msg_id = msg_key.replace("message_", "")
        
        # We need to construct a "full message" structure as expected by pipeline
        messages.append({
            "id": msg_id,
            "text": text,
            "ocr_text": "", # We put everything in text for this benchmark
            "channel_name": "Benchmark_Channel", # Dummy
            "date": "2026-02-14",
            "source": "Benchmark"
        })

    print(f"Prepared {len(messages)} messages for processing.")

    # Run Extraction Pipeline
    print("\n" + "="*50)
    print("STARTING PIPELINE EXECUTION")
    print("="*50 + "\n")
    
    start_time = time.time()
    
    # We use a dummy date for consistency
    extracted_picks = ExtractionPipeline.run(
        messages=messages,
        target_date="2026-02-14",
        batch_size=1, 
        strategy="groq" # Or whatever is default efficient
    )
    
    duration = time.time() - start_time
    print(f"\nPipeline finished in {duration:.2f} seconds.")
    print(f"Extracted {len(extracted_picks)} total picks.")

    # fetch scores
    print("\nFetching scores for the benchmark date...")
    scores = fetch_scores_for_date("2026-02-14")
    grader = GraderEngine(scores)
    
    # Grade extracted picks
    for p in extracted_picks:
        try:
            parsed = PickParser.parse(p.get("pick", ""), p.get("league", "Other"), p.get("date", "2026-02-14"))
            graded = grader.grade(parsed)
            p["grade"] = graded.grade.value
        except Exception:
            p["grade"] = "ERROR"
            
    # Evaluation
    print("\n" + "="*50)
    print("EVALUATION")
    print("="*50 + "\n")

    # Group extracted picks by message ID
    extracted_map = defaultdict(list)
    for p in extracted_picks:
        mid = str(p.get("message_id"))
        extracted_map[f"message_{mid}"].append(p)

    total_expected = 0
    total_found = 0
    total_correct = 0
    
    total_grades_expected = 0
    total_grades_correct = 0
    total_grades_miss = []
    
    # Detailed miss log
    misses = []

    for msg_key, expected_list in ground_truth.items():
        # Sort expected matches by ID or order to try and match sequentially if possible, 
        # but fuzzy matching is set-based per message.
        
        actual_list = extracted_map.get(msg_key, [])
        
        total_expected += len(expected_list)
        total_found += len(actual_list)
        
        # Matching logic
        # We want to map Expected -> Actual 1:1
        # Greedy match: matches first best candidate
        
        used_actual_indices = set()
        
        for exp in expected_list:
            match_found = False
            for idx, act in enumerate(actual_list):
                if idx in used_actual_indices:
                    continue
                
                if fuzzy_match(exp, act):
                    match_found = True
                    used_actual_indices.add(idx)
                    total_correct += 1
                    
                    # Grade matching
                    if 'grade' in exp:
                        total_grades_expected += 1
                        if exp['grade'] == act.get('grade'):
                            total_grades_correct += 1
                        else:
                            total_grades_miss.append({
                                'pick': exp.get('p'),
                                'expected_grade': exp['grade'],
                                'actual_grade': act.get('grade')
                            })
                    break
            
            if not match_found:
                misses.append({
                    "msg_id": msg_key,
                    "expected": exp,
                    "candidates": actual_list
                })

    # Statistics
    precision = (total_correct / total_found * 100) if total_found > 0 else 0
    recall = (total_correct / total_expected * 100) if total_expected > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    print(f"Total Messages: {len(messages)}")
    print(f"Total Expected Picks (Ground Truth): {total_expected}")
    print(f"Total Extracted Picks (Pipeline):    {total_found}")
    print(f"Successfully Matched:                {total_correct}")
    print("-" * 30)
    print(f"Recall (Accuracy against GT):        {recall:.2f}%")
    print(f"Precision (Quality of Extraction):   {precision:.2f}%")
    print(f"F1 Score:                            {f1:.2f}%")
    print("-" * 30)
    
    grading_accuracy = (total_grades_correct / total_grades_expected * 100) if total_grades_expected > 0 else 0
    print(f"Grading Accuracy (on matched):       {grading_accuracy:.2f}% ({total_grades_correct}/{total_grades_expected})")
    print("-" * 30)

    # Save stats to file
    with open("benchmark_stats.txt", "w") as f:
        f.write(f"Recall: {recall:.2f}%\n")
        f.write(f"Precision: {precision:.2f}%\n")
        f.write(f"F1: {f1:.2f}%\n")
        f.write(f"Grading Accuracy: {grading_accuracy:.2f}%\n")

    if misses:
        print(f"\nTop 5 Missed Picks (Sample):")
        for m in misses[:5]:
            print(f"- Msg {m['msg_id']}: Expected '{m['expected'].get('p')}' ({m['expected'].get('ty')})")
            print(f"  Candidates in pipeline: {[a.get('pick') for a in m['candidates']]}")

    if total_grades_miss:
        print(f"\nTop 5 Grading Misses (Sample):")
        for m in total_grades_miss[:5]:
            print(f"- Pick '{m['pick']}': Expected {m['expected_grade']}, Got {m['actual_grade']}")

if __name__ == "__main__":
    run_benchmark()
