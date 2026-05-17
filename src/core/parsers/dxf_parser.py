"""
DXF file parser using ezdxf library.

Parses DXF files and extracts layers, entities, blocks, title blocks,
and attributes into a unified ParsedDrawing structure.
"""

from pathlib import Path
from typing import Dict, List, Any
import logging

try:
    import ezdxf
    from ezdxf import colors
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False

from .base_parser import BaseParser, ParsedDrawing
from ...utils.error_handling import ParsingError


class DXFParser(BaseParser):
    """Parse DXF files using ezdxf library."""

    def __init__(self):
        if not EZDXF_AVAILABLE:
            raise ImportError(
                "ezdxf library is required. Install with: pip install ezdxf"
            )
        self.logger = logging.getLogger(__name__)

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file."""
        return file_path.suffix.lower() == ".dxf"

    def parse(self, file_path: Path) -> ParsedDrawing:
        """Parse DXF file and extract all relevant data."""
        try:
            self.logger.info(f"Parsing DXF file: {file_path}")
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()

            # Extract layers
            layers = self._extract_layers(doc)

            # Extract entities by layer
            entities = self._extract_entities(msp)

            # Populate entities in each layer
            for entity in entities:
                layer_name = entity.get("layer")
                if layer_name in layers:
                    layers[layer_name]["entities"].append(entity)

            # Extract blocks
            blocks = self._extract_blocks(doc)

            # Extract title block
            title_block = self._extract_title_block(doc, msp)

            # Extract attributes
            attributes = self._extract_attributes(msp)

            # Extract metadata
            metadata = self._extract_metadata(doc)

            self.logger.info(
                f"Parsed {len(layers)} layers, {len(entities)} entities, "
                f"{len(blocks)} blocks"
            )

            return ParsedDrawing(
                file_path=file_path,
                file_type="DXF",
                layers=layers,
                entities=entities,
                blocks=blocks,
                title_block=title_block,
                attributes=attributes,
                metadata=metadata,
                raw_data=doc,  # Keep raw ezdxf document for backup
            )

        except Exception as e:
            self.logger.error(f"Failed to parse DXF file {file_path}: {str(e)}")
            raise ParsingError(f"Failed to parse DXF file {file_path}: {str(e)}")

    def _extract_layers(self, doc) -> Dict[str, Any]:
        """Extract layer information."""
        layers = {}
        try:
            for layer in doc.layers:
                layers[layer.dxf.name] = {
                    "name": layer.dxf.name,
                    "color": layer.dxf.color,
                    "line_type": layer.dxf.linetype,
                    "line_weight": layer.dxf.lineweight,
                    "plot": layer.dxf.plot,
                    "frozen": (layer.dxf.flags & 1) != 0,
                    "locked": (layer.dxf.flags & 4) != 0,
                    "entities": [],  # Will be populated later
                }
        except Exception as e:
            self.logger.warning(f"Error extracting layers: {str(e)}")

        return layers

    def _extract_entities(self, msp) -> List[Dict[str, Any]]:
        """Extract all entities from model space."""
        entities = []
        try:
            for entity in msp:
                entity_dict = {
                    "type": entity.dxftype(),
                    "layer": entity.dxf.layer,
                    "color": entity.dxf.color,
                    "data": entity,  # Keep raw entity
                }
                entities.append(entity_dict)
        except Exception as e:
            self.logger.warning(f"Error extracting entities: {str(e)}")

        return entities

    def _extract_blocks(self, doc) -> Dict[str, Any]:
        """Extract block definitions."""
        blocks = {}
        try:
            for block in doc.blocks:
                blocks[block.name] = {
                    "name": block.name,
                    "entities": [entity.dxftype() for entity in block],
                }
        except Exception as e:
            self.logger.warning(f"Error extracting blocks: {str(e)}")

        return blocks

    def _extract_title_block(self, doc, msp) -> Dict[str, Any]:
        """Extract title block data."""
        title_block = {}
        try:
            # Try to find title block by known patterns
            for entity in msp:
                if entity.dxftype() == "INSERT":
                    block_name = entity.dxf.name.upper()
                    if "TITLE" in block_name or "TB" in block_name:
                        # Extract attributes from block
                        for attrib in entity.attribs:
                            tag = attrib.dxf.tag
                            value = attrib.dxf.text
                            title_block[tag] = value

                        # Store block name for reference
                        title_block["_block_name"] = entity.dxf.name
                        title_block["_insertion_point"] = {
                            "x": entity.dxf.insert.x,
                            "y": entity.dxf.insert.y,
                        }

                        self.logger.info(f"Found title block: {entity.dxf.name}")
                        break  # Use first title block found

        except Exception as e:
            self.logger.warning(f"Error extracting title block: {str(e)}")

        return title_block

    def _extract_attributes(self, msp) -> Dict[str, str]:
        """Extract all attributes from drawing."""
        attributes = {}
        try:
            # Extract from INSERT entities with attributes
            for entity in msp:
                if entity.dxftype() == "INSERT":
                    for attrib in entity.attribs:
                        tag = attrib.dxf.tag
                        value = attrib.dxf.text
                        # Use compound key to avoid collisions
                        key = f"{entity.dxf.name}_{tag}"
                        attributes[key] = value

        except Exception as e:
            self.logger.warning(f"Error extracting attributes: {str(e)}")

        return attributes

    def _extract_metadata(self, doc) -> Dict[str, Any]:
        """Extract drawing metadata."""
        metadata = {}
        try:
            # Header variables
            metadata["acadver"] = doc.header.get("$ACADVER", "Unknown")
            metadata["dwgcodepage"] = doc.header.get("$DWGCODEPAGE", "Unknown")

            # Get current layer
            if hasattr(doc, "layers") and len(doc.layers) > 0:
                metadata["current_layer"] = "0"  # Default layer

            # Get units
            metadata["insunits"] = doc.header.get("$INSUNITS", 0)
            metadata["measurement"] = doc.header.get("$MEASUREMENT", 0)

            # Get limits
            metadata["limmin"] = doc.header.get("$LIMMIN", (0, 0))
            metadata["limmax"] = doc.header.get("$LIMMAX", (0, 0))

        except Exception as e:
            self.logger.warning(f"Error extracting metadata: {str(e)}")

        return metadata

    def save(self, parsed_drawing: ParsedDrawing, output_path: Path) -> None:
        """Save parsed drawing to DXF file."""
        if parsed_drawing.raw_data is None:
            raise ValueError("No raw data to save")

        try:
            self.logger.info(f"Saving DXF file: {output_path}")
            parsed_drawing.raw_data.saveas(output_path)
            self.logger.info(f"Saved DXF file: {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to save DXF file {output_path}: {str(e)}")
            raise ParsingError(f"Failed to save DXF file {output_path}: {str(e)}")

    def get_supported_versions(self) -> List[str]:
        """Return list of supported CAD versions."""
        return [
            "AC1009",  # R12
            "AC1012",  # R13
            "AC1014",  # R14
            "AC1015",  # R2000
            "AC1018",  # R2004
            "AC1021",  # R2007
            "AC1024",  # R2010
            "AC1027",  # R2013
            "AC1032",  # R2018
        ]
