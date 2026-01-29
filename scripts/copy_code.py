#!/usr/bin/env python3
"""
copy_code.py - Copies full project context to clipboard for AI consumption.
Includes: Full project tree, file names, and all user-made code content.
Uses macOS native pbcopy (no dependencies).
"""

import subprocess
from pathlib import Path

# === CONFIGURATION ===

# File extensions to include content for
CODE_EXTENSIONS = {".py", ".js", ".html", ".css", ".json", ".md", ".txt", ".yaml", ".yml", ".toml"}

# Files to always exclude (sensitive/generated)
EXCLUDE_FILES = {".env", ".gitignore", "copy_code.py", ".DS_Store", "user_session.session"}

# Directories to skip in tree AND content
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "temp_images",
    ".idea",
    ".vscode",
    "eggs",
    "*.egg-info",
    "htmlcov",
    ".pytest_cache",
    ".mypy_cache",
}

# Directories to show in tree but NOT read content from
TREE_ONLY_DIRS = {"build", "dist", "tessdata", "tesseract_bin"}

# Directories containing user code (will read file contents)
CODE_DIRS = {"src", "static", "templates"}

# Max file size to include (prevents huge files)
MAX_FILE_SIZE_KB = 400


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using macOS pbcopy"""
    try:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode("utf-8"))
        return process.returncode == 0
    except Exception as e:
        print(f"Clipboard error: {e}")
        return False


def should_skip_dir(dir_name: str) -> bool:
    """Check if directory should be completely skipped"""
    if dir_name in EXCLUDE_DIRS:
        return True
    if dir_name.endswith(".egg-info"):
        return True
    return False


def generate_full_tree(root_path: Path, max_depth: int = 4) -> str:
    """Generate complete project directory tree"""
    tree_lines = [f"📁 {root_path.name}/"]

    def walk_dir(path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            tree_lines.append(f"{prefix}└── ...")
            return

        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return

        # Filter out excluded directories
        items = [item for item in items if not (item.is_dir() and should_skip_dir(item.name))]

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "

            if item.is_dir():
                # Mark tree-only dirs
                marker = " 📦" if item.name in TREE_ONLY_DIRS else ""
                tree_lines.append(f"{prefix}{connector}{item.name}/{marker}")

                # Recurse unless it's a tree-only dir
                if item.name not in TREE_ONLY_DIRS:
                    extension = "    " if is_last else "│   "
                    walk_dir(item, prefix + extension, depth + 1)
            elif item.name not in EXCLUDE_FILES:
                size_kb = item.stat().st_size / 1024
                size_str = f" ({size_kb:.1f}KB)" if size_kb > 10 else ""
                tree_lines.append(f"{prefix}{connector}{item.name}{size_str}")

    walk_dir(root_path)
    return "\n".join(tree_lines)


def is_binary_file(file_path: Path) -> bool:
    """Check if file contains binary content"""
    try:
        with open(file_path, "rb") as f:
            header = f.read(1024)
            if b"\0" in header:
                return True
    except Exception:
        pass
    return False


def should_include_content(file_path: Path, root_path: Path) -> tuple[bool, str]:
    """Determine if we should include this file's content"""
    relative = file_path.relative_to(root_path)
    filename = file_path.name

    # Explicit exclusions
    if filename in EXCLUDE_FILES:
        return False, "excluded"

    # Check extension
    if file_path.suffix.lower() not in CODE_EXTENSIONS:
        return False, "binary/unsupported"

    # Check file size
    try:
        size_kb = file_path.stat().st_size / 1024
        if size_kb > MAX_FILE_SIZE_KB:
            return False, f"too large ({size_kb:.0f}KB)"
    except:
        pass

    # Root directory files
    if len(relative.parts) == 1:
        return True, "root"

    # Code directories
    if relative.parts[0] in CODE_DIRS:
        return True, relative.parts[0]

    return False, "outside code dirs"


def read_file_safely(file_path: Path) -> tuple[str, bool]:
    """Read file content safely"""
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return content, True
    except Exception as e:
        return f"# Error reading: {e}\n", False


def collect_code_files(root_path: Path) -> list[Path]:
    """Collect all files whose content should be included"""
    files = []

    # Root directory
    for item in root_path.iterdir():
        if item.is_file():
            include, _ = should_include_content(item, root_path)
            if include and not is_binary_file(item):
                files.append(item)

    # Code directories (recursive)
    for dir_name in CODE_DIRS:
        dir_path = root_path / dir_name
        if dir_path.exists():
            for sub_path in dir_path.rglob("*"):
                if sub_path.is_file():
                    # Skip excluded parent dirs
                    skip = any(part in EXCLUDE_DIRS for part in sub_path.relative_to(root_path).parts)
                    if skip:
                        continue

                    include, _ = should_include_content(sub_path, root_path)
                    if include and not is_binary_file(sub_path):
                        files.append(sub_path)

    return sorted(files, key=lambda p: str(p.relative_to(root_path)))


def main():
    # Script is in scripts/, so go up one level to project root
    project_root = Path(__file__).parent.parent

    print("🔍 Generating AI-ready project context...")
    print(f"   Root: {project_root}\n")

    # === SECTION 1: PROJECT OVERVIEW ===
    output = []
    output.append("=" * 70)
    output.append("🚀 PROJECT CONTEXT FOR AI")
    output.append("=" * 70)
    output.append("")
    output.append(f"Project: {project_root.name}")
    output.append("Type: Python + JavaScript Web Application")
    output.append("Stack: Flask (Python backend), Vanilla JS frontend, Tailwind CSS")
    output.append("")

    # === SECTION 2: FULL PROJECT TREE ===
    output.append("=" * 70)
    output.append("📂 FULL PROJECT STRUCTURE")
    output.append("=" * 70)
    output.append("")
    tree = generate_full_tree(project_root)
    output.append(tree)
    output.append("")
    output.append("Legend: 📦 = build artifacts (content not included)")
    output.append("")

    # === SECTION 3: KEY FILES SUMMARY ===
    output.append("=" * 70)
    output.append("📋 KEY FILES OVERVIEW")
    output.append("=" * 70)
    output.append("")
    output.append("Backend (Python):")
    output.append("  • main.py           - Flask server, API endpoints")
    output.append("  • src/telegram_client.py - Telegram API integration")
    output.append("  • src/prompt_builder.py  - AI prompt generation for pick extraction")
    output.append("  • src/grader.py          - Bet result grading logic")
    output.append("  • src/score_fetcher.py   - ESPN API for live scores")
    output.append("  • src/supabase_client.py - Database operations")
    output.append("  • src/capper_matcher.py  - Fuzzy matching for capper names")
    output.append("")
    output.append("Frontend (JavaScript):")
    output.append("  • static/js/swiss_app.js - Main SPA logic (all UI interactions)")
    output.append("  • templates/index.html   - Single-page HTML structure")
    output.append("  • static/css/swiss.css   - Custom styles (Swiss/Brutalist design)")
    output.append("")

    # === SECTION 4: FILE CONTENTS ===
    output.append("=" * 70)
    output.append("📄 FILE CONTENTS")
    output.append("=" * 70)
    output.append("")

    files = collect_code_files(project_root)
    total_lines = 0
    total_chars = 0

    for file_path in files:
        rel_path = file_path.relative_to(project_root)
        content, success = read_file_safely(file_path)

        if success:
            print(f"  ✓ {rel_path}")
            lines = len(content.split("\n"))
            total_lines += lines
            total_chars += len(content)

            output.append("─" * 70)
            output.append(f"📄 FILE: {rel_path}")
            output.append(f"   Lines: {lines} | Size: {len(content):,} chars")
            output.append("─" * 70)
            output.append("")
            output.append(content)
            output.append("")
        else:
            print(f"  ✗ {rel_path}")

    # Combine
    full_output = "\n".join(output)

    # Copy to clipboard
    if copy_to_clipboard(full_output):
        print(f"\n{'=' * 50}")
        print("✅ COPIED TO CLIPBOARD!")
        print(f"{'=' * 50}")
    else:
        print("\n⚠️  Clipboard failed. Printing to stdout instead.")
        print(full_output)

    # Stats
    print("\n📊 Statistics:")
    print(f"   Files included:  {len(files)}")
    print(f"   Total lines:     {total_lines:,}")
    print(f"   Total chars:     {total_chars:,}")
    print(f"   Approx tokens:   ~{total_chars // 4:,}")
    print(f"\n📁 Code directories: {', '.join(sorted(CODE_DIRS))}")
    print(f"🚫 Excluded: {', '.join(sorted(EXCLUDE_FILES))}")


if __name__ == "__main__":
    main()
