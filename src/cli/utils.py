"""
CLI utility functions.

Common helpers for CLI commands.
"""

import sys
from pathlib import Path
from typing import List
import click


def validate_file_exists(file_path: Path) -> Path:
    """
    Validate that file exists.

    Args:
        file_path: File path to check

    Returns:
        Path if exists

    Raises:
        click.BadParameter: If file doesn't exist
    """
    if not file_path.exists():
        raise click.BadParameter(f"File not found: {file_path}")
    return file_path


def validate_directory_exists(dir_path: Path) -> Path:
    """
    Validate that directory exists.

    Args:
        dir_path: Directory path to check

    Returns:
        Path if exists

    Raises:
        click.BadParameter: If directory doesn't exist
    """
    if not dir_path.exists():
        raise click.BadParameter(f"Directory not found: {dir_path}")
    if not dir_path.is_dir():
        raise click.BadParameter(f"Not a directory: {dir_path}")
    return dir_path


def collect_files(path: Path, pattern: str = "*.dxf") -> List[Path]:
    """
    Collect files matching pattern.

    Args:
        path: Directory or single file
        pattern: Glob pattern (default: *.dxf)

    Returns:
        List of file paths
    """
    if path.is_file():
        return [path]

    # Collect files from directory
    files = list(path.glob(pattern))

    # Also check subdirectories
    files.extend(path.glob(f"**/{pattern}"))

    return sorted(set(files))


def format_file_size(bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: Confirmation message
        default: Default value if user just presses enter

    Returns:
        True if confirmed
    """
    return click.confirm(message, default=default)


def echo_success(message: str):
    """Print success message in green."""
    click.secho(f"✓ {message}", fg="green")


def echo_error(message: str):
    """Print error message in red."""
    click.secho(f"✗ {message}", fg="red", err=True)


def echo_warning(message: str):
    """Print warning message in yellow."""
    click.secho(f"⚠ {message}", fg="yellow")


def echo_info(message: str):
    """Print info message in blue."""
    click.secho(f"ℹ {message}", fg="blue")


def handle_error(e: Exception, verbose: bool = False):
    """
    Handle and display error.

    Args:
        e: Exception to handle
        verbose: Show full traceback
    """
    if verbose:
        import traceback
        click.echo(traceback.format_exc(), err=True)
    else:
        echo_error(f"Error: {e}")

    sys.exit(1)


def create_progress_bar(total: int, label: str = "Processing"):
    """
    Create click progress bar.

    Args:
        total: Total items
        label: Progress label

    Returns:
        Progress bar context manager
    """
    return click.progressbar(
        length=total,
        label=label,
        show_eta=True,
        show_percent=True,
    )
