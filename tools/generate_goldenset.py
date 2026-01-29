#!/usr/bin/env python3
"""
Goldenset Generator
===================
Selects cached messages, saves them as a test set, and generates
a prompt for a Superior AI (ChatGPT/Claude) to establish the Ground Truth.
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "data"
OUTPUT_INPUTS_FILE = OUTPUT_DIR / "goldenset_inputs.json"


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard. Cross-platform."""
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except ImportError:
        pass

    # Windows fallback
    if sys.platform == "win32":
        try:
            import subprocess

            process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, text=True, encoding="utf-8")
            process.communicate(text)
            return True
        except Exception:
            pass

    return False


def load_data():
    """Load messages and OCR results from cache."""
    msg_path = CACHE_DIR / "messages.json"
    ocr_path = CACHE_DIR / "ocr_results.json"

    if not msg_path.exists():
        print(f"Error: {msg_path} not found. Run pipeline first.")
        return []

    with open(msg_path, encoding="utf-8") as f:
        data = json.load(f)
        messages = data.get("messages", [])

    ocr_results = {}
    if ocr_path.exists():
        with open(ocr_path, encoding="utf-8") as f:
            ocr_data = json.load(f)
            ocr_results = ocr_data.get("results", {})

    # Merge OCR
    merged = []
    for msg in messages:
        # Check by image path or msg_id
        ocr_text = ""

        # Method 1: ID Match
        for path, res in ocr_results.items():
            if res.get("msg_id") == msg.get("id"):
                ocr_text = res.get("text", "")
                break

        # Method 2: Image Path Match
        if not ocr_text and msg.get("image"):
            if msg["image"] in ocr_results:
                ocr_text = ocr_results[msg["image"]].get("text", "")

        if ocr_text:
            msg["ocr_text"] = ocr_text

        merged.append(msg)

    return merged


def generate_prompt(messages):
    """Generate the extraction prompt."""

    # Load Spec
    spec_path = PROJECT_ROOT / "docs" / "pick_format.md"
    spec_content = ""
    if spec_path.exists():
        with open(spec_path, encoding="utf-8") as f:
            spec_content = f.read()

    prompt = f"""# EXPERT SPORTS DATA EXTRACTION TASK

## ROLE
You are a highly advanced Sports Betting Data Analyst. Your task is to extract betting picks from Telegram messages with 100% precision.

## GOAL
Produce a "Gold Set" (Ground Truth) dataset for benchmarking other parsers. The output must be valid JSON.

## INPUT DATA
You will be provided with a list of Telegram messages. Each message contains:
- ID: Unique identifier
- Text: The caption text
- OCR Text: Text extracted from attached images (Critical source of data)

## OUTPUT FORMAT
Return a SINGLE JSON OBJECT containing a list of picks under the key "picks".

JSON Structure per pick:
{{
    "message_id": <int>,       // The ID of the message this pick came from
    "capper_name": <string>,   // Name of the tipster (e.g. "PorterPicks")
    "league": <string>,        // NFL, NBA, NCAAB, NHL, TENNIS, etc. (See Spec)
    "type": <string>,          // Moneyline, Spread, Total, Player Prop, Parlay, etc.
    "pick": <string>,          // The pick value formatted per Spec (e.g. "Lakers ML", "Over 215.5")
    "odds": <int>,             // American odds (e.g. -110, 150). Null if not found.
    "units": <float>,          // Unit size (default 1.0)
    "market": <string>,        // (Optional) Market type e.g. "Moneyline", "Total Points"
    "prop_side": <string>,     // (Optional) "Over" or "Under"
    "line": <float>,           // (Optional) The line value e.g. 215.5, -7.5
    "subject": <string>,       // (Optional) The player or team involved
    "result": "Pending"        // Always Pending
}}

## SPECIFICATION (STRICT ADHERENCE REQUIRED)

{spec_content}

## INSTRUCTIONS
1. Analyze both Caption and OCR text. OCR is often the primary source.
2. If a message contains multiple picks, create multiple pick objects with the same `message_id`.
3. If a message contains NO picks, do not create any entries for it.
4. Extract strict integers for odds (no symbols).
5. Extract strict floats for units.
6. Handle Parlays carefully: The `pick` string must be `(LEAGUE) Leg 1 / (LEAGUE) Leg 2`.
7. DO NOT halluncinate. If data is missing, use null.
8. OUTPUT RAW JSON ONLY. NO MARKDOWN. NO COMMENTS.

## MESSAGES TO PROCESS

"""

    for msg in messages:
        prompt += f"--- MESSAGE ID: {msg.get('id')} ---\n"
        prompt += f"CAPTION:\n{msg.get('text', '')}\n\n"
        if msg.get("ocr_text"):
            prompt += f"OCR TEXT:\n{msg['ocr_text']}\n"
        prompt += "\n"

    prompt += "\n--- END OF MESSAGES ---\n\nProvide the JSON output now."
    return prompt


def main():
    print("Loading data...")
    messages = load_data()

    if not messages:
        return

    # Filter for interesting ones (selected=True)
    # Take top 20
    candidates = [m for m in messages if m.get("selected")]
    sample = candidates[:20]

    if not sample:
        print("No selected messages found. Using first 20 raw messages.")
        sample = messages[:20]

    print(f"Selected {len(sample)} messages for Goldenset.")

    # Save Inputs
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_INPUTS_FILE, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2)
    print(f"Saved inputs to: {OUTPUT_INPUTS_FILE}")

    # Generate Prompt
    prompt = generate_prompt(sample)

    # Copy
    if copy_to_clipboard(prompt):
        print("Prompt copied to clipboard! (Success)")
    else:
        print("Clipboard copy failed. Saving to 'goldenset_prompt.txt'")
        with open("goldenset_prompt.txt", "w", encoding="utf-8") as f:
            f.write(prompt)

    print("\nNEXT STEPS:")
    print("1. Paste the prompt into ChatGPT/Claude.")
    print("2. Copy the resulting JSON.")
    print("3. Return the JSON to the agent.")


if __name__ == "__main__":
    main()
