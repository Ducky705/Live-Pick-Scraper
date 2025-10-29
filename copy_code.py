import os
import subprocess

def get_file_tree(path):
    tree = []
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 2 * level
        tree.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            tree.append(f"{subindent}{file}")
    return '\n'.join(tree)

def copy_to_clipboard(text):
    subprocess.run(['clip'], input=text, text=True, shell=True)

def main():
    code_extensions = ('.py', '.html', '.js', '.css')
    code_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith(code_extensions):
                code_files.append(os.path.join(root, file))

    content = get_file_tree('.') + '\n\n' + '='*50 + '\n\n'

    for file_path in code_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            content += f"File: {file_path}\n{file_content}\n\n{'='*50}\n\n"
        except Exception as e:
            content += f"File: {file_path}\nError reading file: {e}\n\n{'='*50}\n\n"

    copy_to_clipboard(content)
    print("Code files and file tree copied to clipboard.")

if __name__ == "__main__":
    main()