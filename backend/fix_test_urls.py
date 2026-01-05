#!/usr/bin/env python3
"""
Bulk fix test files to add trailing slashes to POST/PUT/PATCH/DELETE URLs.
"""
import re
import os
from pathlib import Path

def fix_test_file(filepath):
    """Fix trailing slashes in a test file."""
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content

    # Pattern to match client.post/put/patch/delete without trailing slash
    # Match lines like: client.post("/api/v1/something",
    # But not if they already have a trailing slash or query parameters
    patterns = [
        # Match POST/PUT/PATCH/DELETE without trailing slash (but not with query params or ID at end)
        (r'(client\.(post|put|patch|delete)\(\s*["\'])(/api/v1/[a-z_/-]+[a-z_-])(["\'])', r'\1\3/\4'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all test files."""
    test_dir = Path(__file__).parent / "tests" / "api"
    fixed_files = []

    for test_file in test_dir.glob("test_*.py"):
        if fix_test_file(test_file):
            fixed_files.append(test_file.name)
            print(f"Fixed: {test_file.name}")

    if fixed_files:
        print(f"\nTotal files fixed: {len(fixed_files)}")
    else:
        print("No files needed fixing.")

if __name__ == "__main__":
    main()
