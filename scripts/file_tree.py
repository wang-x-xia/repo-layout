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
from repo_layout_lib.error import ErrorCollector
from repo_layout_lib.yaml_utils import dump

# Error/Warning codes
WARNING_CONFLICT_FILE_DESCRIPTION = "conflict_file_description"
ERROR_FILE_NOT_FOUND = "file_not_found"

# Set stdout encoding to UTF-8 for Windows compatibility
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')



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

def get_file_description_from_agents(agents_file: Path, filename: str) -> Optional[str]:
    """
    Get file description from AGENTS.md frontmatter files field.

    Args:
        agents_file: Path to the AGENTS.md file
        filename: Name of the file to get description for

    Returns:
        Description string if found, None otherwise
    """
    if not agents_file.exists():
        return None

    frontmatter = parse_frontmatter(agents_file)
    if not frontmatter or 'files' not in frontmatter:
        return None

    files_dict = frontmatter['files']
    if isinstance(files_dict, dict) and filename in files_dict:
        return files_dict[filename]

    return None

def get_file_description_from_md_file(file_path: Path) -> Optional[str]:
    """
    Get file description from {file_name}.{ext}.md frontmatter description field.

    Args:
        file_path: Path to the original file

    Returns:
        Description string if found, None otherwise
    """
    # Construct the .md file path: file_name.ext.md
    md_file_path = file_path.parent / f"{file_path.name}.md"

    if not md_file_path.exists():
        return None

    frontmatter = parse_frontmatter(md_file_path)
    if not frontmatter or 'description' not in frontmatter:
        return None

    return frontmatter['description']

def build_file_tree(root_path: str, use_gitignore: bool = True, error_collector: Optional[ErrorCollector] = None) -> Dict[str, Any]:
    """
    Build a tree structure of all files in the directory.

    Args:
        root_path: The root directory path to scan
        use_gitignore: Whether to use .gitignore patterns for filtering
        error_collector: Optional ErrorCollector to collect warnings and errors

    Returns:
        A nested dictionary representing the file tree
    """
    # Create error collector if not provided
    if error_collector is None:
        error_collector = ErrorCollector()
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
        # Check for AGENTS.md in current directory
        agents_file = path / 'AGENTS.md'

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
                    # Get description from multiple sources with conflict detection
                    desc_from_agents = get_file_description_from_agents(agents_file, item.name)
                    desc_from_md = get_file_description_from_md_file(item)
                    desc_from_known = get_file_description(known_files, item.name)

                    # Check for conflicts: if both custom sources have descriptions, use default value and warn
                    if desc_from_agents is not None and desc_from_md is not None:
                        warning_data = {
                            "file": str(item.relative_to(root)),
                            "conflict_definitions": [
                                str(agents_file.relative_to(root)),
                                str(item.relative_to(root)) + ".md"
                            ]
                        }
                        error_collector.add_warning(WARNING_CONFLICT_FILE_DESCRIPTION, warning_data)
                        # Use default value (known_files) when conflict occurs
                        description = desc_from_known
                    # Use custom description if available, otherwise fall back to known_files
                    elif desc_from_agents is not None:
                        description = desc_from_agents
                    elif desc_from_md is not None:
                        description = desc_from_md
                    else:
                        description = desc_from_known

                    current_tree[item.name] = description if description else None
                elif item.is_dir():
                    # Create subtree for directory
                    current_tree[item.name] = {}
                    scan_directory(item, current_tree[item.name])

                    # Check for AGENTS.md in the subdirectory and parse its frontmatter
                    sub_agents_file = item / 'AGENTS.md'
                    if sub_agents_file.exists():
                        frontmatter = parse_frontmatter(sub_agents_file)
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

    error_collector = ErrorCollector()

    try:
        tree = build_file_tree(root_path, use_gitignore, error_collector)

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