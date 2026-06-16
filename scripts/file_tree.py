# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyyaml",
# ]
# ///

import os
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, Set
from repo_layout_lib.git import is_git_repo, get_git_ignored_files

def build_file_tree(root_path: str, use_gitignore: bool = True) -> Dict[str, Any]:
    """
    Build a tree structure of all files in the directory.

    Args:
        root_path: The root directory path to scan
        use_gitignore: Whether to use .gitignore patterns for filtering

    Returns:
        A nested dictionary representing the file tree
    """
    # Default ignore patterns
    ignore_patterns = ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build']

    # Use git command to get ignored files if in a git repository
    ignored_files: Set[str] = set()
    if use_gitignore and is_git_repo(root_path):
        ignored_files = get_git_ignored_files(root_path)

    root = Path(root_path)
    tree = {}

    def scan_directory(path: Path, current_tree: Dict[str, Any]):
        try:
            for item in sorted(path.iterdir()):
                # Skip default ignore patterns
                if any(pattern in item.name for pattern in ignore_patterns):
                    continue

                # Skip git-ignored files if enabled
                if use_gitignore:
                    relative_path = str(item.relative_to(root)).replace('\\', '/')
                    # For directories, also check with trailing slash
                    check_path = relative_path + '/' if item.is_dir() else relative_path
                    if check_path in ignored_files or relative_path in ignored_files:
                        continue

                if item.is_file():
                    # Add file with empty value
                    current_tree[item.name] = None
                elif item.is_dir():
                    # Create subtree for directory
                    current_tree[item.name] = {}
                    scan_directory(item, current_tree[item.name])
        except PermissionError:
            # Skip directories we don't have permission to access
            pass

    scan_directory(root, tree)
    return tree

def main():
    parser = argparse.ArgumentParser(description='Generate file tree structure in YAML format')
    parser.add_argument('path', nargs='?', default=os.getcwd(), 
                       help='Path to the directory to scan (default: current directory)')
    parser.add_argument('--no-gitignore', action='store_true',
                       help='Disable .gitignore filtering (default: enabled)')
    
    args = parser.parse_args()
    root_path = args.path
    use_gitignore = not args.no_gitignore
    
    tree = build_file_tree(root_path, use_gitignore)
    
    # Output as YAML
    yaml_output = yaml.dump(tree, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(yaml_output)

if __name__ == "__main__":
    main()