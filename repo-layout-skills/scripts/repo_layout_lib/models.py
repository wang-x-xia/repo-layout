"""
Data models for file tree metadata.
"""

from typing import Dict, Any, Optional, List, Set, Union
from pathlib import Path
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from .error import RepoLayoutValidationError


class ConfigModel(BaseModel):
    """Base model for parsing configuration/data from external sources."""
    model_config = ConfigDict(extra='forbid')

class FileNode(BaseModel):
    """Represents a file in the tree."""
    name: str
    description: Optional[str] = None
    meta_type: Optional[str] = None  # Type of metadata file (e.g., "md"), None if not a metadata file
    has_meta_type: Optional[str] = None  # Type of metadata file this file has (e.g., "md"), None if none
    repo_layout_md: Optional[Path] = None  # Path to repo-layout md file that covers this file
    show_file_metadata: bool = True  # Whether to show file metadata (controlled by repo-layout show_files)
    is_repo_layout_md: bool = False  # Whether this file is a repo-layout md file


class FolderNode(BaseModel):
    """Represents a folder in the tree."""
    name: str
    children: Dict[str, 'TreeNode'] = Field(default_factory=dict)
    meta: Optional[Any] = None
    has_agents_md: bool = False  # Whether folder has AGENTS.md file
    merged_meta_from_md: Optional[Dict[str, Any]] = None  # Merged metadata from repo-layout md files


# Type alias for tree nodes (can be either file or folder)
TreeNode = Union[FileNode, FolderNode]

# Update forward reference
FolderNode.model_rebuild()


class FileTree(BaseModel):
    """Root of the file tree."""
    root: FolderNode
    meta: Optional[Any] = None


class PatternSpec(ConfigModel):
    """Pattern specification for files or folders."""
    include: List[str] = Field(default_factory=list)
    exclude: List[str] = Field(default_factory=list)


class NamePatterns(ConfigModel):
    """Name patterns for files and folders."""
    files: Optional[PatternSpec] = None
    folders: Optional[PatternSpec] = None


class HintMetadata(ConfigModel):
    """Metadata for repo-layout frontmatter in markdown files (non-AGENTS.md)."""
    path: Path
    files: List[str] = Field(default_factory=list)  # Exact file matches
    include: List[str] = Field(default_factory=list)  # Glob patterns for whitelist
    exclude: List[str] = Field(default_factory=list)  # Glob patterns for blacklist
    show_files: bool = True  # Whether to show metadata for covered files
    meta: Optional[Dict[str, Any]] = None  # Custom metadata to output
    
    @model_validator(mode='after')
    def validate_patterns(self):
        """Validate that patterns are valid (include+exclude or include-only or files)."""
        has_files = bool(self.files)
        has_include = bool(self.include)
        has_exclude = bool(self.exclude)
        
        # Must have either files or include patterns
        if not has_files and not has_include:
            raise RepoLayoutValidationError(
                "invalid_repo_layout_pattern",
                {
                    "file": str(self.path),
                    "pattern_type": "none"
                }
            )
        
        # exclude without include is invalid
        if has_exclude and not has_include:
            raise RepoLayoutValidationError(
                "invalid_repo_layout_pattern",
                {
                    "file": str(self.path),
                    "pattern_type": "exclude_without_include"
                }
            )
        
        return self




class FolderMetadata(ConfigModel):
    """Metadata for a folder parsed from AGENTS.md frontmatter."""
    path: Path
    meta: Optional[Any] = None
    files: Optional[Dict[str, str]] = None
    entry_point: Optional[str] = None
    name_patterns: Optional[NamePatterns] = None
    show_files: bool = True

class FileMetadata(ConfigModel):
    """Metadata for a file from multiple sources."""
    path: Path
    description: Optional[str] = None
    source: Optional[str] = None  # 'agents', 'md_file', 'known_files', or None


class LoadConfig(BaseModel):
    """Configuration for metadata loading."""
    root_path: Path
    use_gitignore: bool = True
    tags: Optional[List[str]] = None
    ignore_patterns: List[str] = Field(
        default_factory=lambda: ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build']
    )
    
    @model_validator(mode='after')
    def set_default_tags(self):
        """Set default tags if not provided."""
        if self.tags is None:
            self.tags = ['standard']
        return self


class MetadataCache(BaseModel):
    """Cache for all loaded metadata during file tree construction."""
    config: LoadConfig
    root_metadata: Optional[FolderMetadata] = None
    folder_metadata: Dict[Path, FolderMetadata] = Field(default_factory=dict)
    file_metadata: Dict[Path, FileMetadata] = Field(default_factory=dict)
    git_ignored_files: Set[str] = Field(default_factory=set)
    known_files: Dict[str, Any] = Field(default_factory=dict)
    repo_layout_metadata: Dict[Path, HintMetadata] = Field(default_factory=dict)
    file_to_repo_layout: Dict[Path, Path] = Field(default_factory=dict)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
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
