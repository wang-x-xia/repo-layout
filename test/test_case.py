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
    base_cmd = "uv run --quiet ../../../scripts/file_tree.py ."
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


def generate_result(case_path: Path):
    """Generate result files for all test cases in case.yaml."""
    cases = load_case_yaml(case_path)
    data_dir = case_path / "data"
    result_dir = case_path / "result"

    # Pre-check: verify data directory exists
    if not data_dir.exists():
        output = {
            "action": "generate",
            "case_path": str(case_path),
            "error": f"Data directory not found: {data_dir}"
        }
        print(yaml.dump(output, default_flow_style=False, allow_unicode=True))
        return

    # Clear result directory if it exists
    if result_dir.exists():
        for item in result_dir.iterdir():
            if item.is_file():
                item.unlink()

    # Create result directory if it doesn't exist
    result_dir.mkdir(parents=True, exist_ok=True)

    results = []

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

        # Run command
        return_code, stdout, stderr = run_command(cli_params, data_dir)

        case_result = {
            "name": name,
            "return_code": return_code,
            "expected_return_code": expected_return_code,
            "return_code_match": return_code == expected_return_code
        }

        # Check return code
        if return_code != expected_return_code:
            case_result["warning"] = f"Expected return code {expected_return_code}, got {return_code}"

        # Save stdout
        if std_out_file:
            stdout_path = result_dir / std_out_file
            with open(stdout_path, 'w', encoding='utf-8') as f:
                f.write(stdout)
            case_result["stdout_saved"] = True
            case_result["stdout_file"] = str(stdout_path)

        # Diagnose stderr for success cases
        if return_code == 0 and stderr.strip():
            case_result["stderr_warning"] = f"Return code is 0 but stderr has content: {stderr}"

        # Save stderr only for error cases (return-code != 0)
        if return_code != 0 and std_err_file:
            stderr_path = result_dir / std_err_file
            with open(stderr_path, 'w', encoding='utf-8') as f:
                f.write(stderr)
            case_result["stderr_saved"] = True
            case_result["stderr_file"] = str(stderr_path)
        else:
            case_result["stderr_saved"] = False

        results.append(case_result)

    output = {
        "action": "generate",
        "case_path": str(case_path),
        "total_cases": len(cases),
        "results": results
    }

    print(yaml.dump(output, default_flow_style=False, allow_unicode=True))


def verify_result(case_path: Path):
    """Verify result files against expected behavior."""
    cases = load_case_yaml(case_path)
    data_dir = case_path / "data"
    result_dir = case_path / "result"

    if not result_dir.exists():
        result = {
            "action": "verify",
            "case_path": str(case_path),
            "passed": False,
            "failed_cases": ["all"],
            "error": f"result directory not found in {case_path}. Please run 'test_case.py generate' first to generate result files."
        }
        print(yaml.dump(result, default_flow_style=False, allow_unicode=True))
        sys.exit(1)
    
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

        case_passed = True
        case_errors = []

        # Run command
        return_code, stdout, stderr = run_command(cli_params, data_dir)

        # Check return code (only for stdout matching)
        if return_code != expected_return_code:
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

        if not case_passed:
            failed_cases.append({
                "name": name,
                "errors": case_errors
            })
    
    result = {
        "action": "verify",
        "case_path": str(case_path),
        "total_cases": len(cases),
        "passed": len(failed_cases) == 0,
        "failed_cases": failed_cases
    }

    print(yaml.dump(result, default_flow_style=False, allow_unicode=True))

    if len(failed_cases) == 0:
        sys.exit(0)
    else:
        sys.exit(1)


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

        # Capture verify output
        import io
        from contextlib import redirect_stdout

        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            try:
                # Temporarily modify sys.argv for verify call
                original_argv = sys.argv
                sys.argv = ['test_case.py', 'verify', str(case_dir)]
                verify_result(case_dir)
                sys.argv = original_argv
                results.append({
                    "name": case_name,
                    "status": "passed"
                })
            except SystemExit as e:
                sys.argv = original_argv
                if e.code != 0:
                    results.append({
                        "name": case_name,
                        "status": "failed"
                    })
                    all_passed = False
                else:
                    results.append({
                        "name": case_name,
                        "status": "passed"
                    })

        # Parse the captured YAML output
        output = stdout_capture.getvalue()
        if output:
            try:
                verify_result_data = yaml.safe_load(output)
                if verify_result_data and isinstance(verify_result_data, dict):
                    results[-1]["details"] = verify_result_data
            except:
                pass

    output = {
        "action": "verify-all",
        "test_dir": str(test_dir),
        "total_cases": len(case_dirs),
        "all_passed": all_passed,
        "results": results
    }

    print(yaml.dump(output, default_flow_style=False, allow_unicode=True))

    if not all_passed:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Test case runner for file tree script')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate result files for test cases')
    generate_parser.add_argument('case_name', help='Test case name (e.g., core-success)')

    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify result files against expected behavior')
    verify_parser.add_argument('case_name', help='Test case name (e.g., core-success)')

    # Verify-all command
    subparsers.add_parser('verify-all', help='Verify all test cases')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get test directory (script parent directory)
    test_dir = Path(__file__).parent

    if args.command == 'generate':
        case_name = args.case_name
        case_path = test_dir / case_name
        if not case_path.exists():
            error_output = {
                "error": f"Case path not found: {case_path}"
            }
            print(yaml.dump(error_output, default_flow_style=False, allow_unicode=True))
            sys.exit(1)
        generate_result(case_path)

    elif args.command == 'verify':
        case_name = args.case_name
        case_path = test_dir / case_name
        if not case_path.exists():
            error_output = {
                "error": f"Case path not found: {case_path}"
            }
            print(yaml.dump(error_output, default_flow_style=False, allow_unicode=True))
            sys.exit(1)
        verify_result(case_path)

    elif args.command == 'verify-all':
        run_all_tests(test_dir)


if __name__ == "__main__":
    main()
