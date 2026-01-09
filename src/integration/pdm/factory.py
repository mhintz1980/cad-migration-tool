"""
PDM client factory.

Automatically selects appropriate PDM client based on platform and configuration.
"""

import platform
from pathlib import Path
import logging

from .base_client import PDMClient
from .mock_client import MockPDMClient
from .com_client import COMPDMClient
from .models import VaultConfig, PDMError

logger = logging.getLogger(__name__)


class PDMClientFactory:
    """Factory for creating PDM clients."""

    @staticmethod
    def create_client(
        vault_name: str,
        mock: bool = False,
        vault_root: Path | None = None,
        server_name: str | None = None,
        database_name: str | None = None,
        user_name: str | None = None,
    ) -> PDMClient:
        """
        Create appropriate PDM client.

        Args:
            vault_name: Vault name
            mock: Force mock client (for development/testing)
            vault_root: Root directory for mock vault
            server_name: PDM server name (for COM client)
            database_name: PDM database name (for COM client)
            user_name: PDM user name (for COM client)

        Returns:
            PDM client instance
        """
        config = VaultConfig(
            vault_name=vault_name,
            server_name=server_name,
            database_name=database_name,
            user_name=user_name,
            vault_root=vault_root,
        )

        # Use mock client if explicitly requested
        if mock:
            logger.info("Creating MockPDMClient (explicitly requested)")
            if not vault_root:
                vault_root = Path(".mock_vault")
            config.vault_root = vault_root
            return MockPDMClient(config)

        # Auto-detect based on platform
        system = platform.system()

        if system == "Windows":
            # Try COM client on Windows
            logger.info("Creating COMPDMClient (Windows detected)")
            return COMPDMClient(config)
        else:
            # Use mock client on Linux/Mac
            logger.info(f"Creating MockPDMClient (non-Windows: {system})")
            if not vault_root:
                vault_root = Path(".mock_vault")
            config.vault_root = vault_root
            return MockPDMClient(config)

    @staticmethod
    def create_mock_client(vault_root: Path | None = None) -> MockPDMClient:
        """
        Create mock PDM client for testing.

        Args:
            vault_root: Root directory for mock vault

        Returns:
            MockPDMClient instance
        """
        if not vault_root:
            vault_root = Path(".mock_vault")

        config = VaultConfig(vault_name="mock_vault", vault_root=vault_root)
        return MockPDMClient(config)

    @staticmethod
    def auto_detect() -> str:
        """
        Auto-detect which client would be created.

        Returns:
            "mock" or "com"
        """
        system = platform.system()
        if system == "Windows":
            return "com"
        return "mock"
