import os
import glob
import re

def resolve_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if "<<<<<<< Updated upstream" not in content:
        return False

    print(f"Resolving {filepath}...")

    # Pattern to match the conflict block
    # Uses dotall to match newlines
    # matches: <<<<<<< ... ======= (content) >>>>>>> ...
    # We want to keep (content)
    
    # We need to handle multiple conflicts in one file?
    # The regex approach might be tricky if nested or multiple.
    # Let's do a line-by-line state machine.
    
    lines = content.splitlines(keepends=True)
    new_lines = []
    
    state = "NORMAL" # NORMAL, UPSTREAM, STASHED
    
    for line in lines:
        if line.startswith("<<<<<<< Updated upstream"):
            state = "UPSTREAM"
            continue
        elif line.startswith("======="):
            if state == "UPSTREAM":
                state = "STASHED"
                continue
            else:
                # Might be a literal ======= in code? Unlikely in python source at start of line
                # But safer to check state
                new_lines.append(line)
        elif line.startswith(">>>>>>> Stashed changes"):
            if state == "STASHED":
                state = "NORMAL"
                continue
            else:
                new_lines.append(line)
        else:
            if state == "NORMAL":
                new_lines.append(line)
            elif state == "UPSTREAM":
                pass # Ignore upstream lines
            elif state == "STASHED":
                new_lines.append(line) # Keep stashed lines
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return True

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(root_dir, "src")
    
    files = glob.glob(os.path.join(src_dir, "**/*.py"), recursive=True)
    
    resolved_count = 0
    for file in files:
        if resolve_file(file):
            resolved_count += 1
            
    print(f"Resolved {resolved_count} files.")

if __name__ == "__main__":
    main()
