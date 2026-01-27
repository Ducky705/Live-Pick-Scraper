from src.grading.parser import PickParser
from src.grading.schema import BetType


def test(text):
    p = PickParser.parse(text, "NFL")
    print(f"Text: '{text}'")
    print(f"Selection: '{p.selection}'")
    print(f"Type: {p.bet_type}")
    print(f"Odds: {p.odds}")
    print(f"Line: {p.line}")
    print("-" * 20)


test("1* Oilers -175, 10:05 pm")
test("Commanders +3.5 (-115)")
test("Paddy Pimblett ML -205")
