import os
import shutil

DATASET_DIR = r"d:\Programs\Sports Betting\TelegramScraper\v0.0.15\benchmark\dataset"
ARCHIVE_DIR = os.path.join(DATASET_DIR, "archive")

# Ensure archive exists
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# The Valid Files (V2)
NEW_OCR = "ocr_golden_set_v2.json"
NEW_PARSING = "parsing_golden_set_v2.json"

# Files to Archive
FILES_TO_ARCHIVE = [
    "ocr_golden_set.json",
    "parsing_golden_set.json",
    "ocr_golden_set_saturday.json",
    "golden_set_v3_candidates.json",
    "golden_set_v3_draft.json",
    "golden_set_v4.json",
    "golden_set_v4_candidates.json",
    "golden_set_v5.json",
    "goldenset_platform_500.json",
    "stress_test_500.json"
]

def cleanup_datasets():
    # 1. Move old files
    for filename in FILES_TO_ARCHIVE:
        src = os.path.join(DATASET_DIR, filename)
        if os.path.exists(src):
            dst = os.path.join(ARCHIVE_DIR, filename)
            print(f"Archiving {filename}...")
            shutil.move(src, dst)
        else:
            print(f"Skipping {filename} (not found)")

    # 2. Rename V2 to Canonical
    # Note: We rename to the standard names "ocr_golden_set.json" and "parsing_golden_set.json"
    # effectively replacing the ones we just archived.
    
    v2_ocr_path = os.path.join(DATASET_DIR, NEW_OCR)
    canonical_ocr_path = os.path.join(DATASET_DIR, "ocr_golden_set.json")
    
    v2_parsing_path = os.path.join(DATASET_DIR, NEW_PARSING)
    canonical_parsing_path = os.path.join(DATASET_DIR, "parsing_golden_set.json")

    if os.path.exists(v2_ocr_path):
        print(f"Promoting {NEW_OCR} to ocr_golden_set.json")
        shutil.move(v2_ocr_path, canonical_ocr_path)
    else:
        print(f"Error: {NEW_OCR} not found!")

    if os.path.exists(v2_parsing_path):
        print(f"Promoting {NEW_PARSING} to parsing_golden_set.json")
        shutil.move(v2_parsing_path, canonical_parsing_path)
    else:
        print(f"Error: {NEW_PARSING} not found!")

    # 3. Create README
    readme_path = os.path.join(DATASET_DIR, "DATASET_README.md")
    readme_content = """# Sports Betting Golden Set

**Active Standard: v2 (Platinum)**
*Created: 2026-02-18*

## Files
- `ocr_golden_set.json`: Contains the raw input text (Full Messages).
- `parsing_golden_set.json`: Contains the expected output (Ground Truth).

## History
- **v2 (Platinum):** Created from `debug_extraction_log_2026-02-14.json`. Includes FULL message context (headers, multiple cappers) and validated capper attribution.
- **v1 (Legacy):** Archived. Contained fragmented single lines and "Unknown" capper names.

## Usage
Use `benchmark_golden_set.py` to run tests against these files.
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("Created DATASET_README.md")

if __name__ == "__main__":
    cleanup_datasets()
