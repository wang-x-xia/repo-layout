import subprocess
from typing import Set


def is_git_repo(root_path: str) -> bool:
    """Check if the directory is a git repository using git command"""
    try:
        subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            cwd=root_path,
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_git_ignored_files(root_path: str) -> Set[str]:
    """Get all ignored files using git command (handles all levels of .gitignore)"""
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--others', '--ignored', '--exclude-standard'],
            cwd=root_path,
            capture_output=True,
            text=True,
            check=True
        )
        ignored_files = set()
        for line in result.stdout.strip().split('\n'):
            if line:
                normalized = line.replace('\\', '/')
                ignored_files.add(normalized)
                # Also add directory paths (e.g., ".devin/file" -> ".devin/")
                dir_path = '/'.join(normalized.split('/')[:-1])
                if dir_path:
                    ignored_files.add(dir_path + '/')
        return ignored_files
    except subprocess.CalledProcessError:
        return set()
