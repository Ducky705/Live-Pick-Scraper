from src.rule_based_extractor import RuleBasedExtractor
from src.grading.schema import BetType

messages = [
    # Case 1: Your Daily Capper (Merge Issue?)
    {"id": "msg1", "text": "Your Daily Capper\n2u - Texas ML"},
    
    # Case 2: Header (Validation Issue?)
    {"id": "msg2", "text": "Game/Time League Signal Play Win% Units Score SameSideCount Verdict Tier"},
    
    # Case 3: Spaced Odds (Regex Issue?)
    {"id": "msg3", "text": "4* Magic - 1.5"},
    
    # Case 4: Parenthesis Units (Prefix Issue?)
    {"id": "msg4", "text": "Minnesota Golden Gophers +5.5 -110 (2u, 12:00e)"} 
]

print("--- DEBUGGING EXTRACTION ---\n")
picks, remaining = RuleBasedExtractor.extract(messages)

print(f"\nExtracted {len(picks)} picks:")
for p in picks:
    print(f"Msg {p['message_id']}: {p['pick']} (Units: {p['units']})")
    print(f"  -> Raw: {p['_source_text']}")
    print(f"  -> Confidence: {p['confidence']}")
    print("-" * 20)

print("\n--- REMAINING MESSAGES ---")
for m in remaining:
    print(f"Msg {m['id']} Skipped")
