"""
Migration data models.

Define data structures for tracking migration operations including
migration status, individual file migrations, and batch migrations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Any


class MigrationStatus(Enum):
    """Status of a migration operation."""

    PENDING = "pending"
    PARSED = "parsed"
    VALIDATED = "validated"
    TRANSFORMED = "transformed"
    COMPLETED = "completed"
    COMMITTED = "committed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationItem:
    """Single file migration record."""

    file_path: Path
    migration_id: str
    status: MigrationStatus = MigrationStatus.PENDING
    output_path: Optional[Path] = None
    backup_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Validation & transformation data
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    error: Optional[str] = None

    # Tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None

    # Statistics
    changes: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "file_path": str(self.file_path),
            "migration_id": self.migration_id,
            "status": self.status.value,
            "output_path": str(self.output_path) if self.output_path else None,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "metadata": self.metadata,
            "warnings": self.warnings,
            "errors": self.errors,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.processing_time,
            "changes": self.changes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationItem":
        """Deserialize from dictionary."""
        started_at = (
            datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        )
        completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        )

        return cls(
            file_path=Path(data["file_path"]),
            migration_id=data["migration_id"],
            status=MigrationStatus(data["status"]),
            output_path=Path(data["output_path"]) if data.get("output_path") else None,
            backup_path=Path(data["backup_path"]) if data.get("backup_path") else None,
            metadata=data.get("metadata", {}),
            warnings=data.get("warnings", []),
            errors=data.get("errors", []),
            error=data.get("error"),
            started_at=started_at,
            completed_at=completed_at,
            processing_time=data.get("processing_time"),
            changes=data.get("changes", {}),
        )


@dataclass
class Migration:
    """Batch migration record."""

    migration_id: str
    profile: str  # electrical_profile, mechanical_profile, etc.
    created_at: datetime = field(default_factory=datetime.now)
    status: MigrationStatus = MigrationStatus.PENDING

    # Configuration
    standards_version: str = "latest"
    enable_rollback: bool = True
    parallel_workers: int = 1

    # Items
    items: List[MigrationItem] = field(default_factory=list)

    # Statistics
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0

    # Summary
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_processing_time: Optional[float] = None

    def add_item(self, item: MigrationItem) -> None:
        """Add migration item and update statistics."""
        self.items.append(item)
        self.total_files += 1

        if item.status == MigrationStatus.COMMITTED:
            self.successful_files += 1
        elif item.status == MigrationStatus.FAILED:
            self.failed_files += 1

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_files == 0:
            return 0.0
        return (self.successful_files / self.total_files) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "migration_id": self.migration_id,
            "profile": self.profile,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "standards_version": self.standards_version,
            "enable_rollback": self.enable_rollback,
            "parallel_workers": self.parallel_workers,
            "items": [item.to_dict() for item in self.items],
            "total_files": self.total_files,
            "successful_files": self.successful_files,
            "failed_files": self.failed_files,
            "skipped_files": self.skipped_files,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_processing_time": self.total_processing_time,
            "success_rate": self.get_success_rate(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Migration":
        """Deserialize from dictionary."""
        items = [
            MigrationItem.from_dict(item_data) for item_data in data.get("items", [])
        ]

        started_at = (
            datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        )
        completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        )

        return cls(
            migration_id=data["migration_id"],
            profile=data["profile"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=MigrationStatus(data["status"]),
            standards_version=data.get("standards_version", "latest"),
            enable_rollback=data.get("enable_rollback", True),
            parallel_workers=data.get("parallel_workers", 1),
            items=items,
            total_files=data.get("total_files", 0),
            successful_files=data.get("successful_files", 0),
            failed_files=data.get("failed_files", 0),
            skipped_files=data.get("skipped_files", 0),
            started_at=started_at,
            completed_at=completed_at,
            total_processing_time=data.get("total_processing_time"),
        )
