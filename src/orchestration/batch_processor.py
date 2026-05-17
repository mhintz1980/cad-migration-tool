"""
Batch processor for parallel CAD file processing.

Orchestrates parallel processing using ProcessPoolExecutor with:
- State management and crash recovery
- Rollback support
- Progress reporting
- Error handling with continue-on-error
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import logging
from datetime import datetime

from .worker import WorkerConfig, WorkerResult, process_file
from .state_machine import StateManager
from .rollback import RollbackManager
from .progress import ProgressReporter, LiveProgressReporter
from ..data.repositories.migration_repository import MigrationRepository
from ..data.repositories.database import Database

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    standards_config_path: Path
    profile: str
    migration_id: str
    parallel_workers: int = 4
    enable_validation: bool = True
    enable_pre_validation: bool = True
    enable_post_validation: bool = True
    enable_rollback: bool = True
    continue_on_error: bool = True
    max_failures: int = 50
    checkpoint_interval: int = 10  # Checkpoint every N files
    backup_dir: Path = field(default_factory=lambda: Path("backups"))
    db_path: Path = field(default_factory=lambda: Path("data/migrations.db"))


class BatchProcessor:
    """Orchestrates parallel batch processing of CAD files."""

    def __init__(self, config: BatchConfig):
        """
        Initialize batch processor.

        Args:
            config: Batch processing configuration
        """
        self.config = config

        # Initialize components
        self.db = Database(self.config.db_path)
        self.repository = MigrationRepository(self.db)
        self.state_manager = StateManager(self.repository, self.config.migration_id)
        self.rollback_manager = RollbackManager(self.config.backup_dir)
        self.progress_reporter = LiveProgressReporter()

        # Worker configuration
        self.worker_config = WorkerConfig(
            standards_config_path=self.config.standards_config_path,
            profile=self.config.profile,
            enable_validation=self.config.enable_validation,
            enable_pre_validation=self.config.enable_pre_validation,
            enable_post_validation=self.config.enable_post_validation,
        )

        # Runtime state
        self.failure_count = 0
        self.should_stop = False

    def process_batch(
        self,
        files: List[Path],
        resume: bool = False,
        live_progress: bool = True,
    ) -> dict:
        """
        Process batch of CAD files with parallel execution.

        Args:
            files: List of CAD files to process
            resume: Resume from previous state (ignores files arg)
            live_progress: Use live updating progress display

        Returns:
            Dictionary with processing statistics:
            - total: Total files
            - successful: Successful count
            - failed: Failed count
            - pending: Pending count
            - success_rate: Success rate (0-1)
            - processing_time: Total processing time in seconds
            - errors: List of error messages
        """
        start_time = datetime.now()

        try:
            # Initialize or resume state
            if resume:
                logger.info(f"Resuming migration: {self.config.migration_id}")
                self.state_manager.migration = self.repository.get(self.config.migration_id)
                if not self.state_manager.migration:
                    raise ValueError(f"Migration {self.config.migration_id} not found for resume")
                files_to_process = self.state_manager.get_pending_files()
            else:
                logger.info(f"Starting new migration: {self.config.migration_id}")
                self.state_manager.initialize(
                    profile=self.config.profile,
                    files=files,
                    standards_version="1.0",  # TODO: Get from standards config
                    enable_rollback=self.config.enable_rollback,
                    parallel_workers=self.config.parallel_workers,
                )
                files_to_process = files
                self.state_manager.mark_started()

            # Check if there's work to do
            if not files_to_process:
                logger.warning("No files to process")
                stats = self.state_manager.get_stats()
                stats["processing_time"] = 0.0
                stats["errors"] = []
                return stats

            # Start progress
            if live_progress:
                self.progress_reporter.start_live(
                    total_files=len(files_to_process),
                    description="Processing CAD files",
                    show_stats=True,
                )
            else:
                self.progress_reporter.start(
                    total_files=len(files_to_process),
                    description="Processing CAD files",
                )

            # Process files with ProcessPoolExecutor
            stats = self._process_with_executor(files_to_process, live_progress)

            # Finalize
            if self.should_stop:
                self.state_manager.mark_failed(f"Stopped: {self.failure_count} failures exceeded max {self.config.max_failures}")
            else:
                self.state_manager.mark_completed()

            # Stop progress
            if live_progress:
                self.progress_reporter.stop_live()
            else:
                self.progress_reporter.stop()

            # Calculate total time
            end_time = datetime.now()
            stats["processing_time"] = (end_time - start_time).total_seconds()

            # Print summary
            self.progress_reporter.print_summary(stats)

            return stats

        except Exception as e:
            logger.error(f"Batch processing failed: {e}", exc_info=True)
            self.state_manager.mark_failed(str(e))
            raise

    def _process_with_executor(
        self,
        files: List[Path],
        live_progress: bool,
    ) -> dict:
        """
        Process files using ProcessPoolExecutor.

        Args:
            files: Files to process
            live_progress: Use live progress updates

        Returns:
            Statistics dictionary
        """
        processed_count = 0
        errors = []

        with ProcessPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            # Submit all files
            future_to_file = {
                executor.submit(process_file, file_path, self.worker_config): file_path
                for file_path in files
            }

            # Process as they complete
            for future in as_completed(future_to_file):
                if self.should_stop:
                    # Cancel remaining futures
                    for f in future_to_file:
                        f.cancel()
                    break

                file_path = future_to_file[future]

                try:
                    result: WorkerResult = future.result()

                    # Create backup if rollback enabled and success
                    if self.config.enable_rollback and result.success and result.output_path:
                        try:
                            self.rollback_manager.create_backup(
                                file_path,
                                self.config.migration_id,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to create backup for {file_path}: {e}")

                    # Record result
                    if result.success:
                        self.state_manager.record_success(
                            file_path=result.file_path,
                            output_path=result.output_path,
                            processing_time=result.processing_time,
                            changes=result.changes,
                        )
                        self.progress_reporter.print_file_result(
                            result.file_path,
                            success=True,
                            message=f"Processed in {result.processing_time:.2f}s",
                        )
                    else:
                        self.state_manager.record_failure(
                            file_path=result.file_path,
                            error=result.error or "Unknown error",
                        )
                        self.failure_count += 1
                        errors.append(f"{file_path.name}: {result.error}")

                        self.progress_reporter.print_file_result(
                            result.file_path,
                            success=False,
                            message=result.error,
                        )

                        # Check if we should stop
                        if not self.config.continue_on_error:
                            logger.error(f"Stopping on first failure: {result.error}")
                            self.should_stop = True
                        elif self.failure_count >= self.config.max_failures:
                            logger.error(
                                f"Stopping: failure count {self.failure_count} "
                                f"exceeded max {self.config.max_failures}"
                            )
                            self.should_stop = True

                    # Print validation summary if there were issues
                    if result.validation_errors > 0 or result.validation_warnings > 0:
                        self.progress_reporter.print_validation_summary(
                            result.file_path,
                            result.validation_errors,
                            result.validation_warnings,
                            result.warnings,
                        )

                except Exception as e:
                    # Executor-level failure (shouldn't happen often)
                    logger.error(f"Executor error processing {file_path}: {e}", exc_info=True)
                    self.state_manager.record_failure(file_path, str(e))
                    self.failure_count += 1
                    errors.append(f"{file_path.name}: {e}")

                    if not self.config.continue_on_error or self.failure_count >= self.config.max_failures:
                        self.should_stop = True

                finally:
                    processed_count += 1

                    # Update progress
                    stats = self.state_manager.get_stats()
                    if live_progress:
                        self.progress_reporter.update_live(
                            advance=1,
                            successful=stats["successful"],
                            failed=stats["failed"],
                            pending=stats["pending"],
                        )
                    else:
                        self.progress_reporter.update(advance=1)

                    # Checkpoint periodically
                    if processed_count % self.config.checkpoint_interval == 0:
                        self.state_manager.checkpoint()
                        logger.debug(f"Checkpoint at {processed_count} files")

        # Final checkpoint
        self.state_manager.checkpoint()

        # Return final stats
        stats = self.state_manager.get_stats()
        stats["errors"] = errors
        return stats

    def rollback(self) -> dict:
        """
        Rollback the migration.

        Returns:
            Dictionary with rollback statistics from RollbackManager
        """
        logger.info(f"Rolling back migration: {self.config.migration_id}")

        self.progress_reporter.print_info(f"Rolling back migration {self.config.migration_id}...")

        stats = self.rollback_manager.rollback_migration(
            self.config.migration_id,
            self.repository,
        )

        # Print results
        if stats["failed_count"] == 0:
            self.progress_reporter.print_info(
                f"Rollback complete: {stats['restored_count']} files restored"
            )
        else:
            self.progress_reporter.print_warning(
                f"Rollback partial: {stats['restored_count']} restored, "
                f"{stats['failed_count']} failed"
            )

            for error in stats["errors"]:
                self.progress_reporter.print_error(error)

        return stats

    def get_status(self) -> dict:
        """
        Get current processing status.

        Returns:
            Dictionary with migration status and statistics
        """
        if not self.state_manager.migration:
            return {"status": "not_initialized"}

        stats = self.state_manager.get_stats()
        migration = self.state_manager.migration

        # Handle datetime fields (may be datetime or string)
        started_at = migration.started_at
        if started_at and not isinstance(started_at, str):
            started_at = started_at.isoformat()

        completed_at = migration.completed_at
        if completed_at and not isinstance(completed_at, str):
            completed_at = completed_at.isoformat()

        return {
            "status": migration.status.value,
            "migration_id": migration.migration_id,
            "profile": migration.profile,
            "started_at": started_at,
            "completed_at": completed_at,
            "stats": stats,
        }

    def cleanup_old_backups(self, max_age_days: int = 30) -> dict:
        """
        Clean up old backups.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Cleanup statistics from RollbackManager
        """
        logger.info(f"Cleaning up backups older than {max_age_days} days")
        return self.rollback_manager.cleanup_old_backups(max_age_days)
