import json
import logging
import sys
import os

# Setup path
sys.path.insert(0, os.path.abspath("."))

from src.rule_based_extractor import RuleBasedExtractor
# Removed broken Grader import
# from src.grader import Grader

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("RuleVerify")

def load_golden_set():
    try:
        with open("new_golden_set.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("new_golden_set.json not found!")
        return []

def simple_grade(expected_picks, generated_picks):
    """
    Simple exact/partial match grader.
    """
    matches = 0
    
    # Normalize expected
    # Expected pick format: "Team Name Moneyline" or "Team -5"
    exp_set = []
    for ep in expected_picks:
        # Create a signature: "pick|type|odds"
        # We'll rely mostly on the "pick" text
        p_text = ep.get("pick", "").lower().replace("moneyline", "ml")
        exp_set.append(p_text)
        
    gen_set = []
    for gp in generated_picks:
        # Rule based picks might be: "Team ML" or "Team -5"
        p_text = gp.get("pick", "").lower()
        gen_set.append(p_text)
        
    # Count matches (Naive Containment)
    for exp in exp_set:
        matched = False
        for gen in gen_set:
            # Check if one is contained in the other
            # e.g. "Lakers -5" in "Lakers -5.5" (close enough for rule check?)
            # or "Lakers" and "Lakers"
            
            # Simple token overlap
            exp_tokens = set(exp.split())
            gen_tokens = set(gen.split())
            
            # If > 50% overlap
            overlap = len(exp_tokens.intersection(gen_tokens))
            if overlap / max(1, len(exp_tokens)) > 0.6:
                matched = True
                break
        
        if matched:
            matches += 1
            
    score = (matches / len(expected_picks) * 100) if expected_picks else 0
    return score, {"correct_count": matches, "missing": [], "extra": []}

def main():
    golden_set = load_golden_set()
    if not golden_set:
        return

    print(f"Loaded {len(golden_set)} messages from Golden Set.")

    # Run Extractor
    # Note: extractor expects a list of messages.
    # We must ensure the input matches internal format (it usually just expects dicts)
    
    extracted_picks, remaining_messages = RuleBasedExtractor.extract(golden_set)
    
    handled_count = len(golden_set) - len(remaining_messages)
    print(f"Rule Engine Handled: {handled_count}/{len(golden_set)} Messages ({handled_count/len(golden_set)*100:.1f}%)")
    print(f"Total Picks Extracted: {len(extracted_picks)}")

    # Grading
    # We need to restructure extracted picks by message ID to grade them against golden set
    picks_by_msg = {}
    for p in extracted_picks:
        mid = str(p.get("message_id"))
        if mid not in picks_by_msg:
            picks_by_msg[mid] = []
        picks_by_msg[mid].append(p)

    # Use simple grader
    
    total_score = 0
    total_items = 0
    
    print("\n--- DETAILED RESULTS ---")

    for item in golden_set:
        mid_str = str(item.get("id"))
        
        # Skip if not handled by rule engine
        if mid_str not in picks_by_msg:
            continue
            
        generated_picks = picks_by_msg[mid_str]
        expected_picks = item.get("expected_picks", [])
        
        # Grade
        score, report = simple_grade(expected_picks, generated_picks)
        
        print(f"Msg {mid_str}: Score {score:.1f}% | Picks: {len(generated_picks)} Found / {len(expected_picks)} Expected")
        if score < 100:
             print(f"   Matches: {report.get('correct_count', 0)}")

        total_score += score
        total_items += 1

    if total_items > 0:
        avg_score = total_score / total_items
        print(f"\nAverage Accuracy on Handled Messages: {avg_score:.2f}%")
    else:
        print("\nNo messages were handled by Rule Engine.")

if __name__ == "__main__":
    main()
