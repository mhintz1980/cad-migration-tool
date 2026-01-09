"""
Abstract base class for PDM clients.

Defines the interface that all PDM client implementations must follow.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .models import (
    PDMFile,
    CheckInResult,
    CheckOutResult,
    PDMFileState,
    VaultConfig,
)

logger = logging.getLogger(__name__)


class PDMClient(ABC):
    """Abstract interface for PDM operations."""

    def __init__(self, config: VaultConfig):
        """
        Initialize PDM client.

        Args:
            config: Vault configuration
        """
        self.config = config
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to PDM vault.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from vault."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if connected to vault.

        Returns:
            True if connected
        """
        pass

    @abstractmethod
    def get_file_state(self, vault_path: str) -> PDMFile:
        """
        Get current state of a file in the vault.

        Args:
            vault_path: Path within vault

        Returns:
            PDMFile with current state
        """
        pass

    @abstractmethod
    def checkout(self, vault_path: str, local_path: Path) -> CheckOutResult:
        """
        Check out file for editing.

        Args:
            vault_path: Path within vault
            local_path: Local path to copy file to

        Returns:
            CheckOutResult
        """
        pass

    @abstractmethod
    def checkin(
        self, local_path: Path, vault_path: str, comment: str = ""
    ) -> CheckInResult:
        """
        Check in modified file.

        Args:
            local_path: Local file path
            vault_path: Path within vault
            comment: Check-in comment

        Returns:
            CheckInResult
        """
        pass

    @abstractmethod
    def add_file(
        self, local_path: Path, vault_folder: str, comment: str = ""
    ) -> CheckInResult:
        """
        Add new file to vault.

        Args:
            local_path: Local file path
            vault_folder: Vault folder to add to
            comment: Check-in comment

        Returns:
            CheckInResult
        """
        pass

    @abstractmethod
    def get_custom_properties(self, vault_path: str) -> Dict[str, str]:
        """
        Get custom properties (data card values).

        Args:
            vault_path: Path within vault

        Returns:
            Dictionary of property_name -> value
        """
        pass

    @abstractmethod
    def set_custom_properties(
        self, vault_path: str, properties: Dict[str, str]
    ) -> bool:
        """
        Set custom properties.

        Args:
            vault_path: Path within vault
            properties: Properties to set

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def undo_checkout(self, vault_path: str) -> bool:
        """
        Undo checkout, discarding changes.

        Args:
            vault_path: Path within vault

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def list_folder(self, vault_folder: str) -> List[str]:
        """
        List files in vault folder.

        Args:
            vault_folder: Vault folder path

        Returns:
            List of file paths in folder
        """
        pass

    def ensure_connected(self):
        """
        Ensure client is connected, raise if not.

        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to PDM vault")
