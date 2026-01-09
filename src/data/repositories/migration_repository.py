"""
SQLite-based repository for migration history and runtime state.

Stores Migration and MigrationItem objects for queryable history,
crash recovery, and resume support.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from ..models.migration import Migration, MigrationItem, MigrationStatus
from .base_repository import Repository
from .database import Database

logger = logging.getLogger(__name__)


class MigrationRepository(Repository[Migration]):
    """Repository for migration state stored in SQLite."""

    # Database schema
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS migrations (
        id TEXT PRIMARY KEY,
        profile TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        status TEXT NOT NULL,
        standards_version TEXT,
        enable_rollback INTEGER DEFAULT 1,
        parallel_workers INTEGER DEFAULT 1,
        total_files INTEGER DEFAULT 0,
        successful_files INTEGER DEFAULT 0,
        failed_files INTEGER DEFAULT 0,
        skipped_files INTEGER DEFAULT 0,
        total_processing_time REAL
    );

    CREATE TABLE IF NOT EXISTS migration_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_id TEXT NOT NULL REFERENCES migrations(id) ON DELETE CASCADE,
        file_path TEXT NOT NULL,
        status TEXT NOT NULL,
        backup_path TEXT,
        output_path TEXT,
        error TEXT,
        warnings TEXT,  -- JSON array
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        processing_time REAL,
        changes TEXT,  -- JSON object
        metadata TEXT,  -- JSON object
        UNIQUE(migration_id, file_path)
    );

    CREATE INDEX IF NOT EXISTS idx_migration_status ON migrations(status);
    CREATE INDEX IF NOT EXISTS idx_migration_date ON migrations(created_at);
    CREATE INDEX IF NOT EXISTS idx_migration_profile ON migrations(profile);
    CREATE INDEX IF NOT EXISTS idx_item_migration ON migration_items(migration_id);
    CREATE INDEX IF NOT EXISTS idx_item_status ON migration_items(status);
    CREATE INDEX IF NOT EXISTS idx_item_file ON migration_items(file_path);
    """

    SCHEMA_VERSION = 1

    def __init__(self, db: Database):
        """
        Initialize migration repository.

        Args:
            db: Database instance
        """
        self.db = db
        self._init_schema()
        logger.info("Initialized migration repository")

    def _init_schema(self) -> None:
        """Initialize database schema if needed."""
        # Check schema version
        current_version = self.db.get_schema_version() or 0

        if current_version < self.SCHEMA_VERSION:
            logger.info(
                f"Initializing schema (current: {current_version}, target: {self.SCHEMA_VERSION})"
            )
            self.db.execute_script(self.SCHEMA)
            self.db.set_schema_version(self.SCHEMA_VERSION)
        else:
            logger.debug(f"Schema up to date (version {current_version})")

    def get(self, migration_id: str) -> Optional[Migration]:
        """
        Load migration with all items.

        Args:
            migration_id: Migration ID

        Returns:
            Migration if found, None otherwise
        """
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM migrations WHERE id = ?", (migration_id,)
            ).fetchone()

            if not row:
                logger.debug(f"Migration '{migration_id}' not found")
                return None

            items = conn.execute(
                "SELECT * FROM migration_items WHERE migration_id = ? ORDER BY id",
                (migration_id,),
            ).fetchall()

            migration = self._row_to_migration(row, items)
            logger.debug(f"Loaded migration '{migration_id}' with {len(items)} items")
            return migration

    def list(
        self,
        status: Optional[str] = None,
        profile: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        **filters,
    ) -> List[Migration]:
        """
        List migrations with filters.

        Args:
            status: Filter by status
            profile: Filter by profile
            since: Filter by created_at >= since
            limit: Maximum results
            **filters: Additional filters (not currently used)

        Returns:
            List of Migration objects
        """
        query = "SELECT * FROM migrations WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if profile:
            query += " AND profile = ?"
            params.append(profile)

        if since:
            query += " AND created_at >= ?"
            params.append(since.isoformat())

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self.db.connection() as conn:
            rows = conn.execute(query, params).fetchall()

            migrations = []
            for row in rows:
                items = conn.execute(
                    "SELECT * FROM migration_items WHERE migration_id = ? ORDER BY id",
                    (row["id"],),
                ).fetchall()
                migrations.append(self._row_to_migration(row, items))

            logger.debug(f"Listed {len(migrations)} migrations")
            return migrations

    def save(self, migration: Migration) -> None:
        """
        Save migration and all items (upsert).

        Args:
            migration: Migration to save
        """
        with self.db.connection() as conn:
            # Upsert migration
            conn.execute(
                """
                INSERT OR REPLACE INTO migrations
                (id, profile, created_at, started_at, completed_at, status,
                 standards_version, enable_rollback, parallel_workers,
                 total_files, successful_files, failed_files, skipped_files,
                 total_processing_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    migration.migration_id,
                    migration.profile,
                    migration.created_at.isoformat(),
                    (
                        migration.started_at.isoformat()
                        if migration.started_at
                        else None
                    ),
                    (
                        migration.completed_at.isoformat()
                        if migration.completed_at
                        else None
                    ),
                    migration.status.value,
                    migration.standards_version,
                    1 if migration.enable_rollback else 0,
                    migration.parallel_workers,
                    migration.total_files,
                    migration.successful_files,
                    migration.failed_files,
                    migration.skipped_files,
                    migration.total_processing_time,
                ),
            )

            # Upsert items
            for item in migration.items:
                self._save_item(conn, item)

            logger.info(
                f"Saved migration '{migration.migration_id}' with {len(migration.items)} items"
            )

    def _save_item(self, conn, item: MigrationItem) -> None:
        """Save a single migration item."""
        conn.execute(
            """
            INSERT OR REPLACE INTO migration_items
            (migration_id, file_path, status, backup_path, output_path,
             error, warnings, started_at, completed_at, processing_time,
             changes, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                item.migration_id,
                str(item.file_path),
                item.status.value,
                str(item.backup_path) if item.backup_path else None,
                str(item.output_path) if item.output_path else None,
                item.error,
                json.dumps(item.warnings) if item.warnings else None,
                item.started_at.isoformat() if item.started_at else None,
                item.completed_at.isoformat() if item.completed_at else None,
                item.processing_time,
                json.dumps(item.changes) if item.changes else None,
                json.dumps(item.metadata) if item.metadata else None,
            ),
        )

    def delete(self, migration_id: str) -> bool:
        """
        Delete migration and all items (cascade).

        Args:
            migration_id: Migration ID

        Returns:
            True if deleted, False if not found
        """
        with self.db.connection() as conn:
            result = conn.execute(
                "DELETE FROM migrations WHERE id = ?", (migration_id,)
            )

            if result.rowcount > 0:
                logger.info(f"Deleted migration '{migration_id}'")
                return True
            else:
                logger.debug(f"Migration '{migration_id}' not found for deletion")
                return False

    def exists(self, migration_id: str) -> bool:
        """
        Check if migration exists.

        Args:
            migration_id: Migration ID

        Returns:
            True if exists
        """
        with self.db.connection() as conn:
            result = conn.execute(
                "SELECT 1 FROM migrations WHERE id = ? LIMIT 1", (migration_id,)
            ).fetchone()
            return result is not None

    def update_status(self, migration_id: str, status: MigrationStatus) -> None:
        """
        Update migration status.

        Args:
            migration_id: Migration ID
            status: New status
        """
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE migrations SET status = ? WHERE id = ?",
                (status.value, migration_id),
            )
            logger.debug(f"Updated migration '{migration_id}' status to {status.value}")

    def update_item_status(
        self, migration_id: str, file_path: Path, status: MigrationStatus
    ) -> None:
        """
        Update single item status.

        Args:
            migration_id: Migration ID
            file_path: File path
            status: New status
        """
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE migration_items
                SET status = ?
                WHERE migration_id = ? AND file_path = ?
            """,
                (status.value, migration_id, str(file_path)),
            )

    def get_pending_files(self, migration_id: str) -> List[Path]:
        """
        Get list of pending files for a migration.

        Args:
            migration_id: Migration ID

        Returns:
            List of file paths with status=PENDING
        """
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT file_path FROM migration_items
                WHERE migration_id = ? AND status = ?
            """,
                (migration_id, MigrationStatus.PENDING.value),
            ).fetchall()

            return [Path(row["file_path"]) for row in rows]

    def get_stats(
        self, since: Optional[datetime] = None, profile: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics.

        Args:
            since: Filter by created_at >= since
            profile: Filter by profile

        Returns:
            Dictionary of statistics
        """
        query = """
            SELECT
                COUNT(*) as total_migrations,
                SUM(total_files) as total_files,
                SUM(successful_files) as successful_files,
                SUM(failed_files) as failed_files,
                SUM(skipped_files) as skipped_files,
                AVG(CAST(successful_files AS REAL) / NULLIF(total_files, 0) * 100) as avg_success_rate,
                SUM(total_processing_time) as total_processing_time
            FROM migrations
            WHERE status = ?
        """
        params = [MigrationStatus.COMPLETED.value]

        if since:
            query += " AND created_at >= ?"
            params.append(since.isoformat())

        if profile:
            query += " AND profile = ?"
            params.append(profile)

        with self.db.connection() as conn:
            row = conn.execute(query, params).fetchone()

            if row:
                stats = dict(row)
                logger.debug(f"Retrieved stats: {stats}")
                return stats
            else:
                return {}

    def _row_to_migration(self, row, item_rows: List) -> Migration:
        """Convert database rows to Migration object."""
        # Parse items
        items = [self._row_to_item(item_row) for item_row in item_rows]

        # Parse timestamps
        created_at = datetime.fromisoformat(row["created_at"])
        started_at = (
            datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
        )
        completed_at = (
            datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None
        )

        return Migration(
            migration_id=row["id"],
            profile=row["profile"],
            created_at=created_at,
            status=MigrationStatus(row["status"]),
            standards_version=row["standards_version"],
            enable_rollback=bool(row["enable_rollback"]),
            parallel_workers=row["parallel_workers"],
            items=items,
            total_files=row["total_files"],
            successful_files=row["successful_files"],
            failed_files=row["failed_files"],
            skipped_files=row["skipped_files"],
            started_at=started_at,
            completed_at=completed_at,
            total_processing_time=row["total_processing_time"],
        )

    def _row_to_item(self, row) -> MigrationItem:
        """Convert database row to MigrationItem object."""
        started_at = (
            datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
        )
        completed_at = (
            datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None
        )

        warnings = json.loads(row["warnings"]) if row["warnings"] else []
        changes = json.loads(row["changes"]) if row["changes"] else {}
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        return MigrationItem(
            file_path=Path(row["file_path"]),
            migration_id=row["migration_id"],
            status=MigrationStatus(row["status"]),
            output_path=Path(row["output_path"]) if row["output_path"] else None,
            backup_path=Path(row["backup_path"]) if row["backup_path"] else None,
            metadata=metadata,
            warnings=warnings,
            errors=[],  # Legacy field, not stored in DB
            error=row["error"],
            started_at=started_at,
            completed_at=completed_at,
            processing_time=row["processing_time"],
            changes=changes,
        )
