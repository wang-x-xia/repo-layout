import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class KnownFileEntry(BaseModel):
    """Schema for a single known file entry."""
    description: Optional[str] = None
    folderLabel: Optional[str] = None
    showFile: bool = True


class KnownFiles(BaseModel):
    """
    Manages known files metadata from reference directory.
    """

    known_files: Dict[str, KnownFileEntry] = Field(default_factory=dict, exclude=True)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, script_path: Path, locale: str = "zh-CN", **kwargs):
        """
        Initialize KnownFiles by loading from reference directory.

        Args:
            script_path: Path to the script file (used to calculate relative path to reference)
            locale: Locale for the known files file (e.g., "zh-CN", "en-US")
        """
        super().__init__(**kwargs)
        self.known_files = self._load_known_files(script_path, locale)

    def _load_known_files(self, script_path: Path, locale: str) -> Dict[str, KnownFileEntry]:
        """
        Load known files descriptions from reference directory.

        Args:
            script_path: Path to the script file (used to calculate relative path to reference)
            locale: Locale for the known files file (e.g., "zh-CN", "en-US")

        Returns:
            Dictionary mapping filenames to their descriptions
        """
        # Calculate reference directory path relative to script
        # Script is in scripts/, reference is in ../reference/
        script_dir = script_path.parent
        reference_dir = script_dir.parent / 'reference'
        known_files_path = reference_dir / f'known_files.{locale}.yaml'

        known_files: Dict[str, KnownFileEntry] = {}
        if known_files_path.exists():
            try:
                with open(known_files_path, 'r', encoding='utf-8') as f:
                    raw_data = yaml.safe_load(f) or {}
                    # Convert to proper schema
                    for key, value in raw_data.items():
                        known_files[key] = KnownFileEntry(**value)
            except Exception:
                pass

        return known_files

    def get_file_description(self, filename: str) -> Optional[str]:
        """
        Get description for a file from known files.

        Args:
            filename: Name of the file to get description for

        Returns:
            Description string if found, None otherwise
        """
        if filename in self.known_files:
            return self.known_files[filename].description
        return None

    def get_folder_label(self, filename: str) -> Optional[str]:
        """
        Get folder label for a file from known files.

        When a folder contains this file, the folder should be labeled with this label.

        Args:
            filename: Name of the file to get folder label for

        Returns:
            Folder label string if found, None otherwise
        """
        if filename in self.known_files:
            return self.known_files[filename].folderLabel
        return None

    def get_data(self) -> Dict[str, Any]:
        """
        Get the raw known files data dictionary.

        Returns:
            Dictionary of known files
        """
        return self.known_files
