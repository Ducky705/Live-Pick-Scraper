
import os
import sys
import json
import logging

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt
from src.ocr_handler import extract_text_batch

# Setup logging
logging.basicConfig(level=logging.INFO)

# Image path
img_path = "D:/Programs/Sports Betting/TelegramScraper/v0.0.15/benchmark/dataset/images/-1001900292133_55817.jpg"

def run_debug():
    print(f"Processing {img_path}...")
    
    # Step 1: OCR
    print("Running OCR...")
    ocr_results = extract_text_batch([img_path])
    ocr_text = ocr_results[0] if ocr_results else ""
    print(f"OCR Result: {ocr_text}")
    
    # Step 2: Parsing
    print("Running Parsing...")
    synthetic_message = {
        'id': 1,
        'text': "",
        'ocr_texts': [ocr_text],
        'ocr_text': ocr_text
    }
    
    prompt = generate_ai_prompt([synthetic_message])
    response = openrouter_completion(prompt)
    
    print("\nParsing Result:")
    print(response)

if __name__ == "__main__":
    run_debug()
