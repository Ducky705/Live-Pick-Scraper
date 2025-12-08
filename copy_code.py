#!/usr/bin/env python3
"""
copy_code.py - Recursively scans project directory and copies combined tree + file contents to clipboard
"""

import os
import sys
from pathlib import Path
import pyperclip
from typing import List, Set, Tuple

# Configuration
BINARY_EXTENSIONS = {'.dll', '.exe', '.so', '.dylib', '.jar', '.bin', '.jpg', '.png', '.gif', '.bmp', '.pdf', '.zip', '.rar', '.ttf', '.whl', '.egg', '.deb', '.rpm', '.msi', '.dmg', '.iso'}
MAX_LINES = 10000
MAX_SIZE_KB = 500
INCLUDE_EXTENSIONS = {'.py', '.js', '.html', '.css'}

def is_binary_file(file_path: Path) -> bool:
    """Enhanced binary detection using both extension and file headers"""
    # Check extension patterns
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    
    # Check file headers for binary content
    try:
        with open(file_path, 'rb') as f:
            # Read first 1024 bytes to check for binary content
            header = f.read(1024)
            if b'\0' in header:  # Null bytes indicate binary
                return True
    except Exception:
        pass
    
    return False

def should_include_file(file_path: Path, root_path: Path) -> bool:
    """Check if file should be included based on inclusion rules"""
    # Only process files in src/ directory and root directory
    relative_path = file_path.relative_to(root_path)
    
    # Check if file is in root directory
    if len(relative_path.parts) == 1:
        return True
    
    # Check if file is in src/ directory
    if relative_path.parts[0] == 'src':
        return True
    
    return False

def read_file_safely(file_path: Path) -> Tuple[str, bool]:
    """Read file content safely with size and line limits"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Check line count
        if len(lines) > MAX_LINES:
            lines = lines[:MAX_LINES]
            lines.append(f"\n# ... (truncated to {MAX_LINES} lines)\n")
        
        # Check file size
        content = ''.join(lines)
        if len(content.encode('utf-8')) > MAX_SIZE_KB * 1024:
            content = content[:MAX_SIZE_KB * 1024]
            content += f"\n# ... (truncated to {MAX_SIZE_KB}KB)\n"
        
        return content, True
    except Exception as e:
        return f"# Error reading file: {e}\n", False

def get_project_tree(root_path: Path) -> str:
    """Generate directory tree structure for src/ and root only"""
    tree_lines = []
    root_path = Path(root_path)
    
    def _build_tree(path: Path, prefix: str = ""):
        try:
            # Only include src/ and files in root
            if path == root_path:
                items = sorted([p for p in path.iterdir() if p.name in ['src'] or (p.is_file() and p.suffix in INCLUDE_EXTENSIONS)])
            elif path.name == 'src':
                items = sorted([p for p in path.iterdir() if p.is_file() and p.suffix in INCLUDE_EXTENSIONS])
            else:
                items = []
        except PermissionError:
            return
        
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            tree_lines.append(f"{prefix}{current_prefix}{item.name}")
            
            if item.is_dir():
                next_prefix = prefix + ("    " if is_last else "│   ")
                _build_tree(item, next_prefix)
    
    tree_lines.append(f"{root_path.name}/")
    _build_tree(root_path)
    return "\n".join(tree_lines)

def get_file_contents(root_path: Path) -> Tuple[str, List[str], int]:
    """Read and concatenate contents of all code files with verbose logging"""
    contents = []
    included_files = []
    excluded_count = 0
    total_lines = 0
    total_chars = 0
    
    # Process root directory files
    print("Processing root directory files...")
    for file_path in root_path.iterdir():
        if file_path.is_file():
            if should_include_file(file_path, root_path):
                if file_path.suffix.lower() in INCLUDE_EXTENSIONS:
                    if not is_binary_file(file_path):
                        file_content, success = read_file_safely(file_path)
                        if success:
                            print(f"  ✓ {file_path}")
                            included_files.append(str(file_path.relative_to(root_path)))
                            contents.append(f"# {file_path.relative_to(root_path)}")
                            contents.append(file_content)
                            contents.append("# ---END OF FILE---\n")
                            
                            total_lines += len(file_content.split('\n'))
                            total_chars += len(file_content)
                    else:
                        print(f"  ✗ {file_path} (binary file)")
                        excluded_count += 1
                else:
                    print(f"  ✗ {file_path} (unsupported extension: {file_path.suffix})")
                    excluded_count += 1
            else:
                print(f"  ✗ {file_path} (outside allowed directories)")
                excluded_count += 1
    
    # Process src/ directory
    src_path = root_path / 'src'
    if src_path.exists():
        print(f"\nProcessing {src_path} directory...")
        for file_path in src_path.iterdir():
            if file_path.is_file():
                if should_include_file(file_path, root_path):
                    if file_path.suffix.lower() in INCLUDE_EXTENSIONS:
                        if not is_binary_file(file_path):
                            file_content, success = read_file_safely(file_path)
                            if success:
                                print(f"  ✓ {file_path}")
                                included_files.append(str(file_path.relative_to(root_path)))
                                contents.append(f"# {file_path.relative_to(root_path)}")
                                contents.append(file_content)
                                contents.append("# ---END OF FILE---\n")
                                
                                total_lines += len(file_content.split('\n'))
                                total_chars += len(file_content)
                        else:
                            print(f"  ✗ {file_path} (binary file)")
                            excluded_count += 1
                    else:
                        print(f"  ✗ {file_path} (unsupported extension: {file_path.suffix})")
                        excluded_count += 1
                else:
                    print(f"  ✗ {file_path} (outside allowed directories)")
                    excluded_count += 1
    
    return ''.join(contents), included_files, excluded_count, total_lines, total_chars

def check_pyperclip() -> bool:
    """Check if pyperclip is available and working"""
    try:
        test_text = "test"
        pyperclip.copy(test_text)
        copied_text = pyperclip.paste()
        return copied_text == test_text
    except Exception:
        return False

def main():
    """Main function to generate and copy project code"""
    project_root = Path(__file__).parent
    
    # Check pyperclip availability
    if not check_pyperclip():
        print("Error: pyperclip is not available or not working.")
        print("Please install it with: pip install pyperclip")
        sys.exit(1)
    
    try:
        # Generate directory tree
        tree = get_project_tree(project_root)
        
        # Get file contents with verbose logging
        file_contents, included_files, excluded_count, total_lines, total_chars = get_file_contents(project_root)
        
        # Combine output
        output = f"""
=== PROJECT TREE ===
{tree}

=== FILE CONTENTS ===
{file_contents}
"""
        
        # Copy to clipboard
        pyperclip.copy(output)
        
        # Print success message
        print(f"\n{'='*50}")
        print("Successfully copied project code to clipboard!")
        print(f"{'='*50}")
        print("Directories scanned:")
        print("  - Root directory (where copy_code.py resides)")
        print("  - src/ directory")
        print(f"\nIncluded files ({len(included_files)}):")
        for file in included_files:
            print(f"  - {file}")
        print(f"\nExcluded files: {excluded_count}")
        print(f"\nStatistics:")
        print(f"   - Total lines: {total_lines}")
        print(f"   - Total characters: {total_chars:,}")
        print(f"   - Included file types: {', '.join(sorted(INCLUDE_EXTENSIONS))}")
        print(f"   - Ignored directories: bin/, build/, static/, tesseract_bin/, tessdata/")
        print(f"   - Binary patterns: {', '.join(sorted(set(BINARY_EXTENSIONS)))}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()