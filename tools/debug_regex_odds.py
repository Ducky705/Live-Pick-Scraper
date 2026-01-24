
import re

text = "St Bonaventure +7.5 (Odds: -111)"
pattern = re.compile(r'\((?:odds:?\s*)?([+-]\d{3,})\)', re.IGNORECASE)

match = pattern.search(text)
if match:
    print(f"MATCH: {match.group(1)}")
else:
    print("NO MATCH")
    
# Test trailing
text2 = "Pick -110"
pattern2 = re.compile(r'\s([+-]\d{3,})(?:\s|$)')
match2 = pattern2.search(text2)
if match2:
    print(f"MATCH 2: {match2.group(1)}")
else:
    print("NO MATCH 2")
