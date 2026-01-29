import json
import logging
import os
import re
import sys

sys.path.insert(0, os.getcwd())

from src.openrouter_client import openrouter_completion
from src.parsers.dsl_parser import parse_dsl_lines
from src.prompt_builder import generate_ai_prompt
from src.rule_based_extractor import RuleBasedExtractor

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Paths
DATASET_DIR = os.path.join(os.getcwd(), "benchmark", "dataset")
IMAGE_MAP_PATH = os.path.join(DATASET_DIR, "image_map.json")
PARSING_GOLDEN_SET_PATH = os.path.join(DATASET_DIR, "parsing_golden_set.json")
OCR_GOLDEN_SET_PATH = os.path.join(DATASET_DIR, "ocr_golden_set.json")

DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"


def fuzzy_match(gt_pick, sys_pick):
    """Fuzzy match two pick strings."""
    if not gt_pick or not sys_pick:
        return False

    # Normalize: lower, strip, remove punctuation
    def normalize(s):
        return re.sub(r"[^\w\s]", "", s.lower().strip())

    gt_norm = normalize(gt_pick)
    sys_norm = normalize(sys_pick)

    if gt_norm == sys_norm:
        return True

    if gt_norm in sys_norm or sys_norm in gt_norm:
        return True

    gt_tokens = set(gt_norm.split())
    sys_tokens = set(sys_norm.split())
    overlap = len(gt_tokens & sys_tokens)
    max_len = max(len(gt_tokens), len(sys_tokens))

    ratio = overlap / max_len if max_len > 0 else 0
    return ratio >= 0.5, ratio


def debug_failures(target_images):
    with open(IMAGE_MAP_PATH, encoding="utf-8") as f:
        image_map = json.load(f)
    with open(PARSING_GOLDEN_SET_PATH, encoding="utf-8") as f:
        parsing_golden = json.load(f)
    with open(OCR_GOLDEN_SET_PATH, encoding="utf-8") as f:
        ocr_golden = json.load(f)

    for img_key in target_images:
        img_path = image_map.get(img_key)
        expected_picks = parsing_golden.get(img_key, [])
        ocr_text = ocr_golden.get(img_key, "")

        print(f"\n{'=' * 60}")
        print(f"DEBUGGING: {img_key}")
        print(f"{'=' * 60}")

        # 1. Rule Based
        rule_input = [{"id": 1, "text": "", "ocr_text": ocr_text}]
        rule_picks, _ = RuleBasedExtractor.extract(rule_input)
        print(f"RULE PICKS: {len(rule_picks)}")
        for p in rule_picks:
            print(f"  [R] {p.get('pick')}")

        # 2. AI
        synthetic_message = {
            "id": 1,
            "text": "",
            "ocr_texts": [ocr_text],
            "ocr_text": ocr_text,
        }
        prompt = generate_ai_prompt([synthetic_message])
        response = openrouter_completion(prompt, model=DEFAULT_MODEL, timeout=60)

        parsed_picks = parse_dsl_lines(response)
        if not parsed_picks:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            try:
                parsed_json = json.loads(cleaned)
                if isinstance(parsed_json, dict):
                    parsed_picks = parsed_json.get("picks") or parsed_json.get("analysis") or []
                elif isinstance(parsed_json, list):
                    parsed_picks = parsed_json
            except:
                pass

        print(f"AI PICKS: {len(parsed_picks)}")
        for p in parsed_picks:
            p_val = p if isinstance(p, str) else p.get("pick", p.get("p"))
            print(f"  [A] {p_val}")

        # 3. Merging
        final_picks = []
        seen = set()

        for p in rule_picks:
            p_str = str(p.get("pick", "")).lower().strip()
            if p_str and p_str not in seen:
                seen.add(p_str)
                final_picks.append(p)

        for p in parsed_picks:
            p_val = p if isinstance(p, str) else p.get("pick", p.get("p"))
            p_str = str(p_val).lower().strip()
            if p_str and p_str not in seen:
                seen.add(p_str)
                final_picks.append(p if not isinstance(p, str) else {"pick": p})

        print(f"FINAL MERGED PICKS: {len(final_picks)}")

        # 4. Scoring Debug
        matched_gt = set()
        print("\nSCORING:")
        for gp in expected_picks:
            gt_pick = gp.get("p", "")
            match_found = False
            for sp_obj in final_picks:
                sys_pick = sp_obj.get("pick") or sp_obj.get("p") or ""
                is_match, ratio = fuzzy_match(gt_pick, sys_pick)
                if is_match:
                    match_found = True
                    print(f"  [MATCH] {gt_pick} == {sys_pick} (Ratio: {ratio:.2f})")
                    break
                # debug partials
                elif ratio > 0.3:
                    print(f"  [NEAR]  {gt_pick} vs {sys_pick} (Ratio: {ratio:.2f})")

            if not match_found:
                print(f"  [MISS]  {gt_pick}")


if __name__ == "__main__":
    debug_failures(["image_04.jpg", "image_20.jpg"])
