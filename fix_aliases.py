
filename = r"d:\Programs\Sports Betting\TelegramScraper\v0.0.15\src\team_aliases.py"

with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the conflict marker
marker_index = -1
for i, line in enumerate(lines):
    if line.strip() == "=======":
        marker_index = i
        break

if marker_index != -1:
    print(f"Found marker at line {marker_index + 1}. Truncating file...")
    new_lines = lines[:marker_index]
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("File truncated successfully.")
else:
    print("Marker not found. Checking if file is already fixed.")
