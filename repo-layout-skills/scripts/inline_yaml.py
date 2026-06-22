# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyyaml",
# ]
# ///

import os
import sys
import argparse
import subprocess
import re
import yaml
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# Set stdout encoding to UTF-8 for Windows compatibility
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def find_repo_layout_blocks(content: str) -> List[Tuple[int, int, str]]:
    """
    Find all yaml code blocks with :repo-layout: command in markdown content.
    
    Returns:
        List of tuples (start_line, end_line, command) for each block found
    """
    blocks = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        # Look for yaml code block start
        if line.strip() == '```yaml':
            # Check if the next line has :repo-layout: command
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                match = re.match(r'#\s*:repo-layout:\s*(.+)', next_line)
                if match:
                    command = match.group(1).strip()
                    block_start = i
                    # Find the end of the code block
                    j = i + 2
                    while j < len(lines) and lines[j].strip() != '```':
                        j += 1
                    if j < len(lines):
                        block_end = j
                        blocks.append((block_start, block_end, command))
                    i = j + 1
                    continue
        i += 1
    
    return blocks


def run_command(command: str, cwd: Optional[Path] = None) -> Tuple[str, str, int]:
    """
    Run a command and return stdout, stderr, and return code.
    
    Args:
        command: Command string to execute
        cwd: Working directory for command execution (default: current directory)
    
    Returns:
        Tuple of (stdout, stderr, return_code)
    """
    if cwd is None:
        cwd = Path.cwd()
    
    # Use shell=True for Windows compatibility
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    return result.stdout, result.stderr, result.returncode


def update_file(file_path: Path, root_dir: Optional[Path] = None, dry_run: bool = False) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Update a single markdown file with command results.

    Args:
        file_path: Path to the markdown file
        root_dir: Root directory for relative path calculation
        dry_run: If True, don't actually modify files

    Returns:
        List of tuples (status, block_data)
    """
    results = []

    if not file_path.exists():
        return [('error', {
            'file': str(file_path),
            'line': None,
            'command': None,
            'error': 'File not found'
        })]

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = find_repo_layout_blocks(content)

    if not blocks:
        return []

    modified = False
    lines = content.split('\n')

    # Calculate relative file path
    if root_dir:
        try:
            rel_file_path = file_path.relative_to(root_dir).as_posix()
        except ValueError:
            # file_path is not relative to root_dir, use absolute
            rel_file_path = file_path.as_posix()
    else:
        rel_file_path = file_path.as_posix()

    # Process blocks from end to start to preserve line numbers
    for start, end, command in reversed(blocks):
        block_data = {
            'file': rel_file_path,
            'line': start + 1,
            'command': command
        }
        
        # Get the directory of the markdown file as working directory
        cwd = file_path.parent
        
        # Run the command
        stdout, stderr, returncode = run_command(command, cwd)
        
        if returncode != 0:
            block_data['stdout'] = stdout
            if stderr:
                block_data['stderr'] = stderr
            block_data['returncode'] = returncode
            results.append(('error', block_data))
            continue
        
        # Prepare new block content
        # Keep the opening ```yaml fence
        new_block_lines = [lines[start]]
        # Keep the first line with the command
        new_block_lines.append(lines[start + 1])
        # Add the command output
        new_block_lines.append(stdout.rstrip())
        # Add the closing ```
        new_block_lines.append('```')
        
        # Replace the old block with the new one
        lines[start:end + 1] = new_block_lines
        modified = True
        results.append(('success', block_data))
    
    if modified:
        new_content = '\n'.join(lines)
        # Check if content actually changed
        if new_content == content:
            status = 'up_to_date'
        else:
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            status = 'updated'
        
        # Update status for all successful blocks
        for i in range(len(results)):
            if results[i][0] == 'success':
                results[i] = (status, results[i][1])
    else:
        # This shouldn't happen, but handle it
        for i in range(len(results)):
            if results[i][0] == 'success':
                results[i] = ('up_to_date', results[i][1])
    
    return results


def update_all(root_dir: Path, dry_run: bool = False) -> Dict[str, Any]:
    """
    Update all markdown files in a directory recursively.
    
    Args:
        root_dir: Root directory to search for markdown files
        dry_run: If True, don't actually modify files
    
    Returns:
        Dict with overall results and block details
    """
    
    results = {
        'updated': [],
        'up_to_date': [],
        'failed': []
    }
    
    for md_file in root_dir.rglob('*.md'):
        block_results = update_file(md_file, root_dir=root_dir, dry_run=dry_run)
        
        for status, block_data in block_results:
            if status == 'updated':
                results['updated'].append(block_data)
            elif status == 'up_to_date':
                results['up_to_date'].append(block_data)
            elif status == 'error':
                results['failed'].append(block_data)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Update markdown files with inline command results'
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # update command
    update_parser = subparsers.add_parser('update', help='Update a single file')
    update_parser.add_argument('file', type=Path, help='Markdown file to update')
    update_parser.add_argument('--dry-run', action='store_true',
                               help='Run without actually modifying files')
    update_parser.add_argument('--any-not-up-to-date-exit-1', action='store_true',
                               help='Return exit code 1 if any block is not up-to-date')
    
    # update-all command
    update_all_parser = subparsers.add_parser('update-all', help='Update all markdown files')
    update_all_parser.add_argument('root', nargs='?', type=Path, default=Path.cwd(),
                                   help='Root directory to search (default: current directory)')
    update_all_parser.add_argument('--dry-run', action='store_true',
                                   help='Run without actually modifying files')
    update_all_parser.add_argument('--any-not-up-to-date-exit-1', action='store_true',
                                   help='Return exit code 1 if any block is not up-to-date')
    
    args = parser.parse_args()
    
    if args.command == 'update':
        block_results = update_file(args.file, root_dir=args.file.parent, dry_run=args.dry_run)
        # Categorize block results
        results = {'updated': [], 'up_to_date': [], 'failed': []}
        for status, block_data in block_results:
            if status == 'updated':
                results['updated'].append(block_data)
            elif status == 'up_to_date':
                results['up_to_date'].append(block_data)
            elif status == 'error':
                results['failed'].append(block_data)
        output = yaml.dump(results, allow_unicode=True, default_flow_style=False)
        print(output)
        
        # Return 1 if any block is not up-to-date and --any-not-up-to-date-exit-1 is set
        if args.any_not_up_to_date_exit_1 and (results['updated'] or results['failed']):
            return 1
        return 0
    
    elif args.command == 'update-all':
        results = update_all(args.root, args.dry_run)
        output = yaml.dump(results, allow_unicode=True, default_flow_style=False)
        print(output)
        
        # Return 1 if any block is not up-to-date and --any-not-up-to-date-exit-1 is set
        if args.any_not_up_to_date_exit_1 and (results['updated'] or results['failed']):
            return 1
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
