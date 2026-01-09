"""
Performance monitoring system.

Tracks performance metrics and generates reports.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path
import time


@dataclass
class PerformanceReport:
    """Performance report for migration operations."""

    start_time: datetime
    end_time: datetime
    duration: float  # seconds
    files_processed: int
    files_succeeded: int
    files_failed: int
    total_file_size: int  # bytes
    throughput: float  # files per second
    avg_file_time: float  # seconds per file
    success_rate: float  # 0.0-1.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 60,
            "Performance Report",
            "=" * 60,
            f"Duration: {self.duration:.2f}s",
            f"Files Processed: {self.files_processed}",
            f"  - Succeeded: {self.files_succeeded}",
            f"  - Failed: {self.files_failed}",
            f"Success Rate: {self.success_rate:.1%}",
            f"Throughput: {self.throughput:.2f} files/sec",
            f"Avg File Time: {self.avg_file_time:.2f}s",
            f"Total Size: {self._format_bytes(self.total_file_size)}",
            "",
        ]

        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            for error in self.errors[:5]:
                lines.append(f"  - {error}")
            if len(self.errors) > 5:
                lines.append(f"  ... and {len(self.errors) - 5} more")
            lines.append("")

        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            for warning in self.warnings[:5]:
                lines.append(f"  - {warning}")
            if len(self.warnings) > 5:
                lines.append(f"  ... and {len(self.warnings) - 5} more")

        return "\n".join(lines)

    def _format_bytes(self, bytes: int) -> str:
        """Format bytes in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} TB"

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "files_processed": self.files_processed,
            "files_succeeded": self.files_succeeded,
            "files_failed": self.files_failed,
            "total_file_size": self.total_file_size,
            "throughput": self.throughput,
            "avg_file_time": self.avg_file_time,
            "success_rate": self.success_rate,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


class PerformanceMonitor:
    """
    Monitors performance of migration operations.

    Tracks timing, throughput, and resource usage.
    """

    def __init__(self):
        """Initialize performance monitor."""
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.files_processed: int = 0
        self.files_succeeded: int = 0
        self.files_failed: int = 0
        self.total_file_size: int = 0
        self.file_times: List[float] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, any] = {}

    def start(self):
        """Start monitoring."""
        self.start_time = datetime.now()

    def stop(self):
        """Stop monitoring."""
        self.end_time = datetime.now()

    def record_file_processed(
        self,
        file_path: Path,
        success: bool,
        processing_time: float,
        error: str | None = None,
    ):
        """
        Record processed file.

        Args:
            file_path: File that was processed
            success: Whether processing succeeded
            processing_time: Time taken in seconds
            error: Optional error message
        """
        self.files_processed += 1

        if success:
            self.files_succeeded += 1
        else:
            self.files_failed += 1
            if error:
                self.errors.append(f"{file_path.name}: {error}")

        self.file_times.append(processing_time)

        # Track file size
        if file_path.exists():
            self.total_file_size += file_path.stat().st_size

    def add_warning(self, warning: str):
        """Add warning message."""
        self.warnings.append(warning)

    def add_metric(self, name: str, value: any):
        """Add custom metric."""
        self.metrics[name] = value

    def generate_report(self) -> PerformanceReport:
        """
        Generate performance report.

        Returns:
            PerformanceReport with all metrics
        """
        if not self.start_time or not self.end_time:
            raise RuntimeError("Monitor not started/stopped properly")

        duration = (self.end_time - self.start_time).total_seconds()
        throughput = self.files_processed / duration if duration > 0 else 0
        avg_file_time = (
            sum(self.file_times) / len(self.file_times) if self.file_times else 0
        )
        success_rate = (
            self.files_succeeded / self.files_processed if self.files_processed > 0 else 0
        )

        return PerformanceReport(
            start_time=self.start_time,
            end_time=self.end_time,
            duration=duration,
            files_processed=self.files_processed,
            files_succeeded=self.files_succeeded,
            files_failed=self.files_failed,
            total_file_size=self.total_file_size,
            throughput=throughput,
            avg_file_time=avg_file_time,
            success_rate=success_rate,
            errors=self.errors,
            warnings=self.warnings,
            metrics=self.metrics,
        )

    def reset(self):
        """Reset all metrics."""
        self.start_time = None
        self.end_time = None
        self.files_processed = 0
        self.files_succeeded = 0
        self.files_failed = 0
        self.total_file_size = 0
        self.file_times.clear()
        self.errors.clear()
        self.warnings.clear()
        self.metrics.clear()
