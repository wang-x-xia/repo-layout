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

from repo_layout_lib.file_tree import build_file_tree, FileTree, FolderNode, FileNode, TreeNode
from repo_layout_lib.error import ErrorCollector
from repo_layout_lib.yaml_utils import dump


def file_tree_to_dict(tree: FileTree) -> Dict[str, Any]:
    """
    Convert FileTree to dict for YAML output with formatting:
    1. Add '/' suffix to folder names
    2. Merge folders with only one child (flatten the path)

    Args:
        tree: FileTree object to convert

    Returns:
        Dictionary formatted for YAML output
    """
    # Handle when condition at root level (show_files: false)
    if tree.metadata:
        return tree.metadata

    result = {}

    # Handle root folder metadata
    if tree.root.metadata:
        result[':meta'] = tree.root.metadata

    # Process root folder children
    for name, node in tree.root.children.items():
        result.update(_node_to_dict_entry(name, node))

    return result


def _node_to_dict_entry(name: str, node: TreeNode) -> Dict[str, Any]:
    """
    Convert a tree node to a dict entry (key-value pair).

    Args:
        name: Name of the node
        node: Tree node (FileNode or FolderNode)

    Returns:
        Dictionary with a single key-value pair
    """
    if isinstance(node, FileNode):
        # File node: name -> description
        return {name: node.description}
    elif isinstance(node, FolderNode):
        # Folder node - always add '/' suffix for consistency
        return _folder_node_to_dict_entry(name, node)
    else:
        raise TypeError(f"Unknown node type: {type(node)}")


def _folder_node_to_dict_entry(name: str, folder: FolderNode) -> Dict[str, Any]:
    """
    Convert a folder node to a dict entry with formatting logic.

    Args:
        name: Folder name
        folder: FolderNode to convert

    Returns:
        Dictionary with a single key-value pair (formatted)
    """
    # Handle when condition with show_files: false (no children, only metadata)
    if folder.metadata and not folder.children:
        return {f"{name}/": folder.metadata}

    # Process children recursively
    children_dict = {}
    for child_name, child_node in folder.children.items():
        children_dict.update(_node_to_dict_entry(child_name, child_node))

    # Add metadata if present
    if folder.metadata:
        children_dict[':meta'] = folder.metadata

    # Check if folder has only one non-meta child
    non_meta_keys = [k for k in children_dict.keys() if not k.startswith(':')]

    if len(non_meta_keys) == 1:
        # Merge: only one child, flatten the path
        child_key = non_meta_keys[0]
        child_value = children_dict[child_key]

        # Preserve metadata if exists
        meta_keys = [k for k in children_dict.keys() if k.startswith(':')]
        if meta_keys:
            # Create a new merged dict with metadata, keep folder with '/'
            merged_key = f"{name}/"
            merged_value = {child_key: child_value}
            for meta_key in meta_keys:
                merged_value[meta_key] = children_dict[meta_key]
            return {merged_key: merged_value}
        else:
            # Simple merge without metadata
            if isinstance(child_value, dict):
                # Child is also a folder, merge paths
                merged_key = f"{name}/{child_key}"
                return {merged_key: child_value}
            else:
                # Child is a file
                merged_key = f"{name}/{child_key}"
                return {merged_key: child_value}
    else:
        # Multiple children or no children, keep folder with '/' suffix
        return {f"{name}/": children_dict}

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

        # Convert FileTree to dict with formatting (add '/' suffix, merge single-child folders)
        tree_dict = file_tree_to_dict(tree)

        # Output as YAML with metadata sorting
        yaml_output = dump(tree_dict)
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