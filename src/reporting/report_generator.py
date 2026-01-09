"""
Migration report generator.

Creates detailed reports of migration operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from ..data.models.migration import Migration, FileRecord
from ..data.repositories.migration_repository import MigrationRepository


@dataclass
class FileResult:
    """Individual file processing result."""

    file_path: Path
    status: str  # COMPLETED, FAILED, PENDING
    processing_time: float
    changes: Dict[str, int]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class MigrationReport:
    """Complete migration report."""

    migration_id: str
    profile: str
    started_at: datetime
    completed_at: datetime | None
    duration: float
    total_files: int
    successful: int
    failed: int
    pending: int
    success_rate: float
    file_results: List[FileResult] = field(default_factory=list)
    summary: Dict[str, any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Generate text report."""
        lines = [
            "=" * 80,
            f"Migration Report: {self.migration_id}",
            "=" * 80,
            "",
            f"Profile: {self.profile}",
            f"Started: {self.started_at}",
            f"Completed: {self.completed_at or 'In progress'}",
            f"Duration: {self.duration:.1f}s",
            "",
            "Summary:",
            f"  Total files: {self.total_files}",
            f"  Successful: {self.successful}",
            f"  Failed: {self.failed}",
            f"  Pending: {self.pending}",
            f"  Success rate: {self.success_rate:.1%}",
            "",
        ]

        # Add changes summary
        if self.summary.get("changes"):
            lines.append("Changes:")
            for change_type, count in self.summary["changes"].items():
                lines.append(f"  {change_type}: {count}")
            lines.append("")

        # Add failed files
        failed_files = [f for f in self.file_results if f.status == "FAILED"]
        if failed_files:
            lines.append(f"Failed Files ({len(failed_files)}):")
            for file_result in failed_files[:10]:
                lines.append(f"  • {file_result.file_path.name}")
                if file_result.errors:
                    for error in file_result.errors[:2]:
                        lines.append(f"    - {error}")
            if len(failed_files) > 10:
                lines.append(f"  ... and {len(failed_files) - 10} more")

        return "\n".join(lines)


class ReportGenerator:
    """
    Generates migration reports.

    Creates comprehensive reports from migration data.
    """

    def __init__(self, repository: MigrationRepository):
        """
        Initialize report generator.

        Args:
            repository: Migration repository
        """
        self.repository = repository

    def generate_report(self, migration_id: str) -> MigrationReport:
        """
        Generate migration report.

        Args:
            migration_id: Migration to report on

        Returns:
            MigrationReport with all details
        """
        # Get migration
        migration = self.repository.get(migration_id)
        if not migration:
            raise ValueError(f"Migration not found: {migration_id}")

        # Get file records
        file_records = self.repository.get_files(migration_id)

        # Get stats
        stats = self.repository.get_stats(migration_id)

        # Calculate duration
        duration = 0.0
        if migration.started_at and migration.completed_at:
            duration = (migration.completed_at - migration.started_at).total_seconds()

        # Build file results
        file_results = []
        changes_summary = {}

        for record in file_records:
            result = FileResult(
                file_path=record.file_path,
                status=record.status.value,
                processing_time=record.processing_time or 0.0,
                changes=record.changes or {},
                errors=[record.error_message] if record.error_message else [],
                warnings=[],
            )
            file_results.append(result)

            # Aggregate changes
            if record.changes:
                for change_type, count in record.changes.items():
                    changes_summary[change_type] = changes_summary.get(change_type, 0) + count

        # Build report
        return MigrationReport(
            migration_id=migration.migration_id,
            profile=migration.profile,
            started_at=migration.started_at,
            completed_at=migration.completed_at,
            duration=duration,
            total_files=stats["total"],
            successful=stats["successful"],
            failed=stats["failed"],
            pending=stats["pending"],
            success_rate=stats["success_rate"],
            file_results=file_results,
            summary={
                "changes": changes_summary,
                "parallel_workers": migration.parallel_workers,
                "enable_rollback": migration.enable_rollback,
            },
        )

    def generate_summary_report(self, limit: int = 10) -> str:
        """
        Generate summary report of recent migrations.

        Args:
            limit: Number of migrations to include

        Returns:
            Text summary report
        """
        migrations = self.repository.list(limit=limit)

        lines = [
            "=" * 80,
            "Recent Migrations Summary",
            "=" * 80,
            "",
            f"{'Migration ID':<35} {'Status':<12} {'Files':<12} {'Success Rate':<15}",
            "-" * 80,
        ]

        for migration in migrations:
            stats = self.repository.get_stats(migration.migration_id)
            lines.append(
                f"{migration.migration_id:<35} "
                f"{migration.status.value:<12} "
                f"{stats['successful']}/{stats['total']:<10} "
                f"{stats['success_rate']:.1%}"
            )

        return "\n".join(lines)
