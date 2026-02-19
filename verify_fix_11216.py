import sys
import os
import json
import asyncio

# Add src to path
sys.path.append(os.getcwd())

from src.extraction_pipeline import ExtractionPipeline

# The problematic message from Verification Report
# Raw text reconstruction
msg_text = """**BetSharper**
Straight Bets Only

5u Lakers -5 (-110)
Marist ML"""

msg_data = {
    "id": 11216,
    "date": "2026-02-15 12:00:00",
    "message": msg_text, # Legacy field for manual construction? 
    # Pipeline expects dictionary with 'text' or 'caption'
    "text": msg_text,
    "ocr_text": "",
    "caption": ""
}

print("=== TESTING MSG 11216 (BetSharper Case) ===")
print(f"Input Text:\n{msg_text}\n")

# Run Pipeline
# extraction_pipeline.run takes list of messages
try:
    # We use the sync wrapper or async?
    # ExtractionPipeline.run is sync (it calls parallel_processor which handles threads)
    picks = ExtractionPipeline.run([msg_data], target_date="2026-02-15")
    
    print(f"\nResult: {len(picks)} picks extracted")
    for p in picks:
        print(json.dumps(p, indent=2))
        
    # Validation logic
    teams = [p.get("selection", "") for p in picks]
    headers = [p.get("capper_name", "") for p in picks]
    
    if any("BetSharper" in t for t in teams):
        print("\n❌ FAILURE: 'BetSharper' incorrectly extracted as a pick/team!")
    else:
        print("\n✅ SUCCESS: 'BetSharper' ignored (Noise Filter working).")
        
    if any("Lakers" in t for t in teams) and any("Marist" in t for t in teams):
         print("✅ SUCCESS: Lakers and Marist extracted.")
    else:
         print("❌ FAILURE: Missed valid picks (Lakers/Marist).")

except Exception as e:
    print(f"Error: {e}")
