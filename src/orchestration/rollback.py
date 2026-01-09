"""
Rollback manager for CAD file migrations.

Provides backup and restore functionality with full-file copy strategy.
Binary CAD files require complete copies rather than diff-based backups.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import shutil
import logging

from ..data.repositories.migration_repository import MigrationRepository
from ..data.models.migration import MigrationStatus

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages file backups and rollback operations."""

    def __init__(self, backup_dir: Path):
        """
        Initialize rollback manager.

        Args:
            backup_dir: Root directory for all backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, file_path: Path, migration_id: str) -> Path:
        """
        Create full copy backup before modification.

        Args:
            file_path: File to backup
            migration_id: Migration ID for organization

        Returns:
            Path to backup file

        Raises:
            FileNotFoundError: If source file doesn't exist
            IOError: If backup fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        # Create migration backup directory
        migration_backup_dir = self.backup_dir / migration_id
        migration_backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup filename: original_name.bak
        backup_path = migration_backup_dir / f"{file_path.name}.bak"

        # Handle duplicate backups (shouldn't happen in normal flow)
        if backup_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = migration_backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}.bak"

        # Full file copy
        try:
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {file_path} -> {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup of {file_path}: {e}")
            raise IOError(f"Backup failed: {e}") from e

    def rollback_file(self, backup_path: Path, original_path: Path) -> None:
        """
        Restore single file from backup.

        Args:
            backup_path: Path to backup file
            original_path: Path to restore to

        Raises:
            FileNotFoundError: If backup doesn't exist
            IOError: If restore fails
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            # Ensure parent directory exists
            original_path.parent.mkdir(parents=True, exist_ok=True)

            # Restore backup to original location
            shutil.copy2(backup_path, original_path)
            logger.info(f"Restored file: {backup_path} -> {original_path}")
        except Exception as e:
            logger.error(f"Failed to restore {backup_path} to {original_path}: {e}")
            raise IOError(f"Restore failed: {e}") from e

    def rollback_migration(
        self,
        migration_id: str,
        repository: MigrationRepository,
    ) -> dict:
        """
        Rollback entire migration by restoring all backed up files.

        Args:
            migration_id: Migration to rollback
            repository: Migration repository for tracking

        Returns:
            Dictionary with rollback statistics:
            - restored_count: Number of files restored
            - failed_count: Number of restore failures
            - errors: List of error messages
        """
        migration_backup_dir = self.backup_dir / migration_id

        if not migration_backup_dir.exists():
            logger.warning(f"No backup directory found for migration {migration_id}")
            return {"restored_count": 0, "failed_count": 0, "errors": ["No backups found"]}

        # Get migration record
        migration = repository.get(migration_id)
        if not migration:
            logger.error(f"Migration {migration_id} not found in repository")
            return {"restored_count": 0, "failed_count": 0, "errors": ["Migration not found"]}

        stats = {
            "restored_count": 0,
            "failed_count": 0,
            "errors": [],
        }

        # Restore each backed up file
        backup_files = list(migration_backup_dir.glob("*.bak"))
        logger.info(f"Rolling back {len(backup_files)} files for migration {migration_id}")

        for backup_path in backup_files:
            # Determine original path from migration items
            original_name = backup_path.stem  # Remove .bak extension
            original_path = self._find_original_path(original_name, migration)

            if not original_path:
                error_msg = f"Could not determine original path for backup: {backup_path.name}"
                logger.warning(error_msg)
                stats["errors"].append(error_msg)
                stats["failed_count"] += 1
                continue

            try:
                self.rollback_file(backup_path, original_path)
                stats["restored_count"] += 1
            except Exception as e:
                error_msg = f"Failed to restore {backup_path.name}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
                stats["failed_count"] += 1

        # Update migration status
        if stats["failed_count"] == 0:
            logger.info(f"Migration {migration_id} fully rolled back: {stats['restored_count']} files restored")
        else:
            logger.warning(
                f"Migration {migration_id} partially rolled back: "
                f"{stats['restored_count']} restored, {stats['failed_count']} failed"
            )

        return stats

    def cleanup_old_backups(self, max_age_days: int = 30) -> dict:
        """
        Remove backups older than max_age_days.

        Args:
            max_age_days: Maximum age in days for backups

        Returns:
            Dictionary with cleanup statistics:
            - removed_migrations: Number of migration backup dirs removed
            - freed_bytes: Approximate bytes freed
            - errors: List of error messages
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        stats = {
            "removed_migrations": 0,
            "freed_bytes": 0,
            "errors": [],
        }

        logger.info(f"Cleaning up backups older than {max_age_days} days (before {cutoff_date})")

        # Iterate through migration backup directories
        for migration_dir in self.backup_dir.iterdir():
            if not migration_dir.is_dir():
                continue

            # Check directory modification time
            mtime = datetime.fromtimestamp(migration_dir.stat().st_mtime)

            if mtime < cutoff_date:
                # Calculate size before deletion
                dir_size = sum(f.stat().st_size for f in migration_dir.rglob("*") if f.is_file())

                try:
                    shutil.rmtree(migration_dir)
                    stats["removed_migrations"] += 1
                    stats["freed_bytes"] += dir_size
                    logger.info(f"Removed old backup: {migration_dir.name} ({dir_size:,} bytes)")
                except Exception as e:
                    error_msg = f"Failed to remove {migration_dir.name}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

        logger.info(
            f"Cleanup complete: {stats['removed_migrations']} migrations removed, "
            f"{stats['freed_bytes']:,} bytes freed"
        )

        return stats

    def list_backups(self, migration_id: Optional[str] = None) -> List[dict]:
        """
        List available backups.

        Args:
            migration_id: Optional filter for specific migration

        Returns:
            List of backup info dictionaries with keys:
            - migration_id: Migration identifier
            - file_count: Number of backed up files
            - total_size: Total size in bytes
            - created_at: Creation timestamp
        """
        backups = []

        if migration_id:
            # Single migration
            migration_dirs = [self.backup_dir / migration_id]
        else:
            # All migrations
            migration_dirs = [d for d in self.backup_dir.iterdir() if d.is_dir()]

        for migration_dir in migration_dirs:
            if not migration_dir.exists():
                continue

            # Get backup files
            backup_files = list(migration_dir.glob("*.bak"))
            total_size = sum(f.stat().st_size for f in backup_files)
            created_at = datetime.fromtimestamp(migration_dir.stat().st_ctime)

            backups.append({
                "migration_id": migration_dir.name,
                "file_count": len(backup_files),
                "total_size": total_size,
                "created_at": created_at,
            })

        return backups

    def _find_original_path(self, original_name: str, migration) -> Optional[Path]:
        """
        Find original file path from migration items.

        Args:
            original_name: Original filename (without .bak)
            migration: Migration object with items

        Returns:
            Original Path or None if not found
        """
        # Check each migration item
        for item in migration.items:
            if item.file_path.name == original_name:
                return item.file_path

        # Fallback: check output paths for items that were processed
        for item in migration.items:
            if item.output_path and item.output_path.name == original_name:
                return item.output_path

        return None
