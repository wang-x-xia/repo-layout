# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyyaml",
# ]
# ///

import os
import sys
import subprocess
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

# Set stdout encoding to UTF-8 for Windows compatibility
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def load_case_yaml(case_path: Path) -> List[Dict[str, Any]]:
    """Load case.yaml file."""
    case_file = case_path / "case.yaml"
    if not case_file.exists():
        print(f"Error: case.yaml not found in {case_path}")
        sys.exit(1)
    
    with open(case_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_command(cli_params: str, working_dir: Path) -> tuple[int, str, str]:
    """Run command and return return code, stdout, stderr."""
    base_cmd = "uv run --quiet ../../../repo-layout-skills/scripts/file_tree.py ."
    if cli_params:
        cmd = f"{base_cmd} {cli_params}"
    else:
        cmd = base_cmd
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
    cases = load_case_yaml(case_path)
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
        name = case['name']
        cli_params = case['cli-params']
        expected_return_code = case['return-code']
        std_out_file = case.get('std-out')
        std_err_file = case.get('std-err')

        # Default file names if not specified
        if std_out_file is None:
            std_out_file = f"{name}.out.yaml"
        if std_err_file is None:
            std_err_file = f"{name}.err.yaml"

        # Run command (common for all cases)
        return_code, stdout, stderr = run_command(cli_params, data_dir)
        return_code_match = return_code == expected_return_code
        has_configured_output = case.get('std-out') is not None or case.get('std-err') is not None

        # Determine if we should verify or generate
        should_verify = has_configured_output or not generate

        if should_verify:
            # Verification logic
            case_passed = True
            case_errors = []

            if not return_code_match:
                case_passed = False
                case_errors.append(f"Return code: expected {expected_return_code}, got {return_code}")

            # Check stdout
            stdout_path = result_dir / std_out_file
            if not stdout_path.exists():
                case_passed = False
                case_errors.append(f"Stdout file not found: {stdout_path}")
            else:
                with open(stdout_path, 'r', encoding='utf-8') as f:
                    expected_stdout = f.read()
                if stdout != expected_stdout:
                    case_passed = False
                    case_errors.append(f"Stdout does not match {std_out_file}")

            # Check stderr (must be empty for success cases, can have content for error cases)
            if expected_return_code == 0 and stderr.strip():
                case_passed = False
                case_errors.append(f"Stderr should be empty but got: {stderr}")

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
                    "errors": [f"Return code: expected {expected_return_code}, got {return_code}"]
                })
                continue

            # Save stdout
            stdout_path = result_dir / std_out_file
            with open(stdout_path, 'w', encoding='utf-8') as f:
                f.write(stdout)

            # Diagnose stderr for success cases
            if return_code == 0 and stderr.strip():
                failed_cases.append({
                    "name": name,
                    "errors": [f"Return code is 0 but stderr has content: {stderr}"]
                })
                continue

            # Save stderr only for error cases (return-code != 0)
            if return_code != 0 and std_err_file:
                stderr_path = result_dir / std_err_file
                with open(stderr_path, 'w', encoding='utf-8') as f:
                    f.write(stderr)

    # Output results
    action = "generate" if generate else "verify"
    output = {
        "action": action,
        "case_path": str(case_path),
        "total_cases": len(cases),
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
    results = []

    for case_dir in sorted(case_dirs):
        case_name = case_dir.name
        result = verify_result(case_dir, generate=False)
        case_passed = len(result["failed_cases"]) == 0

        if not case_passed:
            all_passed = False

        results.append({
            "name": case_name,
            "status": "passed" if case_passed else "failed",
            "details": result
        })

    output = {
        "action": "verify-all",
        "test_dir": str(test_dir),
        "total_test_dirs": len(case_dirs),
        "all_passed": all_passed,
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
