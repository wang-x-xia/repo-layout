import sys
from typing import Dict, Any, List, Optional
from pydantic import ValidationError
from .yaml_utils import dump


class RepoLayoutValidationError(Exception):
    """Custom validation error for repo-layout metadata."""
    def __init__(self, error_code: str, error_data: Dict[str, Any]):
        self.error_code = error_code
        self.error_data = error_data
        super().__init__(f"{error_code}: {error_data}")


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

    def handle_validation_error(self, error: Exception, file_path: str) -> None:
        """
        Handle validation errors from Pydantic or custom validators.

        Args:
            error: The exception to handle
            file_path: Path to the file being validated
        """
        if isinstance(error, RepoLayoutValidationError):
            # Handle our custom validation errors
            self.add_error(error.error_code, error.error_data)
        elif isinstance(error, ValidationError):
            # Handle Pydantic validation errors
            error_details = error.errors()
            for err in error_details:
                loc = err['loc']
                err_type = err['type']
                
                if err_type == 'extra_forbidden':
                    # Handle extra field error
                    field_name = str(loc[0]) if loc else 'unknown'
                    self.add_error("invalid_repo_layout_field", {
                        "file": file_path,
                        "invalid_field": field_name,
                        "allowed_fields": ['files', 'include', 'exclude', 'show_files', 'meta', 'when']
                    })
                elif err_type == 'model_type':
                    # Handle type validation error (e.g., name_patterns should be dict)
                    field_name = str(loc[0]) if loc else 'unknown'
                    self.add_error("invalid_name_patterns_type", {
                        "file": file_path,
                        "field": field_name,
                        "expected_type": "dict"
                    })
                else:
                    # Other validation errors
                    self.add_error("validation_error", {
                        "file": file_path,
                        "error": str(err)
                    })
        else:
            # Handle other exceptions
            self.add_error("validation_error", {
                "file": file_path,
                "error": str(error)
            })
