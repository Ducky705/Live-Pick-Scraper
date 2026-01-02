import sys
import os
import json
import asyncio

# Add root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from src.ocr_handler import extract_text
from src.prompt_builder import generate_ai_prompt
from src.openrouter_client import openrouter_completion
from config import BASE_DIR

def run_single(image_rel_path, case_id="debug_case"):
    print(f"Testing full pipeline on: {image_rel_path}")
    
    # 1. OCR
    ocr_text = extract_text(image_rel_path)
    print("--- OCR ---")
    print(ocr_text[:200] + "...")
    print("-----------")
    
    # 2. Prompt
    fake_item = {
        'id': case_id,
        'text': "Caption",
        'ocr_texts': [ocr_text],
        'ocr_text': ocr_text
    }
    
    prompt = generate_ai_prompt([fake_item])
    
    # 3. AI
    print("Calling AI...")
    try:
        result_str = openrouter_completion(prompt)
        print("--- AI RESULT ---")
        print(result_str)
        print("-----------------")
    except Exception as e:
        print(f"AI Failed: {e}")

if __name__ == "__main__":
    run_single("tests/samples/-1001900292133_55839.jpg")
