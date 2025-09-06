# Scripts Directory

This directory contains utility scripts for the Krill project.

## clean_whitespace.py

A Python script that automatically cleans up whitespace issues in code files.

### Features

- Removes trailing whitespace from all lines
- Reduces multiple consecutive blank lines to a maximum of 2
- Ensures files end with a single newline
- Supports Python, HTML, JavaScript, CSS, YAML, and JSON files
- Automatically ignores common directories like `.git`, `__pycache__`, `node_modules`, etc.

### Usage

```bash
# Clean all files in the project
python3 scripts/clean_whitespace.py

# Clean specific files or directories
python3 scripts/clean_whitespace.py krill/person/views.py
python3 scripts/clean_whitespace.py krill/templates/

# Using Makefile
make clean-whitespace
make lint
```

### Integration

The script is integrated into the development workflow:

- **Pre-commit hook**: Automatically runs before each commit
- **Makefile targets**: `make clean-whitespace` and `make lint`
- **Manual execution**: Can be run anytime during development

### Pre-commit Hook

The pre-commit hook (`.git/hooks/pre-commit`) automatically runs the whitespace cleanup before each commit. If files are modified during cleanup, the commit is aborted and you'll need to review and commit again.

This ensures that all committed code has consistent whitespace formatting.
