"""
Abstract base repository interface.

Defines the contract that all repository implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract repository interface using the Repository pattern."""

    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        """
        Retrieve entity by ID.

        Args:
            id: Unique identifier

        Returns:
            Entity if found, None otherwise
        """
        pass

    @abstractmethod
    def list(self, **filters) -> List[T]:
        """
        List entities with optional filters.

        Args:
            **filters: Key-value pairs for filtering

        Returns:
            List of matching entities
        """
        pass

    @abstractmethod
    def save(self, entity: T) -> None:
        """
        Create or update entity.

        Args:
            entity: Entity to save
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, id: str) -> bool:
        """
        Check if entity exists.

        Args:
            id: Unique identifier

        Returns:
            True if exists, False otherwise
        """
        pass
