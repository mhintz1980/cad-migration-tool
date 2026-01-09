"""
YAML-based repository for standards configurations.

Stores StandardConfig objects as human-editable YAML files in config/standards/.
Supports versioning and filtering by drawing type.
"""

from pathlib import Path
from typing import List, Optional
import logging

from ..models.standards import StandardConfig
from .base_repository import Repository

logger = logging.getLogger(__name__)


class StandardsRepository(Repository[StandardConfig]):
    """Repository for standards configurations stored as YAML files."""

    def __init__(self, standards_dir: Path):
        """
        Initialize standards repository.

        Args:
            standards_dir: Directory containing standards YAML files
        """
        self.standards_dir = standards_dir
        self.standards_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized standards repository at {standards_dir}")

    def _get_file_path(self, name: str) -> Path:
        """Get file path for a standard by name."""
        return self.standards_dir / f"{name}.yaml"

    def get(self, name: str) -> Optional[StandardConfig]:
        """
        Load standard configuration by name.

        Args:
            name: Standard name (e.g., "electrical_v2")

        Returns:
            StandardConfig if found, None otherwise
        """
        file_path = self._get_file_path(name)

        if not file_path.exists():
            logger.debug(f"Standard '{name}' not found at {file_path}")
            return None

        try:
            config = StandardConfig.load_from_file(file_path)
            logger.debug(f"Loaded standard '{name}' from {file_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load standard '{name}': {e}")
            raise

    def list(
        self, drawing_type: Optional[str] = None, **filters
    ) -> List[StandardConfig]:
        """
        List all standards, optionally filtered by drawing type.

        Args:
            drawing_type: Filter by drawing type (electrical, mechanical, etc.)
            **filters: Additional filters (not currently used)

        Returns:
            List of StandardConfig objects
        """
        standards = []

        for file_path in sorted(self.standards_dir.glob("*.yaml")):
            try:
                config = StandardConfig.load_from_file(file_path)

                # Filter by drawing type if specified
                if drawing_type is None or config.drawing_type == drawing_type:
                    standards.append(config)

            except Exception as e:
                logger.warning(f"Failed to load standard from {file_path}: {e}")
                continue

        logger.debug(
            f"Listed {len(standards)} standards"
            + (f" for type '{drawing_type}'" if drawing_type else "")
        )
        return standards

    def save(self, config: StandardConfig) -> None:
        """
        Save standard configuration to YAML file.

        Args:
            config: StandardConfig to save
        """
        file_path = self._get_file_path(config.name)

        try:
            config.save_to_file(file_path)
            logger.info(f"Saved standard '{config.name}' to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save standard '{config.name}': {e}")
            raise

    def delete(self, name: str) -> bool:
        """
        Delete standard configuration file.

        Args:
            name: Standard name

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_file_path(name)

        if not file_path.exists():
            logger.debug(f"Standard '{name}' not found for deletion")
            return False

        try:
            file_path.unlink()
            logger.info(f"Deleted standard '{name}' at {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete standard '{name}': {e}")
            raise

    def exists(self, name: str) -> bool:
        """
        Check if standard exists.

        Args:
            name: Standard name

        Returns:
            True if exists
        """
        return self._get_file_path(name).exists()

    def get_latest(self, drawing_type: str = "general") -> Optional[StandardConfig]:
        """
        Get the latest version of standards for a drawing type.

        Compares version strings using semantic versioning.

        Args:
            drawing_type: Drawing type to filter by

        Returns:
            Latest StandardConfig or None if no standards found
        """
        candidates = self.list(drawing_type=drawing_type)

        if not candidates:
            logger.warning(f"No standards found for type '{drawing_type}'")
            return None

        # Sort by version (semantic versioning)
        try:
            from packaging.version import Version

            candidates.sort(key=lambda c: Version(c.version), reverse=True)
            latest = candidates[0]
            logger.info(
                f"Latest standard for '{drawing_type}': {latest.name} v{latest.version}"
            )
            return latest
        except ImportError:
            # Fallback to string comparison if packaging not available
            logger.warning("packaging library not available, using string comparison")
            candidates.sort(key=lambda c: c.version, reverse=True)
            return candidates[0]

    def list_versions(self, drawing_type: Optional[str] = None) -> List[str]:
        """
        List all available versions for a drawing type.

        Args:
            drawing_type: Drawing type to filter by

        Returns:
            List of version strings sorted newest to oldest
        """
        standards = self.list(drawing_type=drawing_type)
        versions = [s.version for s in standards]

        try:
            from packaging.version import Version

            versions.sort(key=Version, reverse=True)
        except ImportError:
            versions.sort(reverse=True)

        return versions

    def get_by_version(
        self, version: str, drawing_type: Optional[str] = None
    ) -> Optional[StandardConfig]:
        """
        Get standard by exact version match.

        Args:
            version: Version string
            drawing_type: Optional drawing type filter

        Returns:
            StandardConfig if found
        """
        standards = self.list(drawing_type=drawing_type)

        for standard in standards:
            if standard.version == version:
                return standard

        logger.debug(f"No standard found with version '{version}'")
        return None
