"""
Progress reporter for batch processing.

Provides Rich console progress bars and status updates for long-running operations.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import logging

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich import box

logger = logging.getLogger(__name__)


class ProgressReporter:
    """Reports batch processing progress with Rich console."""

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize progress reporter.

        Args:
            console: Rich console instance (creates new if None)
        """
        self.console = console or Console()
        self.progress: Optional[Progress] = None
        self.task_id: Optional[int] = None
        self.start_time: Optional[datetime] = None

    def start(self, total_files: int, description: str = "Processing files") -> None:
        """
        Start progress tracking.

        Args:
            total_files: Total number of files to process
            description: Progress bar description
        """
        self.start_time = datetime.now()

        # Create progress bar with multiple columns
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console,
        )

        self.progress.start()
        self.task_id = self.progress.add_task(description, total=total_files)

        logger.info(f"Started progress tracking: {total_files} files")

    def update(self, advance: int = 1, description: Optional[str] = None) -> None:
        """
        Update progress.

        Args:
            advance: Number of files completed
            description: Optional new description
        """
        if self.progress and self.task_id is not None:
            update_kwargs = {"advance": advance}
            if description:
                update_kwargs["description"] = description

            self.progress.update(self.task_id, **update_kwargs)

    def stop(self) -> None:
        """Stop progress tracking."""
        if self.progress:
            self.progress.stop()
            self.progress = None
            self.task_id = None

        logger.info("Stopped progress tracking")

    def print_summary(self, stats: dict) -> None:
        """
        Print batch processing summary.

        Args:
            stats: Statistics dictionary with keys:
                - total: Total files
                - successful: Successful count
                - failed: Failed count
                - pending: Pending count
                - success_rate: Success rate (0-1)
        """
        # Calculate elapsed time
        elapsed = datetime.now() - self.start_time if self.start_time else timedelta(0)
        elapsed_str = self._format_timedelta(elapsed)

        # Calculate rates
        total_processed = stats["successful"] + stats["failed"]
        avg_time = elapsed.total_seconds() / total_processed if total_processed > 0 else 0

        # Create summary table
        table = Table(title="Batch Processing Summary", box=box.ROUNDED, show_header=True)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # Add rows
        table.add_row("Total Files", str(stats["total"]))
        table.add_row("Successful", f"[green]{stats['successful']}[/green]")
        table.add_row("Failed", f"[red]{stats['failed']}[/red]")
        table.add_row("Pending", str(stats["pending"]))
        table.add_row("Success Rate", f"{stats['success_rate']:.1%}")
        table.add_row("Total Time", elapsed_str)
        table.add_row("Avg Time/File", f"{avg_time:.2f}s")

        # Print table
        self.console.print()
        self.console.print(table)

    def print_file_result(self, file_path: Path, success: bool, message: str = "") -> None:
        """
        Print individual file result.

        Args:
            file_path: File that was processed
            success: Whether processing succeeded
            message: Optional message (error or info)
        """
        if success:
            status = "[green]✓[/green]"
            color = "green"
        else:
            status = "[red]✗[/red]"
            color = "red"

        output = f"{status} {file_path.name}"
        if message:
            output += f" - [{color}]{message}[/{color}]"

        self.console.print(output)

    def print_validation_summary(
        self,
        file_path: Path,
        validation_errors: int,
        validation_warnings: int,
        issues: list = None,
    ) -> None:
        """
        Print validation summary for a file.

        Args:
            file_path: File that was validated
            validation_errors: Number of errors
            validation_warnings: Number of warnings
            issues: Optional list of validation issues
        """
        # Create validation panel
        if validation_errors > 0:
            title = f"[red]Validation Failed: {file_path.name}[/red]"
            border_style = "red"
        elif validation_warnings > 0:
            title = f"[yellow]Validation Warnings: {file_path.name}[/yellow]"
            border_style = "yellow"
        else:
            title = f"[green]Validation Passed: {file_path.name}[/green]"
            border_style = "green"

        content = f"Errors: {validation_errors}, Warnings: {validation_warnings}"

        # Add issue details if provided
        if issues:
            issue_text = "\n".join([f"  • {issue}" for issue in issues[:5]])  # Limit to 5
            if len(issues) > 5:
                issue_text += f"\n  ... and {len(issues) - 5} more"
            content += f"\n\n{issue_text}"

        panel = Panel(content, title=title, border_style=border_style, box=box.ROUNDED)
        self.console.print(panel)

    def print_error(self, message: str, error: Exception = None) -> None:
        """
        Print error message.

        Args:
            message: Error message
            error: Optional exception
        """
        output = f"[red]Error:[/red] {message}"
        if error:
            output += f"\n[red]{type(error).__name__}:[/red] {str(error)}"

        self.console.print(output)
        logger.error(message, exc_info=error)

    def print_warning(self, message: str) -> None:
        """
        Print warning message.

        Args:
            message: Warning message
        """
        self.console.print(f"[yellow]Warning:[/yellow] {message}")
        logger.warning(message)

    def print_info(self, message: str) -> None:
        """
        Print info message.

        Args:
            message: Info message
        """
        self.console.print(f"[blue]Info:[/blue] {message}")
        logger.info(message)

    def _format_timedelta(self, td: timedelta) -> str:
        """
        Format timedelta as human-readable string.

        Args:
            td: Timedelta to format

        Returns:
            Formatted string (e.g., "1h 23m 45s")
        """
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)


class LiveProgressReporter(ProgressReporter):
    """Progress reporter with live updating display."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize live progress reporter."""
        super().__init__(console)
        self.live: Optional[Live] = None
        self.stats_table: Optional[Table] = None

    def start_live(
        self,
        total_files: int,
        description: str = "Processing files",
        show_stats: bool = True,
    ) -> None:
        """
        Start live progress with stats table.

        Args:
            total_files: Total number of files
            description: Progress description
            show_stats: Show live stats table
        """
        self.start_time = datetime.now()

        # Create progress bar
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        self.task_id = self.progress.add_task(description, total=total_files)

        # Create stats table if enabled
        if show_stats:
            self.stats_table = self._create_stats_table(0, 0, 0)

            # Combine progress and stats
            from rich.layout import Layout

            layout = Layout()
            layout.split_column(
                Layout(self.progress),
                Layout(self.stats_table),
            )

            self.live = Live(layout, console=self.console, refresh_per_second=4)
        else:
            self.live = Live(self.progress, console=self.console, refresh_per_second=4)

        self.live.start()
        logger.info(f"Started live progress: {total_files} files")

    def update_live(
        self,
        advance: int = 1,
        successful: int = 0,
        failed: int = 0,
        pending: int = 0,
    ) -> None:
        """
        Update live progress and stats.

        Args:
            advance: Files to advance
            successful: Current successful count
            failed: Current failed count
            pending: Current pending count
        """
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, advance=advance)

        # Update stats table if present
        if self.stats_table:
            self.stats_table = self._create_stats_table(successful, failed, pending)

            # Update live display
            if self.live:
                from rich.layout import Layout

                layout = Layout()
                layout.split_column(
                    Layout(self.progress),
                    Layout(self.stats_table),
                )
                self.live.update(layout)

    def stop_live(self) -> None:
        """Stop live progress."""
        if self.live:
            self.live.stop()
            self.live = None

        if self.progress:
            self.progress = None
            self.task_id = None

        logger.info("Stopped live progress")

    def _create_stats_table(self, successful: int, failed: int, pending: int) -> Table:
        """Create stats table."""
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column(style="white")

        total = successful + failed + pending
        success_rate = (successful / total * 100) if total > 0 else 0

        table.add_row("Successful:", f"[green]{successful}[/green]")
        table.add_row("Failed:", f"[red]{failed}[/red]")
        table.add_row("Pending:", f"{pending}")
        table.add_row("Success Rate:", f"{success_rate:.1f}%")

        return table
