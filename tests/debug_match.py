import difflib


def test_match():
    target = "Oklahoma St"
    candidates = [
        "Oklahoma Sooners",
        "Oklahoma State Cowboys",
        "Ohio State Buckeyes",
        "Oregon State Beavers",
    ]

    print(f"Target: {target}")
    best_score = 0
    best_match = None

    for c in candidates:
        # Current logic
        s = difflib.SequenceMatcher(None, c.lower(), target.lower()).ratio()
        print(f"  vs '{c}': {s:.4f}")
        if s > best_score:
            best_score = s
            best_match = c

    print(f"Winner: {best_match}")


test_match()
