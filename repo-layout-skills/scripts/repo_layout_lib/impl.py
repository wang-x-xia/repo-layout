"""
File tree metadata loading and caching system.

This module provides a structured approach to loading and caching file/folder metadata
with support for tags, gitignore patterns, and progressive loading.
"""

import fnmatch
from typing import Dict, Any, Optional, List
from pathlib import Path

from .yaml_utils import parse_frontmatter
from .models import (
    FileNode,
    FolderNode,
    TreeNode,
    FileTree,
    VisibilityState,
    WhenCondition,
    HintMetadata,
    FolderMetadata,
    FileMetadata,
    LoadConfig,
    MetadataCache,
    NamePatterns
)
from .error import RepoLayoutValidationError


def parse_folder_metadata(frontmatter: Optional[Dict[str, Any]], md_file_path: Path, error_collector: Optional[Any] = None) -> Optional[FolderMetadata]:
    """
    Parse repo-layout frontmatter from AGENTS.md file.

    AGENTS.md contains folder-level metadata (meta, when, entry_point, name_patterns, files).

    Args:
        frontmatter: Parsed frontmatter dictionary
        md_file_path: Path to the AGENTS.md file
        error_collector: Optional ErrorCollector for validation errors

    Returns:
        FolderMetadata object if repo-layout field exists, None otherwise
    """
    if not frontmatter or 'repo-layout' not in frontmatter:
        return None

    repo_layout_data = frontmatter['repo-layout']
    if not isinstance(repo_layout_data, dict):
        return None

    # Add path to data for validation
    repo_layout_data['path'] = md_file_path

    try:
        # Use Pydantic's model_validate for parsing and validation
        metadata = FolderMetadata.model_validate(repo_layout_data)
        return metadata
    
    except Exception as e:
        # Handle validation errors through error_collector
        if error_collector:
            error_collector.handle_validation_error(e, str(md_file_path))
        return None


def parse_hint_metadata(frontmatter: Optional[Dict[str, Any]], md_file_path: Path, error_collector: Optional[Any] = None) -> Optional[HintMetadata]:
    """
    Parse repo-layout frontmatter from a non-AGENTS.md markdown file.

    Non-AGENTS.md files must have patterns (files, include, or include+exclude).

    Args:
        frontmatter: Parsed frontmatter dictionary
        md_file_path: Path to the markdown file
        error_collector: Optional ErrorCollector for validation errors

    Returns:
        HintMetadata object if repo-layout field exists, None otherwise
    """
    if not frontmatter or 'repo-layout' not in frontmatter:
        return None

    repo_layout_data = frontmatter['repo-layout']
    if not isinstance(repo_layout_data, dict):
        return None

    # Add path to data for validation
    repo_layout_data['path'] = md_file_path

    try:
        # Use Pydantic's model_validate for parsing and validation
        # Pattern validation is now handled by the model's validator
        metadata = HintMetadata.model_validate(repo_layout_data)
        return metadata
    
    except Exception as e:
        # Handle validation errors through error_collector
        if error_collector:
            error_collector.handle_validation_error(e, str(md_file_path))
        return None


def match_file_patterns(filename: str, repo_layout: HintMetadata) -> bool:
    """
    Check if a filename matches the repo-layout patterns.

    Args:
        filename: Name of the file to check
        repo_layout: HintMetadata with patterns

    Returns:
        True if file matches, False otherwise
    """
    # Check exact matches first
    if filename in repo_layout.files:
        return True

    # Check include patterns
    if repo_layout.include:
        for pattern in repo_layout.include:
            if fnmatch.fnmatch(filename, pattern):
                # Check if not excluded
                excluded = False
                for exclude_pattern in repo_layout.exclude:
                    if fnmatch.fnmatch(filename, exclude_pattern):
                        excluded = True
                        break
                if not excluded:
                    return True

    return False


def parse_when_conditions(frontmatter: Optional[Dict[str, Any]]) -> List[WhenCondition]:
    """
    Parse when conditions from frontmatter.
    
    Args:
        frontmatter: Parsed frontmatter dictionary
        
    Returns:
        List of WhenCondition objects
    """
    if not frontmatter or 'when' not in frontmatter:
        return []
    
    when_conditions = frontmatter['when']
    if not isinstance(when_conditions, list):
        return []
    
    conditions = []
    for condition in when_conditions:
        if not isinstance(condition, dict):
            continue
        try:
            conditions.append(WhenCondition.model_validate(condition))
        except (ValueError, TypeError):
            # Skip invalid conditions silently
            continue
    
    return conditions


def load_folder_metadata(path: Path, error_collector: Optional[Any] = None) -> Optional[FolderMetadata]:
    """
    Load folder metadata from AGENTS.md file in the given path.
    
    Args:
        path: Path to the folder
        error_collector: Optional ErrorCollector for validation errors
        
    Returns:
        FolderMetadata object if AGENTS.md exists, None otherwise
    """
    agents_file = path / 'AGENTS.md'
    if not agents_file.exists():
        return None
    
    frontmatter = parse_frontmatter(agents_file)
    if not frontmatter:
        return FolderMetadata(path=path)
    
    # Parse repo-layout structure using the new parser
    agents_repo_layout = parse_folder_metadata(frontmatter, agents_file, error_collector)
    
    # Even if parsing fails, try to extract basic metadata from frontmatter
    meta = None
    when = None
    files = None
    entry_point = None
    name_patterns = None
    show_files = True
    
    if agents_repo_layout:
        meta = agents_repo_layout.meta
        when = agents_repo_layout.when
        files = agents_repo_layout.files
        entry_point = agents_repo_layout.entry_point
        name_patterns = agents_repo_layout.name_patterns
        show_files = meta.get('show_files', True) if meta else True
    else:
        # Try to extract basic metadata manually if parsing failed
        repo_layout = frontmatter.get('repo-layout')
        if repo_layout and isinstance(repo_layout, dict):
            meta = repo_layout.get('meta')
            entry_point = repo_layout.get('entry_point')
            show_files = meta.get('show_files', True) if meta else True
    
    # Validate entry_point
    if entry_point:
        entry_point_path = path / entry_point
        if not entry_point_path.exists():
            if error_collector:
                error_collector.add_error("invalid_entry_point", {
                    "file": str(agents_file),
                    "entry_point": entry_point
                })
    if name_patterns:
        try:
            # Validate files
            if name_patterns.files:
                actual_files = [f.name for f in path.iterdir() if f.is_file()]
                if name_patterns.files.include:
                    for filename in actual_files:
                        if not any(fnmatch.fnmatch(filename, pattern) for pattern in name_patterns.files.include):
                            is_excluded = any(fnmatch.fnmatch(filename, pattern) for pattern in name_patterns.files.exclude)
                            if not is_excluded:
                                if error_collector:
                                    error_collector.add_error("file_not_in_name_patterns", {
                                        "file": str(agents_file),
                                        "field": "name_patterns.files",
                                        "filename": filename
                                    })
            
            # Validate folders
            if name_patterns.folders:
                actual_folders = [f.name for f in path.iterdir() if f.is_dir()]
                if name_patterns.folders.include:
                    for foldername in actual_folders:
                        if not any(fnmatch.fnmatch(foldername, pattern) for pattern in name_patterns.folders.include):
                            is_excluded = any(fnmatch.fnmatch(foldername, pattern) for pattern in name_patterns.folders.exclude)
                            if not is_excluded:
                                if error_collector:
                                    error_collector.add_error("folder_not_in_name_patterns", {
                                        "file": str(agents_file),
                                        "field": "name_patterns.folders",
                                        "foldername": foldername
                                    })
        except PermissionError:
            pass
    
    return FolderMetadata(
        path=path,
        meta=meta,
        when=when,
        files=files,
        entry_point=entry_point,
        name_patterns=name_patterns,
        show_files=show_files
    )


def load_root_metadata(cache: MetadataCache, error_collector: Optional[Any] = None) -> None:
    """
    Load root folder metadata and cache it.
    
    Args:
        cache: MetadataCache to populate with root metadata
        error_collector: Optional ErrorCollector for validation errors
    """
    root_metadata = load_folder_metadata(cache.config.root_path, error_collector)
    cache.root_metadata = root_metadata
    
    if root_metadata:
        cache.set_folder_metadata(cache.config.root_path, root_metadata)


def load_folder_metadata_recursive(cache: MetadataCache, path: Path, error_collector: Optional[Any] = None) -> None:
    """
    Recursively load folder metadata for a path and its subdirectories.
    
    This function now respects parent folder configuration - if a folder has
    show_files: false in its when condition, it will skip loading metadata
    from its subdirectories.
    
    Args:
        cache: MetadataCache to populate with folder metadata
        path: Path to the folder to scan
        error_collector: Optional ErrorCollector for validation errors
    """
    try:
        # Load metadata for current folder first
        metadata = load_folder_metadata(path, error_collector)
        if metadata:
            cache.set_folder_metadata(path, metadata)
        
        # Check if we should skip loading subdirectory metadata
        should_skip_subdirs = False
        if metadata:
            should_skip_subdirs = metadata.should_hide_files(cache.config.tags)
        
        # If show_files is false, skip loading subdirectory metadata
        if should_skip_subdirs:
            return
        
        # Load metadata for subdirectories
        for item in sorted(path.iterdir()):
            if item.is_dir():
                # Recursively load metadata for subdirectories
                load_folder_metadata_recursive(cache, item, error_collector)
    except PermissionError:
        # Skip directories we don't have permission to access
        pass


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


def load_file_metadata(
    cache: MetadataCache,
    file_path: Path,
    folder_metadata: Optional[FolderMetadata] = None,
    error_collector: Optional[Any] = None
) -> FileMetadata:
    """
    Load file metadata from multiple sources with conflict detection.

    Args:
        cache: MetadataCache containing known_files and other data
        file_path: Path to the file
        folder_metadata: FolderMetadata for the parent directory
        error_collector: Optional ErrorCollector for conflict warnings

    Returns:
        FileMetadata object with description from best source
    """
    # Get description from multiple sources
    desc_from_folder = None
    if folder_metadata and folder_metadata.files:
        desc_from_folder = folder_metadata.files.get(file_path.name)
    desc_from_md = get_file_description_from_md_file(file_path)
    desc_from_known = cache.known_files.get(file_path.name)

    # Extract description from known_files if it's a dict
    if isinstance(desc_from_known, dict):
        desc_from_known = desc_from_known.get('description')
    elif not isinstance(desc_from_known, str):
        desc_from_known = None

    # Determine source and handle conflicts
    description = None
    source = None

    # Check for conflicts: if both custom sources have descriptions, use default value and error
    if desc_from_folder is not None and desc_from_md is not None:
        if error_collector:
            agents_md_path = file_path.parent / 'AGENTS.md'
            error_data = {
                "file": str(file_path.relative_to(cache.config.root_path)),
                "conflict_with_folder_meta": True,
                "conflict_with_md_file": str(file_path.relative_to(cache.config.root_path)) + ".md"
            }
            error_collector.add_error("conflict_file_description", error_data)
        # Use default value (known_files) when conflict occurs
        description = desc_from_known
        source = "known_files"
    # Use custom description if available, otherwise fall back to known_files
    elif desc_from_folder is not None:
        description = desc_from_folder
        source = "agents"
    elif desc_from_md is not None:
        description = desc_from_md
        source = "md_file"
    else:
        description = desc_from_known
        source = "known_files" if desc_from_known else None

    return FileMetadata(
        path=file_path,
        description=description,
        source=source
    )


def initialize_cache(
    root_path: str, 
    use_gitignore: bool = True, 
    tags: Optional[List[str]] = None,
    script_path: Optional[Path] = None,
    locale: str = "zh-CN"
) -> MetadataCache:
    """
    Initialize a MetadataCache with all necessary data.
    
    Args:
        root_path: Root directory path
        use_gitignore: Whether to use gitignore patterns
        tags: Optional list of tags for filtering
        script_path: Path to the script (for loading known_files)
        locale: Locale for known_files
        
    Returns:
        Initialized MetadataCache
    """
    config = LoadConfig(
        root_path=Path(root_path),
        use_gitignore=use_gitignore,
        tags=tags
    )
    
    cache = MetadataCache(config=config)
    
    # Load git ignored files if needed
    if use_gitignore:
        from repo_layout_lib.git import is_git_repo, get_git_ignored_files
        if is_git_repo(root_path):
            cache.git_ignored_files = get_git_ignored_files(root_path)
    
    # Load known files
    if script_path:
        from repo_layout_lib.known_files import load_known_files
        cache.known_files = load_known_files(script_path, locale)
    
    return cache


def build_file_tree(
    root_path: str,
    use_gitignore: bool = True,
    tags: Optional[List[str]] = None,
    script_path: Optional[Path] = None,
    locale: str = "zh-CN",
    error_collector: Optional[Any] = None
) -> FileTree:
    """
    Build file tree structure - unified entry point.

    This function orchestrates the entire process:
    1. Initialize cache with configuration
    2. Load all metadata (root, folders, files)
    3. Build and return the tree structure

    Args:
        root_path: Root directory path
        use_gitignore: Whether to use gitignore patterns
        tags: Optional list of tags for filtering
        script_path: Path to the script (for loading known_files)
        locale: Locale for known_files
        error_collector: Optional ErrorCollector for warnings

    Returns:
        FileTree object representing the file tree
    """
    # Step 1: Initialize cache
    cache = initialize_cache(
        root_path=root_path,
        use_gitignore=use_gitignore,
        tags=tags,
        script_path=script_path,
        locale=locale
    )

    # Step 2-4: Build tree from cache (handles all metadata loading internally)
    return build_file_tree_from_cache(cache, error_collector)


def get_meta_file_type(filename: str) -> Optional[str]:
    """
    Get the metadata file type if filename is a metadata file.

    Args:
        filename: The filename to check

    Returns:
        Metadata type (e.g., "md") if the filename matches metadata pattern, None otherwise
    """
    # Pattern: has at least one dot before .md, and ends with .md
    # Examples: file.py.md, file.txt.md, but not README.md or file.md
    if not filename.endswith('.md'):
        return None
    # Remove .md suffix and check if there's at least one dot remaining
    base = filename[:-3]  # Remove .md
    if '.' in base:
        return "md"
    return None


def build_file_tree_from_cache(
    cache: MetadataCache,
    error_collector: Optional[Any] = None
) -> FileTree:
    """
    Build file tree structure from cached metadata.

    Args:
        cache: MetadataCache with all loaded metadata
        error_collector: Optional ErrorCollector for warnings

    Returns:
        FileTree object representing the file tree
    """
    # Load all metadata
    load_root_metadata(cache, error_collector)
    load_folder_metadata_recursive(cache, cache.config.root_path, error_collector)

    root = cache.config.root_path
    root_folder = FolderNode(name=root.name, children={}, meta=None, has_agents_md=(cache.root_metadata is not None))

    def build_tree_recursive(path: Path, folder_node: FolderNode) -> None:
        """
        Recursively build tree structure from cached metadata.

        Args:
            path: Current directory path
            folder_node: Current folder node to populate
        """
        # Get folder metadata for this directory
        folder_metadata = cache.get_folder_metadata(path)

        # First, scan for repo-layout md files in this folder (exclude AGENTS.md)
        repo_layout_mds = []
        for item in sorted(path.iterdir()):
            if item.is_file() and item.name.endswith('.md'):
                # Skip AGENTS.md - it's handled by load_folder_metadata for folder-level config
                if item.name == 'AGENTS.md':
                    continue
                frontmatter = parse_frontmatter(item)
                repo_layout_meta = parse_hint_metadata(frontmatter, item, error_collector)
                if repo_layout_meta:
                    repo_layout_mds.append(repo_layout_meta)
                    cache.repo_layout_metadata[item] = repo_layout_meta

        # Collect all repo-layout meta fields (merge with conflict detection)
        folder_repo_layout_meta = {}
        for rl_meta in repo_layout_mds:
            for key, value in rl_meta.meta.items():
                if key in folder_repo_layout_meta:
                    # Conflict detected
                    if error_collector:
                        error_data = {
                            "folder": str(path.relative_to(root)),
                            "conflicting_keys": [key],
                            "sources": [
                                str(rl_meta.path.relative_to(root))
                            ]
                        }
                        error_collector.add_error("conflict_repo_layout_meta", error_data)
                    # Keep first value
                else:
                    folder_repo_layout_meta[key] = value

        if folder_repo_layout_meta:
            folder_node.merged_meta_from_md = folder_repo_layout_meta

        try:
            for item in sorted(path.iterdir()):
                # Skip default ignore patterns
                if cache.is_default_ignored(item.name):
                    continue

                # Skip git-ignored files if enabled
                if cache.config.use_gitignore:
                    relative_path = str(item.relative_to(root)).replace('\\', '/')
                    if cache.is_git_ignored(relative_path, item.is_dir()):
                        continue

                if item.is_file():
                    # Check if this file is a repo-layout md file
                    is_repo_layout_md = item in cache.repo_layout_metadata

                    # Check if this file is covered by any repo-layout md
                    covering_repo_layouts = []
                    for rl_meta in repo_layout_mds:
                        if match_file_patterns(item.name, rl_meta):
                            covering_repo_layouts.append(rl_meta)

                    # Handle conflict: multiple repo-layout md files covering the same file
                    if len(covering_repo_layouts) > 1:
                        if error_collector:
                            error_data = {
                                "file": str(item.relative_to(root)),
                                "covering_repo_layouts": [str(rl.path.relative_to(root)) for rl in covering_repo_layouts]
                            }
                            error_collector.add_error("conflict_repo_layout_coverage", error_data)
                        # Reset to no coverage
                        covering_repo_layouts = []

                    # Load file metadata
                    file_metadata = load_file_metadata(
                        cache, item, folder_metadata, error_collector
                    )
                    cache.set_file_metadata(item, file_metadata)

                    # Set repo_layout_md and show_file_metadata if covered
                    repo_layout_md_path = None
                    show_file_metadata = True
                    if covering_repo_layouts:
                        repo_layout_md_path = covering_repo_layouts[0].path
                        show_file_metadata = covering_repo_layouts[0].show_files

                    # Add file node to folder
                    folder_node.children[item.name] = FileNode(
                        name=item.name,
                        description=file_metadata.description,
                        meta_type=get_meta_file_type(item.name),
                        repo_layout_md=repo_layout_md_path,
                        show_file_metadata=show_file_metadata,
                        is_repo_layout_md=is_repo_layout_md
                    )

                elif item.is_dir():
                    # Get cached folder metadata
                    folder_metadata = cache.get_folder_metadata(item)

                    # Check if when condition matches (show_files should be false)
                    should_hide_files = False
                    if folder_metadata:
                        should_hide_files = folder_metadata.should_hide_files(cache.config.tags)

                    if should_hide_files and folder_metadata and folder_metadata.meta:
                        # When condition matches, use meta as metadata
                        folder_node.children[item.name] = FolderNode(
                            name=item.name,
                            children={},
                            meta=folder_metadata.meta,
                            has_agents_md=(folder_metadata is not None)
                        )
                    else:
                        # Create folder node and recurse
                        child_folder = FolderNode(
                            name=item.name,
                            children={},
                            meta=folder_metadata.meta if folder_metadata else None,
                            has_agents_md=(folder_metadata is not None)
                        )
                        folder_node.children[item.name] = child_folder
                        build_tree_recursive(item, child_folder)

        except PermissionError:
            # Skip directories we don't have permission to access
            pass

    # Build tree structure
    build_tree_recursive(root, root_folder)

    # Post-process: mark files that have corresponding metadata files
    def mark_has_meta_type(folder_node: FolderNode) -> None:
        """
        Mark files that have corresponding metadata files.

        Args:
            folder_node: Folder node to process
        """
        # Collect all metadata files in this folder
        meta_files = {}  # original_name -> meta_type
        for child_name, child_node in folder_node.children.items():
            if isinstance(child_node, FileNode) and child_node.meta_type:
                # Extract the original filename: file.txt.md -> file.txt
                # Remove .{meta_type} suffix (including the dot)
                suffix = f".{child_node.meta_type}"
                original_name = child_name[:-len(suffix)]
                meta_files[original_name] = child_node.meta_type

        # Mark files that have corresponding metadata files
        for child_name, child_node in folder_node.children.items():
            if isinstance(child_node, FileNode) and not child_node.meta_type:
                if child_name in meta_files:
                    child_node.has_meta_type = meta_files[child_name]

        # Recursively process subfolders
        for child_node in folder_node.children.values():
            if isinstance(child_node, FolderNode):
                mark_has_meta_type(child_node)

    mark_has_meta_type(root_folder)

    # Handle root folder metadata
    root_metadata = None
    if cache.root_metadata and cache.root_metadata.meta:
        should_hide_files = cache.root_metadata.should_hide_files(cache.config.tags)

        if should_hide_files:
            # When condition matches, set root metadata
            root_metadata = cache.root_metadata.meta
        else:
            # Add meta to root node
            root_folder.meta = cache.root_metadata.meta

    return FileTree(root=root_folder, meta=root_metadata)
