import json
import logging
import os
import random
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.ocr_handler import extract_text
from src.openrouter_client import openrouter_completion
from src.prompt_builder import generate_ai_prompt

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_json(filepath):
    if not os.path.exists(filepath):
        logging.warning(f"File not found: {filepath}")
        return []
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def resolve_image_path(image_path):
    # Determine project root
    base_dir = os.getcwd()
    temp_img_dir = os.path.join(base_dir, "temp_images")

    if image_path.startswith("/static/temp_images/"):
        filename = image_path.split("/static/temp_images/")[-1]
        return os.path.join(temp_img_dir, filename)

    # Handle absolute paths or other formats if necessary
    return image_path


def process_item(item, source):
    """
    Process a single item:
    1. Extract text from image if present (and not already OCR'd).
    2. Prepare data for prompt.
    3. Call LLM to get picks.
    """
    item_id = item.get("id")
    text = item.get("text", "")
    images = item.get("images", [])
    if not images and item.get("image"):
        images = [item.get("image")]

    # Resolve image paths
    resolved_images = []
    ocr_texts = []

    for img_path in images:
        if img_path:
            abs_path = resolve_image_path(img_path)
            if os.path.exists(abs_path):
                resolved_images.append(abs_path)
                # Perform OCR
                try:
                    logging.info(f"Running OCR on {abs_path}...")
                    ocr_text = extract_text(abs_path)
                    if ocr_text:
                        ocr_texts.append(ocr_text)
                except Exception as e:
                    logging.error(f"OCR failed for {abs_path}: {e}")
            else:
                logging.warning(f"Image not found: {abs_path}")

    # Prepare data for prompt builder
    # prompt_builder expects dicts with 'text', 'ocr_texts', 'id'
    data_for_prompt = {"id": item_id, "text": text, "ocr_texts": ocr_texts}

    # Generate prompt
    prompt = generate_ai_prompt([data_for_prompt])

    # Call LLM
    expected_picks = []
    try:
        logging.info(f"Calling LLM for item {item_id}...")
        response = openrouter_completion(prompt)

        # Parse JSON response
        # The prompt asks for a JSON object with a "picks" key
        try:
            parsed = json.loads(response)
            if "picks" in parsed:
                expected_picks = parsed["picks"]
            else:
                logging.warning(f"LLM response missing 'picks' key for {item_id}")
        except json.JSONDecodeError:
            logging.error(f"Failed to parse LLM JSON for {item_id}: {response}")

    except Exception as e:
        logging.error(f"LLM call failed for {item_id}: {e}")

    # Construct Golden Set Entry
    entry = {
        "id": str(item_id),
        "source": source,
        "original_text": text,
        "image_paths": resolved_images,
        "ocr_texts": ocr_texts,  # Store OCR for debugging/reference
        "expected_picks": expected_picks,
    }

    return entry


from concurrent.futures import ThreadPoolExecutor, as_completed


def process_item_safe(item, source):
    try:
        return process_item(item, source)
    except Exception as e:
        logging.error(f"Failed to process {item.get('id')}: {e}")
        return None


def main():
    # Load sources
    telegram_data = load_json("test_messages.json")
    twitter_data = load_json("debug_raw_tweets.json")
    discord_data = load_json("debug_raw_discord.json")

    logging.info(
        f"Loaded {len(telegram_data)} Telegram, {len(twitter_data)} Twitter, {len(discord_data)} Discord messages."
    )

    # Select 100 items (34 Telegram, 33 Twitter, 33 Discord)
    def filter_valid(items):
        return [i for i in items if i.get("text") or i.get("image") or i.get("images")]

    telegram_valid = filter_valid(telegram_data)
    twitter_valid = filter_valid(twitter_data)
    discord_valid = filter_valid(discord_data)

    random.seed(42)

    selected_telegram = random.sample(telegram_valid, min(34, len(telegram_valid)))
    selected_twitter = random.sample(twitter_valid, min(33, len(twitter_valid)))
    selected_discord = random.sample(discord_valid, min(33, len(discord_valid)))

    all_selected = []
    for item in selected_telegram:
        all_selected.append((item, "Telegram"))
    for item in selected_twitter:
        all_selected.append((item, "Twitter"))
    for item in selected_discord:
        all_selected.append((item, "Discord"))

    logging.info(f"Selected {len(all_selected)} total items for Golden Set.")

    golden_set = []

    # Process in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_item_safe, item, source): item["id"] for item, source in all_selected}

        for future in as_completed(futures):
            item_id = futures[future]
            try:
                result = future.result()
                if result:
                    golden_set.append(result)
                    logging.info(f"Completed {item_id}. Total: {len(golden_set)}")
            except Exception as e:
                logging.error(f"Error getting result for {item_id}: {e}")

    # Save Golden Set
    output_file = "golden_set/golden_set_v2.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(golden_set, f, indent=2)

    logging.info(f"Golden Set saved to {output_file} with {len(golden_set)} entries.")


if __name__ == "__main__":
    main()
