"""
State machine for batch processing.

Tracks batch state using MigrationRepository for crash recovery and resume support.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

from ..data.models.migration import Migration, MigrationItem, MigrationStatus
from ..data.repositories.migration_repository import MigrationRepository

logger = logging.getLogger(__name__)


class StateManager:
    """Manages batch processing state with crash recovery."""

    def __init__(self, repository: MigrationRepository, migration_id: str):
        """
        Initialize state manager.

        Args:
            repository: Migration repository for persistence
            migration_id: Migration ID to track
        """
        self.repository = repository
        self.migration_id = migration_id
        self.migration: Optional[Migration] = None

    def initialize(
        self,
        profile: str,
        files: List[Path],
        standards_version: str,
        enable_rollback: bool = True,
        parallel_workers: int = 1,
    ) -> None:
        """
        Initialize new migration or load existing.

        Args:
            profile: Migration profile name
            files: List of files to process
            standards_version: Standards version
            enable_rollback: Enable rollback support
            parallel_workers: Number of parallel workers
        """
        # Check if migration already exists (resume)
        existing = self.repository.get(self.migration_id)

        if existing:
            logger.info(f"Resuming existing migration: {self.migration_id}")
            self.migration = existing
        else:
            logger.info(f"Creating new migration: {self.migration_id}")
            self.migration = Migration(
                migration_id=self.migration_id,
                profile=profile,
                standards_version=standards_version,
                enable_rollback=enable_rollback,
                parallel_workers=parallel_workers,
            )

            # Add items for all files
            for file_path in files:
                item = MigrationItem(
                    file_path=file_path,
                    migration_id=self.migration_id,
                )
                self.migration.add_item(item)

            # Save initial state
            self.repository.save(self.migration)

    def get_pending_files(self) -> List[Path]:
        """
        Get list of files still pending processing.

        Returns:
            List of file paths with PENDING status
        """
        return self.repository.get_pending_files(self.migration_id)

    def record_success(
        self,
        file_path: Path,
        output_path: Path,
        processing_time: float,
        changes: dict,
    ) -> None:
        """
        Record successful file processing.

        Args:
            file_path: Input file path
            output_path: Output file path
            processing_time: Processing time in seconds
            changes: Dictionary of changes made
        """
        # Find item
        item = self._find_item(file_path)
        if not item:
            logger.error(f"Item not found for {file_path}")
            return

        # Update item
        item.status = MigrationStatus.COMPLETED
        item.output_path = output_path
        item.completed_at = datetime.now()
        item.processing_time = processing_time
        item.changes = changes

        # Update migration stats
        self.migration.successful_files += 1

        # Save
        self.repository.save(self.migration)
        logger.debug(f"Recorded success for {file_path}")

    def record_failure(self, file_path: Path, error: str) -> None:
        """
        Record failed file processing.

        Args:
            file_path: File that failed
            error: Error message
        """
        # Find item
        item = self._find_item(file_path)
        if not item:
            logger.error(f"Item not found for {file_path}")
            return

        # Update item
        item.status = MigrationStatus.FAILED
        item.error = error
        item.completed_at = datetime.now()

        # Update migration stats
        self.migration.failed_files += 1

        # Save
        self.repository.save(self.migration)
        logger.debug(f"Recorded failure for {file_path}: {error}")

    def mark_started(self) -> None:
        """Mark migration as started."""
        self.migration.status = MigrationStatus.PARSED  # In progress
        self.migration.started_at = datetime.now()
        self.repository.save(self.migration)
        logger.info(f"Migration {self.migration_id} started")

    def mark_completed(self) -> None:
        """Mark migration as completed."""
        self.migration.status = MigrationStatus.COMPLETED
        self.migration.completed_at = datetime.now()

        # Calculate total processing time
        if self.migration.started_at and self.migration.completed_at:
            delta = self.migration.completed_at - self.migration.started_at
            self.migration.total_processing_time = delta.total_seconds()

        self.repository.save(self.migration)
        logger.info(
            f"Migration {self.migration_id} completed: "
            f"{self.migration.successful_files}/{self.migration.total_files} successful"
        )

    def mark_failed(self, reason: str) -> None:
        """Mark migration as failed."""
        self.migration.status = MigrationStatus.FAILED
        self.migration.completed_at = datetime.now()
        self.repository.save(self.migration)
        logger.error(f"Migration {self.migration_id} failed: {reason}")

    def checkpoint(self) -> None:
        """Force checkpoint (save current state)."""
        self.repository.save(self.migration)
        self.repository.db.checkpoint()
        logger.debug(f"Checkpointed migration {self.migration_id}")

    def get_stats(self) -> dict:
        """Get current statistics."""
        return {
            "total": self.migration.total_files,
            "successful": self.migration.successful_files,
            "failed": self.migration.failed_files,
            "pending": self.migration.total_files
            - self.migration.successful_files
            - self.migration.failed_files,
            "success_rate": self.migration.get_success_rate(),
        }

    def _find_item(self, file_path: Path) -> Optional[MigrationItem]:
        """Find migration item by file path."""
        for item in self.migration.items:
            if item.file_path == file_path:
                return item
        return None
