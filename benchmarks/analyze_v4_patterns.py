import json
import re
from collections import Counter
import sys
import os

V4_PATH = "benchmark/dataset/golden_set_v4.json"

def normalize_fingerprint(text):
    """
    Convert text to a structural fingerprint.
    1. Lowercase
    2. Remove Emojis/Special Chars
    3. Replace specific entity types with tokens.
    """
    # 0. Basic Cleanup
    # Keep only alphanumeric, common punctuation, newlines
    clean = re.sub(r"[^\w\s\.\(\)\+\-:\/]", "", text)
    
    # 1. Tokenize Numbers (Lines/Odds)
    # Odds: (-110, +200) -> <ODDS>
    # Line: -5.5, +3 -> <LINE>
    
    # We need to be careful. 
    # Replace anything looking like odds first (3 digits)
    # This is a Rough Heuristic to see structure similarity
    
    tokenized = clean
    
    # Replace Odds: ([-+]\d{3,}) -> <ODDS>
    tokenized = re.sub(r"[\(]?[\+\-]\d{3,}[\)]?", " <ODDS> ", tokenized)
    
    # Replace Lines: ([-+]\d+\.?\d*) -> <LINE>
    # Be careful not to clobber dates or times if possible, but for betting text usually fine
    tokenized = re.sub(r"[\+\-]?\d+\.?\d*", " <NUM> ", tokenized)
    
    # Replace Team-like words? 
    # Hard to distinct words from Teams without NER, but we can look at "Structure"
    # Collapse sequence of words -> <TEXT>
    tokenized = re.sub(r"[a-zA-Z]+", "<TEXT>", tokenized)
    
    # Collapse multiple <TEXT> into one
    tokenized = re.sub(r"(<TEXT>\s*)+", "<TEXT> ", tokenized)
    
    # Collapse multiple spaces
    tokenized = re.sub(r"\s+", " ", tokenized).strip()
    
    return tokenized

def analyze_patterns():
    if not os.path.exists(V4_PATH):
        print("V4 Data not found.")
        return

    with open(V4_PATH, "r") as f:
        data = json.load(f)
        
    fingerprints = []
    
    print(f"Analyzing {len(data)} samples...")
    
    for item in data:
        text = item.get("text", "")
        # Split multiline picks? usually V4 items are single picks or blocks
        # Let's treat lines individually as that's how a parser works
        lines = text.split('\n')
        for line in lines:
            if not line.strip(): continue
            # skip noise lines?
            if len(line) < 5: continue
            
            fp = normalize_fingerprint(line)
            fingerprints.append(fp)
            
    counts = Counter(fingerprints)
    
    total_lines = len(fingerprints)
    unique_patterns = len(counts)
    
    print(f"\nTotal Lines Processed: {total_lines}")
    print(f"Unique Patterns Found: {unique_patterns}")
    print(f"Pattern Variety Ratio: {unique_patterns/total_lines:.2f} (Lower is better for Templates)")
    
    print("\nTop 10 Patterns:")
    cumulative = 0
    for pattern, count in counts.most_common(10):
        cumulative += count
        print(f"{count:3d} ({count/total_lines:.1%}): {pattern}")
        
    print(f"\nTop 10 Coverage: {cumulative/total_lines:.1%}")

if __name__ == "__main__":
    analyze_patterns()
