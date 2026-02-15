
import sys
import os
import asyncio
import logging

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extraction_pipeline import ExtractionPipeline
from src.semantic_validator import SemanticValidator

# Setup Logging
logging.basicConfig(level=logging.INFO)

async def main():
    print("--- Verifying 'Pats' Alias Fix ---")
    
    # Synthetic message matching the failure pattern
    msg = {
        "id": "test_pats_fix",
        "text": "Pats 1h team total Under 9.5 +105 .5U",
        "date": "2026-02-08"
    }
    
    # 1. Extract (Mocking extraction or just constructing the pick to test validation directly?)
    # The error was in Validation dropping the pick because "Pats" wasn't a team.
    # So we can just test SemanticValidator.validate() with a pick containing "Pats".
    
    pick = {
        "pick": "Pats 1h team total Under 9.5",
        "original_text": "Pats 1h team total Under 9.5 +105 .5U",
        "odds": 105,
        "units": 0.5,
        "type": "Team Prop",
        "sport": "NFL" # Assuming inferred
    }
    
    print(f"Testing validation for pick: {pick['pick']}")
    
    is_valid, reason = SemanticValidator.validate(pick)
    
    if is_valid:
        print("✅ SUCCESS: 'Pats' was recognized as a valid team!")
        print(f"Validated Pick: {pick}")
        return True
    else:
        print(f"❌ FAILED: Pick was rejected. Reason: {reason}")
        return False

if __name__ == "__main__":
    asyncio.run(main())
