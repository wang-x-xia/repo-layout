# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyyaml",
# ]
# ///

import os
import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, Set, Optional
from repo_layout_lib.git import is_git_repo, get_git_ignored_files
from repo_layout_lib.known_files import load_known_files, get_file_description

# Set stdout encoding to UTF-8 for Windows compatibility
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def sort_tree_with_metadata(tree: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sort tree dictionary with metadata keys (starting with :) first.

    Args:
        tree: The tree dictionary to sort

    Returns:
        Sorted tree dictionary
    """
    if not isinstance(tree, dict):
        return tree

    # Separate keys into metadata keys (starting with :) and regular keys
    meta_keys = [k for k in tree.keys() if k.startswith(':')]
    regular_keys = [k for k in tree.keys() if not k.startswith(':')]

    # Sort both groups
    meta_keys.sort()
    regular_keys.sort()

    # Build new sorted dictionary
    sorted_tree = {}
    for key in meta_keys + regular_keys:
        value = tree[key]
        if isinstance(value, dict):
            # Recursively sort nested dictionaries
            sorted_tree[key] = sort_tree_with_metadata(value)
        else:
            sorted_tree[key] = value

    return sorted_tree

def parse_frontmatter(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse YAML frontmatter from a markdown file.

    Args:
        file_path: Path to the markdown file

    Returns:
        Parsed frontmatter as a dictionary, or None if no frontmatter found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if file starts with ---
        if not content.startswith('---'):
            return None

        # Find the end of frontmatter (second ---)
        end_marker = content.find('\n---', 4)
        if end_marker == -1:
            return None

        frontmatter_content = content[4:end_marker]
        return yaml.safe_load(frontmatter_content)
    except Exception:
        # If parsing fails, return None
        return None

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

    # Load known files descriptions using script-relative path
    script_path = Path(__file__)
    known_files = load_known_files(script_path, locale="zh-CN")

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
                    # Add file with description if known, otherwise empty value
                    description = get_file_description(known_files, item.name)
                    current_tree[item.name] = description if description else None
                elif item.is_dir():
                    # Create subtree for directory
                    current_tree[item.name] = {}
                    scan_directory(item, current_tree[item.name])

                    # Check for AGENTS.md and parse its frontmatter
                    agents_file = item / 'AGENTS.md'
                    if agents_file.exists():
                        frontmatter = parse_frontmatter(agents_file)
                        if frontmatter and 'folder_meta' in frontmatter:
                            # Add folder_meta with :meta key (colon is illegal in filenames)
                            current_tree[item.name][':meta'] = frontmatter['folder_meta']
        except PermissionError:
            # Skip directories we don't have permission to access
            pass

    scan_directory(root, tree)

    # Check for AGENTS.md in root directory and parse its frontmatter
    agents_file = root / 'AGENTS.md'
    if agents_file.exists():
        frontmatter = parse_frontmatter(agents_file)
        if frontmatter and 'folder_meta' in frontmatter:
            # Add folder_meta with :meta key (colon is illegal in filenames)
            tree[':meta'] = frontmatter['folder_meta']

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

    # Sort tree with metadata keys first
    sorted_tree = sort_tree_with_metadata(tree)

    # Output as YAML
    yaml_output = yaml.dump(sorted_tree, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(yaml_output)

if __name__ == "__main__":
    main()