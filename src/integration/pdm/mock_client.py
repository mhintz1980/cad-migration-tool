"""
Mock PDM client for development and testing.

File-system based simulation of PDM vault operations.
Stores files, versions, and metadata locally.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

from .base_client import PDMClient
from .models import (
    PDMFile,
    CheckInResult,
    CheckOutResult,
    PDMFileState,
    PDMError,
    PDMFileNotFoundError,
    PDMFileLockedError,
    VaultConfig,
)

logger = logging.getLogger(__name__)


class MockPDMClient(PDMClient):
    """
    File-system based mock PDM client.

    Directory structure:
    .mock_vault/
    ├── files/              # Current files
    ├── metadata/           # JSON metadata per file
    ├── versions/           # Version history
    └── checkouts.json      # Current checkout state
    """

    def __init__(self, config: VaultConfig):
        """
        Initialize mock client.

        Args:
            config: Vault configuration (must include vault_root)
        """
        super().__init__(config)

        if not config.vault_root:
            raise ValueError("MockPDMClient requires vault_root in config")

        self.vault_root = Path(config.vault_root)
        self.files_dir = self.vault_root / "files"
        self.metadata_dir = self.vault_root / "metadata"
        self.versions_dir = self.vault_root / "versions"
        self.checkouts_file = self.vault_root / "checkouts.json"

    def connect(self) -> bool:
        """Initialize mock vault structure."""
        try:
            self.files_dir.mkdir(parents=True, exist_ok=True)
            self.metadata_dir.mkdir(parents=True, exist_ok=True)
            self.versions_dir.mkdir(parents=True, exist_ok=True)

            if not self.checkouts_file.exists():
                self.checkouts_file.write_text("{}")

            self._connected = True
            logger.info(f"Connected to mock vault: {self.vault_root}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize mock vault: {e}")
            return False

    def disconnect(self):
        """Disconnect (no-op for mock)."""
        self._connected = False
        logger.info("Disconnected from mock vault")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def get_file_state(self, vault_path: str) -> PDMFile:
        """Get file state from mock vault."""
        self.ensure_connected()

        file_path = self.files_dir / vault_path
        metadata_path = self.metadata_dir / f"{vault_path}.json"

        if not file_path.exists():
            return PDMFile(
                path=file_path,
                vault_path=vault_path,
                state=PDMFileState.NOT_IN_VAULT,
                version=0,
            )

        # Load metadata
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())

        # Load checkouts
        checkouts = json.loads(self.checkouts_file.read_text())

        # Determine state
        if vault_path in checkouts:
            state = PDMFileState.CHECKED_OUT
            checked_out_by = checkouts[vault_path]["user"]
        else:
            state = PDMFileState.CHECKED_IN
            checked_out_by = None

        return PDMFile(
            path=file_path,
            vault_path=vault_path,
            state=state,
            version=metadata.get("version", 1),
            checked_out_by=checked_out_by,
            custom_properties=metadata.get("properties", {}),
            last_modified=datetime.fromisoformat(metadata["last_modified"])
            if "last_modified" in metadata
            else None,
            last_modified_by=metadata.get("last_modified_by"),
        )

    def checkout(self, vault_path: str, local_path: Path) -> CheckOutResult:
        """Simulate checkout by copying file."""
        self.ensure_connected()

        file_state = self.get_file_state(vault_path)

        if file_state.state == PDMFileState.NOT_IN_VAULT:
            return CheckOutResult(
                success=False, error=f"File not in vault: {vault_path}"
            )

        if file_state.state == PDMFileState.CHECKED_OUT:
            return CheckOutResult(
                success=False,
                error=f"File already checked out by: {file_state.checked_out_by}",
            )

        try:
            # Copy to local
            local_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.files_dir / vault_path, local_path)

            # Record checkout
            checkouts = json.loads(self.checkouts_file.read_text())
            checkouts[vault_path] = {
                "user": "mock_user",
                "local_path": str(local_path),
                "timestamp": datetime.now().isoformat(),
            }
            self.checkouts_file.write_text(json.dumps(checkouts, indent=2))

            logger.info(f"Checked out: {vault_path} -> {local_path}")
            return CheckOutResult(success=True, local_path=local_path)

        except Exception as e:
            logger.error(f"Checkout failed: {e}")
            return CheckOutResult(success=False, error=str(e))

    def checkin(
        self, local_path: Path, vault_path: str, comment: str = ""
    ) -> CheckInResult:
        """Simulate check-in with version increment."""
        self.ensure_connected()

        if not local_path.exists():
            return CheckInResult(
                success=False, new_version=0, error=f"Local file not found: {local_path}"
            )

        metadata_path = self.metadata_dir / f"{vault_path}.json"
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())

        # Increment version
        old_version = metadata.get("version", 0)
        new_version = old_version + 1

        try:
            # Archive old version
            if old_version > 0:
                version_dir = self.versions_dir / vault_path
                version_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(
                    self.files_dir / vault_path, version_dir / f"v{old_version}"
                )

            # Copy new file
            vault_file = self.files_dir / vault_path
            vault_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, vault_file)

            # Update metadata
            metadata["version"] = new_version
            metadata["last_modified"] = datetime.now().isoformat()
            metadata["last_modified_by"] = "mock_user"
            metadata["comment"] = comment

            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps(metadata, indent=2))

            # Remove from checkouts
            checkouts = json.loads(self.checkouts_file.read_text())
            checkouts.pop(vault_path, None)
            self.checkouts_file.write_text(json.dumps(checkouts, indent=2))

            logger.info(f"Checked in: {local_path} -> {vault_path} (v{new_version})")
            return CheckInResult(
                success=True, new_version=new_version, vault_path=vault_path
            )

        except Exception as e:
            logger.error(f"Check-in failed: {e}")
            return CheckInResult(success=False, new_version=old_version, error=str(e))

    def add_file(
        self, local_path: Path, vault_folder: str, comment: str = ""
    ) -> CheckInResult:
        """Add new file to vault."""
        vault_path = f"{vault_folder}/{local_path.name}".replace("//", "/")
        return self.checkin(local_path, vault_path, comment)

    def get_custom_properties(self, vault_path: str) -> Dict[str, str]:
        """Get custom properties from metadata."""
        self.ensure_connected()

        metadata_path = self.metadata_dir / f"{vault_path}.json"
        if not metadata_path.exists():
            return {}

        metadata = json.loads(metadata_path.read_text())
        return metadata.get("properties", {})

    def set_custom_properties(
        self, vault_path: str, properties: Dict[str, str]
    ) -> bool:
        """Set custom properties in metadata."""
        self.ensure_connected()

        metadata_path = self.metadata_dir / f"{vault_path}.json"
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())

        metadata["properties"] = properties
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2))

        logger.debug(f"Set properties on {vault_path}: {properties}")
        return True

    def undo_checkout(self, vault_path: str) -> bool:
        """Undo checkout, discarding changes."""
        self.ensure_connected()

        checkouts = json.loads(self.checkouts_file.read_text())
        if vault_path in checkouts:
            checkouts.pop(vault_path)
            self.checkouts_file.write_text(json.dumps(checkouts, indent=2))
            logger.info(f"Undid checkout: {vault_path}")
            return True

        return False

    def list_folder(self, vault_folder: str) -> List[str]:
        """List files in vault folder."""
        self.ensure_connected()

        folder_path = self.files_dir / vault_folder
        if not folder_path.exists():
            return []

        files = []
        for item in folder_path.iterdir():
            if item.is_file():
                # Return path relative to vault root
                rel_path = item.relative_to(self.files_dir)
                files.append(str(rel_path))

        return files
