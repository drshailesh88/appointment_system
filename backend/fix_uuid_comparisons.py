#!/usr/bin/env python3
"""
Fix UUID comparison issues in test files.
Converts comparisons like: data["id"] == some_object.id
To: data["id"] == str(some_object.id)
"""
import re
from pathlib import Path

def fix_uuid_comparisons(filepath):
    """Fix UUID comparisons in a test file."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    modified = False
    new_lines = []

    for line in lines:
        original_line = line

        # Pattern: data["field_name"] == test_something.id
        # Should be: data["field_name"] == str(test_something.id)
        # But only if it's not already wrapped in str()
        if '== test_' in line and '.id' in line and 'assert' in line and 'str(' not in line:
            # Find patterns like: == test_xxx.id or == test_xxx_yyy.id
            pattern = r'(==\s+)(test_[a-z_]+\.id)([^"])'
            replacement = r'\1str(\2)\3'
            line = re.sub(pattern, replacement, line)

        # Also handle patterns like: data["xxx_id"] == something.id
        if '_id"]' in line and '==' in line and '.id' in line and 'assert' in line and 'str(' not in line:
            # Match: data["xxx_id"] == object.id
            pattern = r'(data\[["\'][\w_]+["\']\]\s+==\s+)([a-z_]+\.id)(?!\))'
            replacement = r'\1str(\2)'
            line = re.sub(pattern, replacement, line)

        if line != original_line:
            modified = True
        new_lines.append(line)

    if modified:
        with open(filepath, 'w') as f:
            f.writelines(new_lines)
        return True
    return False

def main():
    """Fix all test files."""
    test_dir = Path(__file__).parent / "tests" / "api"
    fixed_files = []

    for test_file in test_dir.glob("test_*.py"):
        if fix_uuid_comparisons(test_file):
            fixed_files.append(test_file.name)
            print(f"Fixed: {test_file.name}")

    if fixed_files:
        print(f"\nTotal files fixed: {len(fixed_files)}")
    else:
        print("No files needed fixing.")

if __name__ == "__main__":
    main()
