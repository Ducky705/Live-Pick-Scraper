import json


def main():
    input_file = "golden_set/golden_set_v2.json"
    output_file = "golden_set/golden_set_final.json"

    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)

    ids_to_remove = ["1462954410371055646", "1461499015681020118"]

    cleaned_data = [item for item in data if item["id"] not in ids_to_remove]

    # Also clean up any other empty/null picks just in case
    final_data = []
    for item in cleaned_data:
        # Filter picks that are just nulls
        valid_picks = []
        for p in item.get("expected_picks", []):
            if p.get("p") is not None and p.get("p") != "None":
                valid_picks.append(p)

        item["expected_picks"] = valid_picks

        # Only keep if it has valid picks OR if it's a valid negative test case (text exists but no picks)
        # But for a golden set of *extraction*, we usually want positive examples.
        # Let's keep it if it has text/images, even if 0 picks (true negative).
        final_data.append(item)

    print(f"Original count: {len(data)}")
    print(f"Removed {len(data) - len(cleaned_data)} items.")
    print(f"Final count: {len(final_data)}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2)

    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
