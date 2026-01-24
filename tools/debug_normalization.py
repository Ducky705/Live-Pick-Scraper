
import sys
import os
import json
import logging

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.prompts.decoder import normalize_response

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_normalization():
    print("=== TESTING NORMALIZATION ===")
    
    # 1. Simulate a typical compact LLM response (as requested in core.py)
    # Keys: i=id, c=capper, l=league, t=type, p=pick, o=odds, u=units
    mock_response = """
    ```json
    {
        "picks": [
            {
                "i": 31597,
                "c": "Vezino", 
                "l": "NBA", 
                "t": "SP", 
                "p": "Milwaukee Bucks -8.5", 
                "o": -110, 
                "u": 1
            },
            {
                "i": 31595, 
                "c": "Porter Picks", 
                "l": "NBA", 
                "t": "TL", 
                "p": "Rockets vs Pistons Under 218", 
                "o": -110, 
                "u": 1
            }
        ]
    }
    ```
    """
    
    print("\n--- Test 1: Standard Compact JSON ---")
    picks = normalize_response(mock_response, expand=True)
    print(f"Extracted {len(picks)} picks")
    if picks:
        print("First pick keys:", picks[0].keys())
        print("First pick sample:", json.dumps(picks[0], indent=2))
        
        # Check if keys are expanded correctly
        if 'capper_name' not in picks[0] or picks[0]['capper_name'] == 'Unknown':
            print("FAIL: capper_name not mapped correctly!")
        if 'pick' not in picks[0] or picks[0]['pick'] == 'N/A':
            print("FAIL: pick not mapped correctly!")
            
    # 2. Simulate raw list response
    mock_response_2 = """
    [
        {"i": 123, "p": "Lakers ML", "t": "ML", "l": "NBA"}
    ]
    """
    print("\n--- Test 2: List JSON ---")
    picks2 = normalize_response(mock_response_2, expand=True)
    print(f"Extracted {len(picks2)} picks")
    print("Sample:", picks2[0])

if __name__ == "__main__":
    test_normalization()
