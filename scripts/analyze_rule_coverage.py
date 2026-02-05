import json
import os
import sys

# Setup
sys.path.insert(0, os.path.abspath("."))
from src.rule_based_extractor import RuleBasedExtractor

def analyze_coverage():
    dataset_path = "new_golden_set.json"
    
    if not os.path.exists(dataset_path):
        print("V3 Dataset not found.")
        return

    with open(dataset_path, "r") as f:
        data = json.load(f)

    print(f"Analyzing Rule Engine Coverage on {len(data)} items...\n")
    
    covered_count = 0
    fallback_reasons = {}
    
    print(f"{'ID':<15} | {'Source':<10} | {'Status':<10} | {'Reason'}")
    print("-" * 80)

    for item in data:
        # We assume the RuleBasedExtractor is stateless for this test
        # We care about the return value: (picks, remaining_messages)
        # If remaining_messages is NOT empty, it means fallback occurred.
        
        picks, remaining = RuleBasedExtractor.extract([item])
        
        status = "HIT"
        reason = ""
        
        if remaining:
            status = "MISS"
            # Why?
            # Usually means no picks found OR explicit low confidence logic
            # Let's peek at the failure reason logic (it's implicit in the code usually)
            # We can check if *any* picks were found but discarded?
            # Actually extract() returns (picks, remaining). 
            # If picks found AND remaining is empty -> Full Coverage.
            # If picks found AND remaining is NOT empty -> Partial/Mixed (treated as fallback usually?)
            # If NO picks AND remaining is NOT empty -> Full Fallback.
            
            if picks:
                status = "PARTIAL"
                reason = "Some lines parses, others failed"
            else:
                status = "FULL_AI"
                reason = "No regex match found"
                
            # Store sample text for review
            snippet = item.get("text", "")[:30].replace("\n", " ")
            fallback_reasons[item.get("id")] = f"{reason} | {snippet}..."
        else:
            covered_count += 1
            status = "HIT"
            reason = f"Found {len(picks)} picks"

        print(f"{str(item.get('id')):<15} | {item.get('source'):<10} | {status:<10} | {reason}")

    metrics = {
        "total": len(data),
        "covered": covered_count,
        "missed": len(data) - covered_count,
        "coverage_pct": (covered_count / len(data)) * 100
    }
    
    print("\n" + "="*40)
    print(f"Coverage: {metrics['coverage_pct']:.2f}% ({metrics['covered']}/{metrics['total']})")
    print("="*40)
    
    if fallback_reasons:
        print("\nTop Improvement Candidates (Failures):")
        for mid, r in fallback_reasons.items():
            print(f"- {mid}: {r}")

if __name__ == "__main__":
    analyze_coverage()
