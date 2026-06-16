"""
File tree metadata loading and caching system.

This module provides a structured approach to loading and caching file/folder metadata
with support for tags, gitignore patterns, and progressive loading.
"""

import yaml
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Union
from pathlib import Path
from enum import Enum


class VisibilityState(Enum):
    """Visibility state for folders based on when conditions."""
    VISIBLE = "visible"
    HIDDEN = "hidden"


@dataclass
class WhenCondition:
    """Represents a when condition from frontmatter."""
    tag: Union[str, List[str]]
    show_files: bool


@dataclass
class FolderMetadata:
    """Metadata for a folder parsed from AGENTS.md frontmatter."""
    path: Path
    folder_meta: Optional[Dict[str, Any]] = None
    when_conditions: List[WhenCondition] = field(default_factory=list)
    files_field: Optional[Dict[str, str]] = None
    visibility_state: VisibilityState = VisibilityState.VISIBLE
    
    def should_hide_files(self, tags: Optional[List[str]]) -> bool:
        """
        Check if files should be hidden based on when conditions and tags.

        Args:
            tags: List of tags to check against

        Returns:
            True if files should be hidden, False otherwise
        """
        if not tags or not self.when_conditions:
            return False

        for condition in self.when_conditions:
            # Handle both string and list tags
            condition_tags = condition.tag if isinstance(condition.tag, list) else [condition.tag]
            # Check if any of the condition tags is in the provided tags
            if any(tag in tags for tag in condition_tags) and not condition.show_files:
                return True
        return False


@dataclass
class FileMetadata:
    """Metadata for a file from multiple sources."""
    path: Path
    description: Optional[str] = None
    source: Optional[str] = None  # 'agents', 'md_file', 'known_files', or None


@dataclass
class LoadConfig:
    """Configuration for metadata loading."""
    root_path: Path
    use_gitignore: bool = True
    tags: Optional[List[str]] = None
    ignore_patterns: List[str] = field(default_factory=lambda: [
        '.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build'
    ])
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = ['standard']


@dataclass
class MetadataCache:
    """Cache for all loaded metadata during file tree construction."""
    config: LoadConfig
    root_metadata: Optional[FolderMetadata] = None
    folder_metadata: Dict[Path, FolderMetadata] = field(default_factory=dict)
    file_metadata: Dict[Path, FileMetadata] = field(default_factory=dict)
    git_ignored_files: Set[str] = field(default_factory=set)
    known_files: Dict[str, Any] = field(default_factory=dict)
    
    def get_folder_metadata(self, path: Path) -> Optional[FolderMetadata]:
        """Get cached folder metadata for a path."""
        return self.folder_metadata.get(path)
    
    def set_folder_metadata(self, path: Path, metadata: FolderMetadata) -> None:
        """Cache folder metadata for a path."""
        self.folder_metadata[path] = metadata
    
    def get_file_metadata(self, path: Path) -> Optional[FileMetadata]:
        """Get cached file metadata for a path."""
        return self.file_metadata.get(path)
    
    def set_file_metadata(self, path: Path, metadata: FileMetadata) -> None:
        """Cache file metadata for a path."""
        self.file_metadata[path] = metadata
    
    def is_git_ignored(self, relative_path: str, is_dir: bool = False) -> bool:
        """
        Check if a path is git ignored.
        
        Args:
            relative_path: Relative path from root
            is_dir: Whether the path is a directory
            
        Returns:
            True if ignored, False otherwise
        """
        check_path = relative_path + '/' if is_dir else relative_path
        return check_path in self.git_ignored_files or relative_path in self.git_ignored_files
    
    def is_default_ignored(self, name: str) -> bool:
        """
        Check if a name matches default ignore patterns.
        
        Args:
            name: File or directory name
            
        Returns:
            True if should be ignored, False otherwise
        """
        return any(pattern in name for pattern in self.config.ignore_patterns)


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
        if 'tag' in condition and 'show_files' in condition:
            conditions.append(WhenCondition(
                tag=condition['tag'],
                show_files=condition['show_files']
            ))
    
    return conditions


def load_folder_metadata(path: Path) -> Optional[FolderMetadata]:
    """
    Load folder metadata from AGENTS.md file in the given path.
    
    Args:
        path: Path to the folder
        
    Returns:
        FolderMetadata object if AGENTS.md exists, None otherwise
    """
    agents_file = path / 'AGENTS.md'
    if not agents_file.exists():
        return None
    
    frontmatter = parse_frontmatter(agents_file)
    if not frontmatter:
        return FolderMetadata(path=path)
    
    return FolderMetadata(
        path=path,
        folder_meta=frontmatter.get('folder_meta'),
        when_conditions=parse_when_conditions(frontmatter),
        files_field=frontmatter.get('files')
    )


def load_root_metadata(cache: MetadataCache) -> None:
    """
    Load root folder metadata and cache it.
    
    Args:
        cache: MetadataCache to populate with root metadata
    """
    root_metadata = load_folder_metadata(cache.config.root_path)
    cache.root_metadata = root_metadata
    
    if root_metadata:
        cache.set_folder_metadata(cache.config.root_path, root_metadata)


def load_folder_metadata_recursive(cache: MetadataCache, path: Path) -> None:
    """
    Recursively load folder metadata for a path and its subdirectories.
    
    This function loads metadata independently for each folder - it doesn't depend
    on parent folder configuration. The parent folder only decides whether to
    display its own contents, not whether to load metadata.
    
    Args:
        cache: MetadataCache to populate with folder metadata
        path: Path to the folder to scan
    """
    try:
        for item in sorted(path.iterdir()):
            if item.is_dir():
                # Load metadata for this subdirectory
                metadata = load_folder_metadata(item)
                if metadata:
                    cache.set_folder_metadata(item, metadata)
                
                # Recursively load metadata for subdirectories
                load_folder_metadata_recursive(cache, item)
    except PermissionError:
        # Skip directories we don't have permission to access
        pass


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


def load_file_metadata(
    cache: MetadataCache, 
    file_path: Path, 
    parent_agents_file: Path,
    error_collector: Optional[Any] = None
) -> FileMetadata:
    """
    Load file metadata from multiple sources with conflict detection.
    
    Args:
        cache: MetadataCache containing known_files and other data
        file_path: Path to the file
        parent_agents_file: Path to parent directory's AGENTS.md
        error_collector: Optional ErrorCollector for conflict warnings
        
    Returns:
        FileMetadata object with description from best source
    """
    # Get description from multiple sources
    desc_from_agents = get_file_description_from_agents(parent_agents_file, file_path.name)
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
    
    # Check for conflicts: if both custom sources have descriptions, use default value and warn
    if desc_from_agents is not None and desc_from_md is not None:
        if error_collector:
            warning_data = {
                "file": str(file_path.relative_to(cache.config.root_path)),
                "conflict_definitions": [
                    str(parent_agents_file.relative_to(cache.config.root_path)),
                    str(file_path.relative_to(cache.config.root_path)) + ".md"
                ]
            }
            error_collector.add_warning("conflict_file_description", warning_data)
        # Use default value (known_files) when conflict occurs
        description = desc_from_known
        source = "known_files"
    # Use custom description if available, otherwise fall back to known_files
    elif desc_from_agents is not None:
        description = desc_from_agents
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
) -> Dict[str, Any]:
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
        Nested dictionary representing the file tree
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


def build_file_tree_from_cache(
    cache: MetadataCache, 
    error_collector: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Build file tree structure from cached metadata.
    
    Args:
        cache: MetadataCache with all loaded metadata
        error_collector: Optional ErrorCollector for warnings
        
    Returns:
        Nested dictionary representing the file tree
    """
    # Load all metadata
    load_root_metadata(cache)
    load_folder_metadata_recursive(cache, cache.config.root_path)
    
    root = cache.config.root_path
    tree = {}
    
    def build_tree_recursive(path: Path, current_tree: Dict[str, Any]) -> None:
        """
        Recursively build tree structure from cached metadata.
        
        Args:
            path: Current directory path
            current_tree: Current tree dict to populate
        """
        parent_agents_file = path / 'AGENTS.md'
        
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
                    # Load file metadata
                    file_metadata = load_file_metadata(
                        cache, item, parent_agents_file, error_collector
                    )
                    cache.set_file_metadata(item, file_metadata)
                    current_tree[item.name] = file_metadata.description
                    
                elif item.is_dir():
                    # Get cached folder metadata
                    folder_metadata = cache.get_folder_metadata(item)
                    
                    # Check if when condition matches (show_files should be false)
                    should_hide_files = False
                    if folder_metadata:
                        should_hide_files = folder_metadata.should_hide_files(cache.config.tags)
                    
                    if should_hide_files and folder_metadata and folder_metadata.folder_meta:
                        # When condition matches, use folder_meta directly as the value
                        current_tree[item.name] = folder_metadata.folder_meta
                    else:
                        # Create subtree for directory
                        current_tree[item.name] = {}
                        build_tree_recursive(item, current_tree[item.name])
                        
                        # Add folder_meta with :meta key (colon is illegal in filenames)
                        if folder_metadata and folder_metadata.folder_meta:
                            current_tree[item.name][':meta'] = folder_metadata.folder_meta
                            
        except PermissionError:
            # Skip directories we don't have permission to access
            pass
    
    # Build tree structure
    build_tree_recursive(root, tree)
    
    # Handle root folder metadata
    if cache.root_metadata and cache.root_metadata.folder_meta:
        should_hide_files = cache.root_metadata.should_hide_files(cache.config.tags)
        
        if should_hide_files:
            # When condition matches, replace entire tree with folder_meta
            tree = cache.root_metadata.folder_meta
        else:
            # Add folder_meta with :meta key
            tree[':meta'] = cache.root_metadata.folder_meta
    
    return tree
