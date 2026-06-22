# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyyaml",
#     "pydantic>=2.0",
# ]
# ///

import os
import sys
import subprocess
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Set stdout encoding to UTF-8 for Windows compatibility
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class CaseItem(BaseModel):
    """Represents a single test case."""
    name: str
    cli_params: str = Field(default="", alias='cli-params')
    return_code: int = Field(alias='return-code', default=0)
    stdout: Optional[str] = Field(None, alias='stdout')
    stderr: Optional[str] = Field(None, alias='stderr')


class CaseConfig(BaseModel):
    """Represents the case.yaml configuration with cli and cases."""
    cli: str
    cases: List[CaseItem]


def load_case_yaml(case_path: Path) -> CaseConfig:
    """Load case.yaml file using pydantic for validation."""
    case_file = case_path / "case.yaml"
    if not case_file.exists():
        print(f"Error: case.yaml not found in {case_path}")
        sys.exit(1)
    
    with open(case_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Support both old format (array) and new format (struct with cli and cases)
    if isinstance(data, list):
        # Old format: array of cases, convert to new format
        cases = [CaseItem(**case) for case in data]
        return CaseConfig(cli="uv run --quiet ../../../repo-layout-skills/scripts/file_tree.py .", cases=cases)
    elif isinstance(data, dict):
        # New format: struct with cli and cases
        return CaseConfig(**data)
    else:
        print(f"Error: Invalid case.yaml format in {case_path}")
        sys.exit(1)


def run_command(cli: str, cli_params: str, working_dir: Path) -> tuple[int, str, str]:
    """Run command and return return code, stdout, stderr."""
    if cli_params:
        cmd = f"{cli} {cli_params}"
    else:
        cmd = cli
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=working_dir,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    return result.returncode, result.stdout, result.stderr


def verify_result(case_path: Path, generate: bool = False) -> dict:
    """Verify result files against expected behavior, or generate if generate=True."""
    config = load_case_yaml(case_path)
    cli = config.cli
    cases = config.cases
    data_dir = case_path / "data"
    result_dir = case_path / "result"

    # Pre-check for generate mode
    if generate:
        if not data_dir.exists():
            return {
                "action": "generate",
                "case_path": str(case_path),
                "total_cases": len(cases),
                "failed_cases": [{"name": "pre-check", "errors": [f"Data directory not found: {data_dir}"]}]
            }

        # Clear result directory if it exists
        if result_dir.exists():
            for item in result_dir.iterdir():
                if item.is_file():
                    item.unlink()

        # Create result directory if it doesn't exist
        result_dir.mkdir(parents=True, exist_ok=True)

    # Pre-check for verify mode
    if not generate and not result_dir.exists():
        return {
            "action": "verify",
            "case_path": str(case_path),
            "total_cases": len(cases),
            "failed_cases": [{"name": "pre-check", "errors": [f"result directory not found in {case_path}. Please run 'test_case.py verify --generate' first to generate result files."]}]
        }

    failed_cases = []

    for case in cases:
        name = case.name
        cli_params = case.cli_params
        expected_return_code = case.return_code
        stdout_file = case.stdout
        stderr_file = case.stderr

        # Default file names if not specified
        if stdout_file is None:
            stdout_file = f"{name}.out.yaml"
        if stderr_file is None:
            stderr_file = f"{name}.err.yaml"

        # Run command (common for all cases)
        return_code, stdout, stderr = run_command(cli, cli_params, data_dir)
        return_code_match = return_code == expected_return_code
        has_configured_output = case.stdout is not None or case.stderr is not None

        # Determine if we should verify or generate
        should_verify = has_configured_output or not generate

        if should_verify:
            # Verification logic
            case_passed = True
            case_errors = []

            if not return_code_match:
                case_passed = False
                case_errors.append({
                    "code": "return_code_mismatch",
                    "expected": expected_return_code,
                    "actual": return_code
                })

            # Check stdout
            stdout_path = result_dir / stdout_file
            if not stdout_path.exists():
                case_passed = False
                case_errors.append({
                    "code": "stdout_file_not_found",
                    "path": str(stdout_path)
                })
            else:
                with open(stdout_path, 'r', encoding='utf-8') as f:
                    expected_stdout = f.read()
                if stdout != expected_stdout:
                    case_passed = False
                    case_errors.append({
                        "code": "stdout_mismatch",
                        "file": stdout_file,
                        "actual": stdout,
                        "expected": expected_stdout
                    })

            # Check stderr (must be empty for success cases, can have content for error cases)
            if expected_return_code == 0 and stderr.strip():
                case_passed = False
                case_errors.append({
                    "code": "stderr_not_empty",
                    "stderr": stderr
                })

            # Build result
            verify_result = {
                "name": name,
                "passed": case_passed
            }
            if not case_passed:
                verify_result["errors"] = case_errors

            # Add to appropriate list
            if not case_passed:
                failed_cases.append(verify_result)
        else:
            # Generation logic
            # Check return code
            if not return_code_match:
                failed_cases.append({
                    "name": name,
                    "errors": [{
                        "code": "return_code_mismatch",
                        "expected": expected_return_code,
                        "actual": return_code
                    }]
                })
                continue

            # Save stdout
            stdout_path = result_dir / stdout_file
            with open(stdout_path, 'w', encoding='utf-8') as f:
                f.write(stdout)

            # Diagnose stderr for success cases
            if return_code == 0 and stderr.strip():
                # Ignore uv installation messages
                if 'Installed' in stderr or 'package' in stderr:
                    pass
                else:
                    failed_cases.append({
                        "name": name,
                        "errors": [{
                            "code": "stderr_not_empty",
                            "stderr": stderr
                        }]
                    })
                    continue

            # Save stderr only for error cases (return-code != 0)
            if return_code != 0 and stderr_file:
                stderr_path = result_dir / stderr_file
                with open(stderr_path, 'w', encoding='utf-8') as f:
                    f.write(stderr)

    # Output results
    action = "generate" if generate else "verify"
    output = {
        "action": action,
        "case_path": str(case_path),
        "total_cases": len(cases),
        "passed_cases": len(cases) - len(failed_cases),
        "failed_cases": failed_cases
    }

    return output


def run_all_tests(test_dir: Path):
    """Run verify for all test cases in test directory."""
    if not test_dir.exists():
        error_output = {
            "error": f"Test directory not found: {test_dir}"
        }
        print(yaml.dump(error_output, default_flow_style=False, allow_unicode=True))
        sys.exit(1)

    # Find all case directories
    case_dirs = []
    for item in test_dir.iterdir():
        if item.is_dir() and (item / "case.yaml").exists():
            case_dirs.append(item)

    if not case_dirs:
        error_output = {
            "error": f"No test cases found in {test_dir}"
        }
        print(yaml.dump(error_output, default_flow_style=False, allow_unicode=True))
        sys.exit(1)

    all_passed = True
    total_cases = 0
    total_passed_cases = 0
    total_failed_cases = 0
    results = []

    for case_dir in sorted(case_dirs):
        case_name = case_dir.name
        result = verify_result(case_dir, generate=False)

        if result["failed_cases"]:
            all_passed = False
        
        total_cases += result["total_cases"]
        total_passed_cases += result["passed_cases"]
        total_failed_cases += len(result["failed_cases"])


        results.append({
            "name": case_name,
            "cases": result["total_cases"],
            "passed_cases": result["passed_cases"],
            "failed_cases": result["failed_cases"] 
        })

    output = {
        "action": "verify-all",
        "test_dir": str(test_dir),
        "total_test_dirs": len(case_dirs),
        "all_passed": all_passed,
        "total_cases": total_cases,
        "total_passed_cases": total_passed_cases,
        "total_failed_cases": total_failed_cases,
        "results": results
    }

    print(yaml.dump(output, default_flow_style=False, allow_unicode=True))

    if not all_passed:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Test case runner for file tree script')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify result files against expected behavior')
    verify_parser.add_argument('case_name', help='Test case name (e.g., core-success)')
    verify_parser.add_argument('--generate', action='store_true', help='Generate result files instead of verifying')

    # Verify-all command
    subparsers.add_parser('verify-all', help='Verify all test cases')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get test directory (script parent directory)
    test_dir = Path(__file__).parent

    if args.command == 'verify':
        case_name = args.case_name
        case_path = test_dir / case_name
        if not case_path.exists():
            error_output = {
                "error": f"Case path not found: {case_path}"
            }
            print(yaml.dump(error_output, default_flow_style=False, allow_unicode=True))
            sys.exit(1)
        result = verify_result(case_path, generate=args.generate)
        print(yaml.dump(result, default_flow_style=False, allow_unicode=True))
        if len(result["failed_cases"]) > 0:
            sys.exit(1)

    elif args.command == 'verify-all':
        run_all_tests(test_dir)


if __name__ == "__main__":
    main()
