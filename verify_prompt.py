import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.prompt_builder import generate_ai_prompt

dummy_data = [
    {
        "id": "12345",
        "text": "**BetSharper** Straight Bets Only\n5u Lakers -5 (-110)\nMarist ML",
        "ocr_text": ""
    }
]

prompt = generate_ai_prompt(dummy_data)
print("=== GENERATED PROMPT ===")
print(prompt)
print("=== END PROMPT ===")
