"""
PDM (Product Data Management) integration.

Provides interface abstraction for SolidWorks PDM vault operations
with mock implementation for cross-platform development.
"""

from .models import (
    PDMFile,
    PDMFileState,
    CheckInResult,
    CheckOutResult,
    VaultConfig,
    PDMError,
    PDMConnectionError,
    PDMFileNotFoundError,
    PDMFileLockedError,
)
from .base_client import PDMClient
from .mock_client import MockPDMClient
from .com_client import COMPDMClient
from .property_handler import PropertyHandler
from .factory import PDMClientFactory

__all__ = [
    "PDMFile",
    "PDMFileState",
    "CheckInResult",
    "CheckOutResult",
    "VaultConfig",
    "PDMError",
    "PDMConnectionError",
    "PDMFileNotFoundError",
    "PDMFileLockedError",
    "PDMClient",
    "MockPDMClient",
    "COMPDMClient",
    "PropertyHandler",
    "PDMClientFactory",
]
