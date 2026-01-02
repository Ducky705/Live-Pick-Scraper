import shlex

scenarios = [
    'tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-.,/:()@#$%"',
]

for s in scenarios:
    print(f"\nTesting: {s}")
    try:
        shlex.split(s, posix=False)
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
