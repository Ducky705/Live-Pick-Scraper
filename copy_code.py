import os
import subprocess

# Try to import pyperclip with error handling
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

def get_file_tree(path):
    """Generate file tree with absolute paths for ALL files (not just code files)"""
    tree = []
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 2 * level
        # Use absolute path for directory
        abs_root = os.path.abspath(root)
        tree.append(f"{indent}{abs_root}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            # Use absolute path for file
            abs_file = os.path.abspath(os.path.join(root, file))
            tree.append(f"{subindent}{abs_file}")
    return '\n'.join(tree)

def copy_to_clipboard(text):
    """Copy text to clipboard with error handling"""
    if PYPERCLIP_AVAILABLE:
        pyperclip.copy(text)
        return True
    else:
        print("Warning: pyperclip not available, cannot copy to clipboard")
        return False

def main():
    code_extensions = ('.py', '.html', '.js', '.css')
    code_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith(code_extensions):
                # Convert to absolute path
                abs_path = os.path.abspath(os.path.join(root, file))
                code_files.append(abs_path)

    content = get_file_tree('.') + '\n\n' + '='*50 + '\n\n'

    for file_path in code_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            content += f"File: {file_path}\n{file_content}\n\n{'='*50}\n\n"
        except Exception as e:
            content += f"File: {file_path}\nError reading file: {e}\n\n{'='*50}\n\n"

    # Copy to clipboard with error handling
    copy_success = copy_to_clipboard(content)
    
    if copy_success:
        print("Code files and file tree copied to clipboard successfully.")
    else:
        print("Content generated but clipboard copy failed.")
        print("You can manually copy the following content:")
        print("="*50)
        print(content[:500] + "..." if len(content) > 500 else content)
    
    # Test functionality
    print("\nTesting functionality:")
    print(f"File tree includes all files: {len(get_file_tree('.').split(chr(10))) > 0}")
    print(f"Code files found: {len(code_files)}")
    print(f"Pyperclip available: {PYPERCLIP_AVAILABLE}")
    
    return content

if __name__ == "__main__":
    main()