import re

RE_ODDS_PATTERN = re.compile(r"(?<!\d)[+-]\s*\d{1,4}(?:\.\d+)?(?!\))")
RE_ML_WORD = re.compile(r"\bml\b")
RE_OU_PATTERN = re.compile(r"\b(o|u|over|under)\s*\d", re.IGNORECASE)
RE_PROP_AGS_CHECK = re.compile(r"\b(Anytime Goal Scorer|AGS|Score|Scorer)\b", re.IGNORECASE)

def has_pick_indicators(text):
    text_lower = text.lower()
    if "moneyline" in text_lower or "spread" in text_lower or "parlay" in text_lower:
        return True
    if RE_ML_WORD.search(text_lower):
        return True

    has_digit = False
    for c in text:
        if c.isdigit():
            has_digit = True
            break
    if not has_digit:
        return False

    if RE_ODDS_PATTERN.search(text):
        return True

    if RE_OU_PATTERN.search(text_lower):
        return True

    if ":" in text or "goal" in text_lower or "score" in text_lower:
        keywords = ["pts", "reb", "ast", "threes", "yards", "td", "goal", "score", "scorer", "win"]
        for k in keywords:
            if k in text_lower:
                return True

    return False

cases = [
    "Your Daily Capper",
    "Game/Time League Signal Play Win% Units Score SameSideCount Verdict Tier",
    "Parlay",
    "Parlay ML"
]

print("--- REGEX TEST ---")
for text in cases:
    print(f"Testing: '{text}'")
    match = RE_ODDS_PATTERN.search(text)
    if match:
        print(f"  ODDS MATCH: '{match.group()}'")
    else:
        print("  ODDS NO MATCH")
    
    ind = has_pick_indicators(text)
    print(f"  INDICATORS: {ind}\n")
