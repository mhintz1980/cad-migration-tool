"""
CLI module for CAD migration tool.

Command-line interface for all migration operations.
"""

from .main import cli
from .migrate import migrate_group
from .learn import learn_group
from .pdm import pdm_group
from .validate import validate_group

__all__ = [
    "cli",
    "migrate_group",
    "learn_group",
    "pdm_group",
    "validate_group",
]
