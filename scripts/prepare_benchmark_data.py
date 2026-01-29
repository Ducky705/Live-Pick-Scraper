import json
import os


def convert_golden_set_to_messages():
    input_path = "benchmark/clean_golden_set.json"
    output_path = "cache/messages.json"

    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    # data is a list of message objects
    # We wrap it in a "messages" key if needed, or just save as list if run_scraper accepts it.
    # run_scraper_on_file.py accepts list or {"messages": list}

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Created {output_path} with {len(data)} messages.")


if __name__ == "__main__":
    convert_golden_set_to_messages()
