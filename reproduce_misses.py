
import logging
from src.rule_based_extractor import RuleBasedExtractor
from src.grading.validity_filter import ValidityFilter

# Setup logging
logging.basicConfig(level=logging.INFO)

def run_debug():
    print("--- Debugging Missed Messages ---")

    missed_cases = [
        {
            "id": "GoldenWhale",
            "text": "*Golden Whale Parlay (1)\nlowa State Cyclones money line\nWake Forest money line"
        },
        {
            "id": "OklahomaMI",
            "text": "5U POD: Oklahoma MI\nTexas MI"
        },
        {
            "id": "Win3pt",
            "text": "Devin Booker Win 3pt content\nJason Hayes Win Slam Dunk"
        },
        {
            "id": "KBL_NoSpace",
            "text": "BusanKCCEgis-5.5-118(1.5U)\nWonju DBPromy +6-115(1U)"
        }
    ]

    extractor = RuleBasedExtractor()
    vf = ValidityFilter()

    for case in missed_cases:
        print(f"\n[Case: {case['id']}]")
        print(f"Input: {case['text'].replace(chr(10), ' | ')}")
        
        # 1. Run RuleBasedExtractor
        msg = {"id": case["id"], "text": case["text"], "ocr_text": ""}
        picks, remaining = RuleBasedExtractor.extract([msg])
        
        if picks:
            print(f"✅ Extracted {len(picks)} picks:")
            for p in picks:
                print(f"   - {p['pick']} (Type: {p['type']}, Odds: {p['odds']})")
                
                # 2. Check Validity
                is_valid, reason = vf.is_valid(p['pick'])
                print(f"     -> Validity Check: {is_valid} ({reason})")
        else:
            print("❌ No picks extracted.")

if __name__ == "__main__":
    run_debug()
