import sys
from typing import Dict, Any, List, Optional
from .yaml_utils import dump


class ErrorCollector:
    """
    Collect errors and warnings during file tree processing.
    """
    def __init__(self):
        self.warnings: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def add_warning(self, code: str, data: Dict[str, Any]) -> None:
        """
        Add a warning to the collector.

        Args:
            code: Warning code
            data: Warning-specific data
        """
        self.warnings.append({
            "code": code,
            "data": data
        })

    def add_error(self, code: str, data: Dict[str, Any]) -> None:
        """
        Add an error to the collector.

        Args:
            code: Error code
            data: Error-specific data
        """
        self.errors.append({
            "code": code,
            "data": data
        })

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def output(self) -> None:
        """Output all collected errors and warnings to stderr."""
        output_data = {}

        # Add errors if any
        if self.errors:
            output_data["errors"] = self.errors

        # Add warnings if any
        if self.warnings:
            output_data["warnings"] = self.warnings

        # Output if there's anything to output
        if output_data:
            dump(output_data, sys.stderr)

    def get_exit_code(self) -> int:
        """
        Get the appropriate exit code based on collected issues.

        Returns:
            0 if no errors, 1 if there are errors
        """
        return 1 if self.has_errors() else 0
