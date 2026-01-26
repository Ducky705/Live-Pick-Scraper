import os
import sys
import json
import logging
import time

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt
from src.ocr_handler import extract_text_batch
from src.parsers.dsl_parser import parse_dsl_lines

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Paths
DATASET_DIR = os.path.join(os.getcwd(), "benchmark", "dataset")
IMAGE_MAP_PATH = os.path.join(DATASET_DIR, "image_map.json")

DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"


def debug_image_04():
    img_key = "image_04.jpg"

    with open(IMAGE_MAP_PATH, "r", encoding="utf-8") as f:
        image_map = json.load(f)

    img_path = image_map.get(img_key)
    if not img_path or not os.path.exists(img_path):
        print(f"Image not found: {img_path}")
        return

    print(f"Debugging {img_key} at {img_path}")

    # 1. OCR
    print("Running OCR...")
    ocr_results = extract_text_batch([img_path])
    ocr_text = ocr_results[0] if ocr_results else ""
    print(f"OCR TEXT:\n{'-' * 40}\n{ocr_text}\n{'-' * 40}")

    # 2. Prompt Generation
    synthetic_message = {
        "id": 1,
        "text": "",
        "ocr_texts": [ocr_text],
        "ocr_text": ocr_text,
    }
    prompt = generate_ai_prompt([synthetic_message])
    print(f"PROMPT (first 500 chars):\n{prompt[:500]}...")

    # 3. Model Call
    print(f"Calling Model: {DEFAULT_MODEL}...")
    response = openrouter_completion(prompt, model=DEFAULT_MODEL, timeout=120)

    # safe print
    try:
        print(
            f"RESPONSE:\n{'-' * 40}\n{response.encode('ascii', 'replace').decode()}\n{'-' * 40}"
        )
    except:
        print("Response printing failed due to encoding")

    # 4. Parsing
    print("Parsing DSL...")
    dsl_picks = parse_dsl_lines(response)
    print(f"DSL Picks: {len(dsl_picks)}")
    for p in dsl_picks:
        print(p)

    print("Parsing JSON fallback...")
    cleaned = response.replace("```json", "").replace("```", "").strip()
    try:
        parsed_json = json.loads(cleaned)
        if isinstance(parsed_json, dict):
            json_picks = parsed_json.get("picks") or []
        else:
            json_picks = parsed_json
        print(f"JSON Picks: {len(json_picks)}")
        for p in json_picks:
            print(p)
    except Exception as e:
        print(f"JSON Parse Failed: {e}")


if __name__ == "__main__":
    debug_image_04()
