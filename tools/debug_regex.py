import re

text = "St Louis/St Bonnies Under 158.5"
pattern = re.compile(
    r"([\(A-Za-z0-9\s\.\-\'\)]+?)\s*[/&]\s*([\(A-Za-z0-9\s\.\-\'\)]+?)\s+(over|under)\s+", re.IGNORECASE
)

match = pattern.search(text)
if match:
    print(f"MATCH: {match.groups()}")
else:
    print("NO MATCH")

# Debug: check what chars are in the string
print(f"Chars: {list(text)}")
