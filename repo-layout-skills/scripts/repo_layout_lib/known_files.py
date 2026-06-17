import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def load_known_files(script_path: Path, locale: str = "zh-CN") -> Dict[str, Any]:
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

    known_files: Dict[str, Any] = {}
    if known_files_path.exists():
        try:
            with open(known_files_path, 'r', encoding='utf-8') as f:
                known_files = yaml.safe_load(f) or {}
        except Exception:
            pass

    return known_files


def get_file_description(known_files: Dict[str, Any], filename: str) -> Optional[str]:
    """
    Get description for a file from known files dictionary.

    Args:
        known_files: Dictionary of known files
        filename: Name of the file to get description for

    Returns:
        Description string if found, None otherwise
    """
    if filename in known_files and isinstance(known_files[filename], dict):
        return known_files[filename].get('description')
    elif filename in known_files and isinstance(known_files[filename], str):
        # Backward compatibility: if value is a string, use it directly
        return known_files[filename]
    return None
