#!/usr/bin/env python3
"""
CAD Migration CLI entry script.

This script serves as the main entry point for the CAD Migration automation tool.
It delegates to the CLI module for all command processing.
"""

import sys
from pathlib import Path

# Add project root to Python path to enable absolute imports from src
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.cli.main import cli

if __name__ == "__main__":
    cli()
