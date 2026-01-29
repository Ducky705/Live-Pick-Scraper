"""
Generate DSL Prompt Tool
========================
Generates a prompt to test the new DSL (Compact Line Protocol)
using the same Goldenset Inputs.
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.prompts.dsl import generate_dsl_user_prompt, get_dsl_system_prompt

INPUT_FILE = PROJECT_ROOT / "tests" / "data" / "goldenset_inputs.json"


def copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except:
        return False


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        messages = json.load(f)

    print(f"Loaded {len(messages)} messages.")

    prompt = "# TEST PROMPT FOR SPORTS BETTING DSL\n\n"
    prompt += "## SYSTEM INSTRUCTIONS\n\n"
    prompt += get_dsl_system_prompt()
    prompt += "\n\n"
    prompt += "## USER INPUTS\n\n"

    for i, msg in enumerate(messages):
        prompt += f"--- MESSAGE {i + 1} (ID: {msg.get('id')}) ---\n"
        ocr = msg.get("ocr_text", "")
        # If no OCR text but has images, check list
        if not ocr and msg.get("ocr_texts"):
            ocr = "\n".join(msg["ocr_texts"])

        prompt += generate_dsl_user_prompt(msg.get("text", ""), ocr)
        prompt += "\n"

    print(f"Generated prompt ({len(prompt)} chars).")

    if copy_to_clipboard(prompt):
        print("Copied to clipboard!")
    else:
        print("Could not copy. Saving to dsl_prompt.txt")
        with open("dsl_prompt.txt", "w", encoding="utf-8") as f:
            f.write(prompt)


if __name__ == "__main__":
    main()
