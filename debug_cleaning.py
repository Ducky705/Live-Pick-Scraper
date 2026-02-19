from src.utils import clean_sauce_text
from src.rule_based_extractor import RuleBasedExtractor

def test_cleaning():
    msgs = {
        "32103": "Analyticscapper \n\nMain Card: NCAAB\nGrand Canyon -11.5 (-110) v. San Jose St 5u\nUT Rio Grande -1.5 (-110) v. SF Austin 5u POTD\nMissouri -1.5 (-110) v. Texas 5u\nPacific +7.5 (-110) v. St Mary's 5u",
        "Bullies": "BulliesPicks (1/5)\n➖➖➖➖➖\nBulliesPicks\nSunday, February 15\nNCAAB EXCLUSIVE MAX PLAY\nSan Francisco -3.5 Alternate Line 💎\n100 TO 10,000 LADDER CHALLENGE 🪜\nPLAY #2: San Francisco -3.5 Alternate Line\n(NCAAB)",
        "MRBIG": "MRBIGBETS\n➖➖ ➖➖➖\nMrBigBets\n2/15 college baseball plays\nArkansas state ML -140 1u\nOklahoma ML +105 .5u\n2 more college baseball plays this afternoon"
    }

    print("--- Testing Cleaning Logic ---")
    for mid, text in msgs.items():
        print(f"\n[Message {mid}]")
        print(f"Original: {repr(text[:50])}...")
        
        cleaned = clean_sauce_text(text)
        print(f"Cleaned (Sauce): {repr(cleaned[:50])}...")
        
        mashed = RuleBasedExtractor._clean_mashed_text(cleaned)
        print(f"Mashed (Final): {repr(mashed[:50])}...")

        # split lines
        lines = mashed.split('\n')
        print(f"Lines: {len(lines)}")
        print(f"Sample Line: {lines[2] if len(lines)>2 else lines[0]}")

if __name__ == "__main__":
    test_cleaning()
