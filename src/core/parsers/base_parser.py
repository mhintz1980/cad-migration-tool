"""
Abstract base class for CAD file parsers.

Defines the interface that all CAD file parsers must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ParsedDrawing:
    """Unified representation of parsed CAD drawing."""

    file_path: Path
    file_type: str  # 'DXF' or 'DWG'

    # Content
    layers: Dict[str, Any]  # layer_name -> {color, line_type, entities}
    entities: List[Any]  # All drawing entities
    blocks: Dict[str, Any]  # block definitions
    title_block: Dict[str, Any]
    attributes: Dict[str, str]

    # Metadata
    metadata: Dict[str, Any]

    # Raw data for backup
    raw_data: Any


class BaseParser(ABC):
    """Abstract base class for CAD file parsers."""

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDrawing:
        """Parse CAD file and return unified structure."""
        pass

    @abstractmethod
    def save(self, parsed_drawing: ParsedDrawing, output_path: Path) -> None:
        """Save parsed drawing to file."""
        pass

    @abstractmethod
    def get_supported_versions(self) -> List[str]:
        """Return list of supported CAD versions."""
        pass
