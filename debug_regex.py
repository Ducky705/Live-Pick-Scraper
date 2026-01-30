from src.rule_based_extractor import RuleBasedExtractor
from src.grading.schema import BetType


def test_lines():
    lines = [
        "5% SMU-12",
        "2U North Carolina +7 -110",
        "Arkansas -10 -110 2U",
    ]

    print("Testing extraction on lines:")
    for line in lines:
        print(f"\nOriginal: '{line}'")

        # Simulate cleanups
        clean = RuleBasedExtractor.RE_REMOVE_PREFIX.sub("", line)
        clean = RuleBasedExtractor.RE_REMOVE_NUMBERING.sub("", clean)
        clean = RuleBasedExtractor.RE_NORM_ML_OCR.sub("ML", clean)
        clean = RuleBasedExtractor.RE_FIX_SPACED_ODDS.sub(r"\1\2", clean)
        clean = RuleBasedExtractor.RE_FIX_UNDER.sub(r"Under \2", clean)
        clean = RuleBasedExtractor.RE_FIX_OVER.sub(r"Over \2", clean)
        clean = RuleBasedExtractor.RE_FIX_MONEYLINE.sub("Moneyline", clean)

        print(f"Cleaned: '{clean}'")

        has_ind = RuleBasedExtractor._has_pick_indicators(clean)
        print(f"Has Indicators: {has_ind}")

        if has_ind:
            units = RuleBasedExtractor._extract_units(clean)
            print(f"Units: {units}")

            clean_parsed = RuleBasedExtractor.RE_PARENS.sub("", clean).strip()
            print(f"Passed to Parser: '{clean_parsed}'")

            from src.grading.parser import PickParser

            try:
                pick = PickParser.parse(clean_parsed, "Unknown")
                print(f"Parsed: {pick}")
                valid = RuleBasedExtractor._is_valid_extraction(pick)
                print(f"Valid: {valid}")
            except Exception as e:
                print(f"Parse Error: {e}")


if __name__ == "__main__":
    test_lines()
