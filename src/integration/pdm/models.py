"""
PDM (Product Data Management) data models.

Defines data structures for PDM vault operations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
from enum import Enum
from datetime import datetime


class PDMFileState(Enum):
    """File state in PDM vault."""

    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CHECKED_OUT_BY_OTHER = "checked_out_by_other"
    NOT_IN_VAULT = "not_in_vault"


@dataclass
class PDMFile:
    """Represents a file in the PDM vault."""

    path: Path
    vault_path: str  # Path within vault
    state: PDMFileState
    version: int
    checked_out_by: Optional[str] = None
    custom_properties: Dict[str, str] = field(default_factory=dict)
    last_modified: Optional[datetime] = None
    last_modified_by: Optional[str] = None


@dataclass
class CheckInResult:
    """Result of a check-in operation."""

    success: bool
    new_version: int
    error: Optional[str] = None
    vault_path: Optional[str] = None


@dataclass
class CheckOutResult:
    """Result of a check-out operation."""

    success: bool
    local_path: Optional[Path] = None
    error: Optional[str] = None


@dataclass
class VaultConfig:
    """PDM vault configuration."""

    vault_name: str
    server_name: Optional[str] = None
    database_name: Optional[str] = None
    user_name: Optional[str] = None
    # For mock client
    vault_root: Optional[Path] = None


class PDMError(Exception):
    """Base exception for PDM operations."""

    pass


class PDMConnectionError(PDMError):
    """Error connecting to PDM vault."""

    pass


class PDMFileNotFoundError(PDMError):
    """File not found in vault."""

    pass


class PDMFileLockedError(PDMError):
    """File is locked (checked out by another user)."""

    pass
