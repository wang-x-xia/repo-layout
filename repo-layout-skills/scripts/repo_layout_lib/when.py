"""
When condition processing logic.

This module handles the application of when conditions to metadata
during the parsing phase.
"""

from typing import Dict, Any, Optional, List, Union
from pathlib import Path


def apply_when_conditions(
    repo_layout_data: Dict[str, Any],
    tags: Optional[List[str]],
    md_file_path: Path
) -> Dict[str, Any]:
    """
    Apply when conditions to repo-layout data during parsing phase.

    When a tag condition matches, the fields from the when condition
    (excluding 'tag') are merged into the repo-layout data, overriding
    existing values.

    Args:
        repo_layout_data: The original repo-layout dict from frontmatter
        tags: List of tags to check against
        md_file_path: Path to the markdown file (for error reporting)

    Returns:
        Modified repo-layout data with when conditions applied
    """
    if 'when' not in repo_layout_data:
        return repo_layout_data

    when_conditions = repo_layout_data['when']
    if not when_conditions:
        # Remove when field even if no conditions
        result = repo_layout_data.copy()
        result.pop('when', None)
        return result

    # Collect all matching overrides
    matching_overrides = {}
    if tags:
        for condition in when_conditions:
            if not isinstance(condition, dict):
                continue

            if 'tag' not in condition:
                continue

            # Handle both string and list tags
            condition_tags = condition['tag']
            if isinstance(condition_tags, str):
                condition_tags = [condition_tags]

            # Check if any of the condition tags is in the provided tags
            if any(tag in tags for tag in condition_tags):
                # Get all fields except 'tag' as overrides
                overrides = {k: v for k, v in condition.items() if k != 'tag'}
                matching_overrides.update(overrides)

    # Create a copy with overrides applied
    result = repo_layout_data.copy()
    result.update(matching_overrides)
    # Remove when field after applying conditions
    result.pop('when', None)
    return result
