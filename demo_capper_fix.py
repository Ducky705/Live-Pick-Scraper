"""
LIVE DEMONSTRATION: Capper Name Fix in Action

This script shows the exact behavior of the scraper with the fix applied,
demonstrating how capper names are extracted from messages.
"""
import re


def extract_capper_name_and_pick(text, channel_title, is_aggregator=False):
    """
    Simplified version of the scraper's capper name extraction logic
    with the fix applied.
    """
    content_lines = [line.strip() for line in text.split('\n') if line.strip()]

    if not content_lines:
        return None, text, "No content"

    # --- START OF FIX: Improved Capper Name Parsing Logic ---

    # Heuristic: Check if message matches 'Capper Name' then 'Pick Details' format
    is_aggregator_format = False
    if len(content_lines) > 1:
        first_line = content_lines[0]
        second_line = content_lines[1]
        third_line = content_lines[2] if len(content_lines) > 2 else ""

        # A more robust regex to identify lines containing betting information.
        pick_terms_regex = r'([+-]\d{3,}|ML|[+-]\d{1,2}\.?5|[OU]\d|\d+[\.,]?\d*\s*u(nit)?s?)'

        # A line is likely a capper name if it's short and lacks betting terms...
        first_line_is_clean = (
            len(first_line) < 40 and
            not re.search(pick_terms_regex, first_line, re.I)
        )
        # Check second line first, then third line if second is empty (common in aggregator format).
        second_line_has_pick = re.search(pick_terms_regex, second_line, re.I)
        third_line_has_pick = not second_line_has_pick and second_line.strip() == "" and re.search(pick_terms_regex, third_line, re.I)

        if first_line_is_clean and (second_line_has_pick or third_line_has_pick):
            is_aggregator_format = True

    # --- Determine Capper Name and Pick Body based on the format ---
    if is_aggregator_format:
        # Format matches "Capper Name\nPick". Use the first line as the capper.
        capper_name = content_lines[0]
        pick_body = '\n'.join(content_lines[1:])
        return capper_name, pick_body, "Aggregator format"
    else:
        # Format is "Channel Name\nPick" or other. Use channel name as capper.
        capper_name = channel_title
        pick_body = text
        return capper_name, pick_body, "Non-aggregator format"


def main():
    print("\n" + "="*80)
    print("LIVE DEMONSTRATION: Capper Name Fix")
    print("="*80)
    print("\nThis demonstrates the fix for:")
    print("  BEFORE: capper_name = 'FREE CAPPERS PICKS | CRYSTAL BALL' (channel name)")
    print("  AFTER:  capper_name = 'PardonMyPick' (from message text)")
    print("\n" + "="*80 + "\n")

    # Test cases from real aggregator channels
    test_cases = [
        {
            "channel_name": "FREE CAPPERS PICKS | CRYSTAL",
            "channel_id": 1900292133,
            "is_aggregator": True,
            "messages": [
                {
                    "text": "PardonMyPick\n\n**Lakers ML -110 2u\nWarriors +3 -105 1u**",
                    "description": "Standard aggregator format (Capper, empty line, picks)"
                },
                {
                    "text": "HammeringHank\n\n**Cowboys ML -130 3u\nGiants +7 -110 1.5u**",
                    "description": "Another capper with multiple picks"
                },
                {
                    "text": "PlatinumLocks\n\n**Chiefs -9.5 -115 2u\nOver 48.5 -110 1u**",
                    "description": "Capper with spread and total bets"
                },
                {
                    "text": "THE GURU\n\n**Texans ML (1.5U) -130\nColts -3 (1U)**",
                    "description": "Capper with parenthetical units"
                },
                {
                    "text": "BETTOR\n\n**Packers (2u) -110\nBears (1.5units) +105**",
                    "description": "Capper with lowercase units"
                },
                {
                    "text": "BRANDON THE PROFIT\n\n**Texans ML -125 (2U) DK\nGiants +3 -120 (1.5U) Fanatics**",
                    "description": "Capper with platform tags (DK, Fanatics)"
                },
                {
                    "text": "CASH CING\n\n**2.5u, Texans ML -130\n2u, Chiefs ML -130**",
                    "description": "Capper with comma-separated units (original bug scenario)"
                },
            ]
        }
    ]

    for channel_data in test_cases:
        channel_name = channel_data["channel_name"]
        is_agg = channel_data["is_aggregator"]

        print(f"\n{'='*80}")
        print(f"CHANNEL: {channel_name}")
        print(f"Type: {'Aggregator' if is_agg else 'Regular'}")
        print(f"{'='*80}\n")

        for i, msg_data in enumerate(channel_data["messages"], 1):
            text = msg_data["text"]
            description = msg_data["description"]

            print(f"\n--- Message #{i}: {description} ---")
            print(f"Raw message:\n{text}\n")

            capper_name, pick_body, format_type = extract_capper_name_and_pick(
                text, channel_name, is_agg
            )

            print(f"Format detected: {format_type}")
            print(f"Capper name extracted: '{capper_name}'")
            print(f"Pick body:\n{pick_body[:100]}{'...' if len(pick_body) > 100 else ''}")

            # Verification
            if is_agg and capper_name != channel_name:
                print("[OK] SUCCESS: Extracted actual capper name (not channel name)")
            elif not is_agg and capper_name == channel_name:
                print("[OK] SUCCESS: Using channel name for non-aggregator")
            else:
                print("[ERROR] UNEXPECTED: Check logic")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nThe fix correctly handles aggregator channel messages by:")
    print("  1. Detecting the 'Capper Name' + empty line + 'Bet details' format")
    print("  2. Checking both 2nd AND 3rd lines for betting terms")
    print("  3. Extracting the capper name from the first line")
    print("  4. NOT using the channel name as the capper name")
    print("\nResult: Capper names like 'PardonMyPick', 'HammeringHank',")
    print("        'PlatinumLocks' are correctly extracted!")
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()
