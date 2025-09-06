#!/usr/bin/env python3
"""
Whitespace cleanup script for the Krill project.
Removes trailing whitespace and excessive blank lines from Python and HTML files.
"""

import os
import re
import sys
from pathlib import Path


def clean_file(file_path):
    """Clean whitespace in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in content.splitlines()]

        # Remove multiple consecutive empty lines (keep max 2)
        cleaned_lines = []
        empty_count = 0
        for line in lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    cleaned_lines.append(line)
            else:
                empty_count = 0
                cleaned_lines.append(line)

        # Ensure file ends with single newline
        cleaned_content = '\n'.join(cleaned_lines)
        if cleaned_content and not cleaned_content.endswith('\n'):
            cleaned_content += '\n'

        # Only write if content changed
        if cleaned_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            return True

        return False

    except Exception as e:
        print(f"Error cleaning {file_path}: {e}")
        return False


def find_files_to_clean(root_dir):
    """Find Python and HTML files to clean."""
    patterns = ['*.py', '*.html', '*.js', '*.css', '*.yml', '*.yaml', '*.json']
    files = []

    for pattern in patterns:
        files.extend(Path(root_dir).rglob(pattern))

    # Filter out files in common ignore directories
    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env'}
    filtered_files = []

    for file_path in files:
        # Check if any parent directory is in ignore list
        if not any(part in ignore_dirs for part in file_path.parts):
            filtered_files.append(file_path)

    return filtered_files


def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Clean specific files/directories
        paths = sys.argv[1:]
    else:
        # Clean entire project
        paths = ['.']

    total_files = 0
    cleaned_files = 0

    for path in paths:
        if os.path.isfile(path):
            # Single file
            if clean_file(path):
                print(f"Cleaned: {path}")
                cleaned_files += 1
            total_files += 1
        elif os.path.isdir(path):
            # Directory
            files = find_files_to_clean(path)
            for file_path in files:
                if clean_file(file_path):
                    print(f"Cleaned: {file_path}")
                    cleaned_files += 1
                total_files += 1

    print(f"\nSummary: Cleaned {cleaned_files} out of {total_files} files")

    if cleaned_files > 0:
        print("Whitespace cleanup completed!")
        return 0
    else:
        print("No files needed cleaning.")
        return 0


if __name__ == '__main__':
    sys.exit(main())
