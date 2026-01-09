"""
Batch orchestration for parallel CAD file processing.

Coordinates parallel processing of multiple files using ProcessPoolExecutor,
with crash recovery, rollback support, and progress tracking.
"""

from .batch_processor import BatchProcessor, BatchConfig
from .state_machine import StateManager
from .rollback import RollbackManager
from .progress import ProgressReporter

__all__ = [
    "BatchProcessor",
    "BatchConfig",
    "StateManager",
    "RollbackManager",
    "ProgressReporter",
]
