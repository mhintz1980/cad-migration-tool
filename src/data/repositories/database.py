"""
SQLite database connection manager.

Provides connection pooling, schema management, and WAL mode for
crash-safe concurrent operations.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)


class Database:
    """SQLite database connection manager with WAL mode."""

    def __init__(self, db_path: Path, timeout: float = 30.0):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
            timeout: Lock timeout in seconds (default: 30.0)
        """
        self.db_path = db_path
        self.timeout = timeout

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize with WAL mode for better concurrency
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database with WAL mode and optimal settings."""
        with self.connection() as conn:
            # Enable WAL mode for better concurrency and crash safety
            conn.execute("PRAGMA journal_mode=WAL")

            # Optimize for performance
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster than FULL, still safe with WAL
            conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O

            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")

            logger.info(f"Initialized database at {self.db_path} with WAL mode")

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections.

        Automatically commits on success, rolls back on error.

        Yields:
            SQLite connection

        Example:
            with db.connection() as conn:
                conn.execute("INSERT INTO ...")
        """
        conn = sqlite3.connect(
            str(self.db_path), timeout=self.timeout, check_same_thread=False
        )

        # Use Row factory for dict-like access
        conn.row_factory = sqlite3.Row

        # Enable foreign keys (must be done per connection)
        conn.execute("PRAGMA foreign_keys=ON")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_script(self, sql_script: str) -> None:
        """
        Execute SQL script (multiple statements).

        Args:
            sql_script: SQL statements separated by semicolons
        """
        with self.connection() as conn:
            conn.executescript(sql_script)

    def checkpoint(self, mode: str = "TRUNCATE") -> None:
        """
        Force WAL checkpoint for durability.

        Args:
            mode: Checkpoint mode - PASSIVE, FULL, RESTART, or TRUNCATE
                  TRUNCATE (default) ensures WAL is emptied
        """
        with self.connection() as conn:
            conn.execute(f"PRAGMA wal_checkpoint({mode})")
            logger.debug(f"WAL checkpoint completed ({mode})")

    def vacuum(self) -> None:
        """
        Vacuum database to reclaim space and optimize.

        Note: This is a blocking operation.
        """
        with self.connection() as conn:
            conn.execute("VACUUM")
            logger.info("Database vacuum completed")

    def get_schema_version(self) -> Optional[int]:
        """
        Get current schema version from user_version pragma.

        Returns:
            Schema version number or None if not set
        """
        with self.connection() as conn:
            result = conn.execute("PRAGMA user_version").fetchone()
            return result[0] if result else None

    def set_schema_version(self, version: int) -> None:
        """
        Set schema version.

        Args:
            version: Version number
        """
        with self.connection() as conn:
            conn.execute(f"PRAGMA user_version = {version}")
            logger.info(f"Schema version set to {version}")

    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists.

        Args:
            table_name: Name of table

        Returns:
            True if table exists
        """
        with self.connection() as conn:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
            return result is not None

    def get_table_names(self) -> list[str]:
        """
        Get list of all table names.

        Returns:
            List of table names
        """
        with self.connection() as conn:
            results = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            return [row[0] for row in results]

    def get_row_count(self, table_name: str) -> int:
        """
        Get number of rows in table.

        Args:
            table_name: Name of table

        Returns:
            Row count
        """
        with self.connection() as conn:
            result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0

    def close(self) -> None:
        """
        Close database connections and perform final checkpoint.

        Call this before application shutdown.
        """
        try:
            self.checkpoint("TRUNCATE")
            logger.info(f"Database {self.db_path} closed cleanly")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
