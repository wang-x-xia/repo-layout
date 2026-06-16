# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyyaml",
# ]
# ///

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

from repo_layout_lib.file_tree import build_file_tree
from repo_layout_lib.error import ErrorCollector
from repo_layout_lib.yaml_utils import dump

# Error codes
ERROR_FILE_NOT_FOUND = "file_not_found"

# Set stdout encoding to UTF-8 for Windows compatibility
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Generate file tree structure in YAML format')
    parser.add_argument('path', nargs='?', default=os.getcwd(),
                       help='Path to the directory to scan (default: current directory)')
    parser.add_argument('--no-gitignore', action='store_true',
                       help='Disable .gitignore filtering (default: enabled)')
    parser.add_argument('--tags', nargs='*', default=['standard'],
                       help='Tags to filter file display (default: standard, use empty list to show all files)')

    args = parser.parse_args()
    root_path = args.path
    use_gitignore = not args.no_gitignore
    tags = args.tags

    error_collector = ErrorCollector()
    script_path = Path(__file__)

    try:
        # Build file tree - unified entry point that handles all steps internally
        tree = build_file_tree(
            root_path=root_path,
            use_gitignore=use_gitignore,
            tags=tags,
            script_path=script_path,
            locale="zh-CN",
            error_collector=error_collector
        )

        # Output as YAML with metadata sorting
        yaml_output = dump(tree)
        print(yaml_output)

        # Output all collected errors and warnings
        error_collector.output()

        return error_collector.get_exit_code()
    except FileNotFoundError as e:
        error_collector.add_error(ERROR_FILE_NOT_FOUND, {"path": str(e)})
        error_collector.output()
        return 1
    except Exception as e:
        # Catch-all for unexpected errors
        error_collector.add_error("unknown_error", {"message": str(e)})
        error_collector.output()
        return 1

if __name__ == "__main__":
    sys.exit(main())