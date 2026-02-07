from src.grading.parser import PickParser

def test_parser():
    cases = [
        "Fau +2.5 **",
        "Celtics -5",
        "2u blue jackets ml",
        "Army +12.5"
    ]
    
    for text in cases:
        print(f"--- parsing '{text}' ---")
        p = PickParser.parse(text, "ncaab" if "Fau" in text or "Army" in text else "nba")
        print(f"Original: '{text}'")
        print(f"Parsed Selection: '{p.selection}'")
        print(f"Parsed Line: {p.line}")
        print(f"Parsed Bet Type: {p.bet_type}")
        print("")

if __name__ == "__main__":
    test_parser()
