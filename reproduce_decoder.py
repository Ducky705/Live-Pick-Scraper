import sys
import os
import json

# Add src to path
sys.path.append(os.getcwd())

from src.prompts.decoder import normalize_response, expand_compact_pick

# Mock Llama 3.3 output (based on prompt structure)
mock_llama_output = """
{
  "picks": [
    {
      "message_id": "12345",
      "capper_name": "BetSharper",
      "sport": "NBA",
      "bet_type": "Spread",
      "selection": "Lakers -5",
      "line": -5.0,
      "odds": -110,
      "units": 1.0,
      "confidence": 9,
      "reasoning": "Explicit mention of Lakers spread"
    },
    {
      "message_id": "12346",
      "capper_name": "Dave",
      "sport": "Basketball",
      "bet_type": "Moneyline",
      "selection": "Knicks ML",
      "odds": -150
    }
  ]
}
"""

print("=== DECODER TEST ===")
try:
    picks = normalize_response(mock_llama_output, expand=True)
    print(f"Decoded Picks: {len(picks)}")
    for i, p in enumerate(picks):
        print(f"Pick {i+1}:")
        print(json.dumps(p, indent=2))
        
        # Check specific fields
        print(f"  -> derived type: {p.get('type')}")
        print(f"  -> derived league: {p.get('league')}")
        
except Exception as e:
    print(f"Error: {e}")
