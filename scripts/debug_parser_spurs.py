
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.grading.parser import PickParser

text = "1Q Spurs -1.5 **"
parsed = PickParser.parse(text)
print(f"Text: {text}")
print(f"League: {parsed.league}")
print(f"Period: {parsed.period}")
print(f"Bet Type: {parsed.bet_type}")

text2 = "Norte Dame +18 **"
parsed2 = PickParser.parse(text2)
print(f"\nText: {text2}")
print(f"League: {parsed2.league}")
