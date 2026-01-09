"""
PDM custom property handler.

Maps between CAD drawing data and PDM custom properties (data card fields).
"""

from typing import Dict, Any
import logging

from ...core.parsers.base_parser import ParsedDrawing
from ...data.models.standards import PropertyMapping
from .base_client import PDMClient

logger = logging.getLogger(__name__)


class PropertyHandler:
    """Handles mapping between drawing data and PDM custom properties."""

    def __init__(self, client: PDMClient, property_mappings: Dict[str, PropertyMapping]):
        """
        Initialize property handler.

        Args:
            client: PDM client
            property_mappings: Dictionary of property_name -> PropertyMapping
        """
        self.client = client
        self.property_mappings = property_mappings

    def extract_properties(self, drawing: ParsedDrawing) -> Dict[str, str]:
        """
        Extract custom properties from drawing according to mappings.

        Args:
            drawing: Parsed drawing

        Returns:
            Dictionary of property_name -> value
        """
        properties = {}

        for prop_name, mapping in self.property_mappings.items():
            value = self._extract_value(drawing, mapping)

            if value is not None:
                properties[prop_name] = str(value)
            elif mapping.required:
                logger.warning(
                    f"Required property '{prop_name}' not found in drawing"
                )
                if mapping.default_value is not None:
                    properties[prop_name] = str(mapping.default_value)

        logger.debug(f"Extracted {len(properties)} properties from drawing")
        return properties

    def apply_properties(
        self, vault_path: str, properties: Dict[str, str]
    ) -> bool:
        """
        Apply custom properties to PDM file.

        Args:
            vault_path: Path in vault
            properties: Properties to set

        Returns:
            True if successful
        """
        try:
            # Validate properties
            validated = self._validate_properties(properties)

            # Set in PDM
            success = self.client.set_custom_properties(vault_path, validated)

            if success:
                logger.info(
                    f"Applied {len(validated)} properties to {vault_path}"
                )
            else:
                logger.error(f"Failed to apply properties to {vault_path}")

            return success

        except Exception as e:
            logger.error(f"Error applying properties: {e}")
            return False

    def sync_properties(
        self, drawing: ParsedDrawing, vault_path: str
    ) -> bool:
        """
        Extract properties from drawing and sync to PDM.

        Args:
            drawing: Parsed drawing
            vault_path: Path in vault

        Returns:
            True if successful
        """
        properties = self.extract_properties(drawing)
        return self.apply_properties(vault_path, properties)

    def _extract_value(
        self, drawing: ParsedDrawing, mapping: PropertyMapping
    ) -> Any:
        """
        Extract value from drawing according to mapping.

        Args:
            drawing: Parsed drawing
            mapping: Property mapping

        Returns:
            Extracted value or None
        """
        source = mapping.source

        if source == "title_block":
            # Extract from title block
            return drawing.title_block.get(mapping.source_key)

        elif source == "attribute":
            # Extract from attributes
            return drawing.attributes.get(mapping.source_key)

        elif source == "metadata":
            # Extract from metadata
            return drawing.metadata.get(mapping.source_key)

        elif source == "custom":
            # Custom extraction logic would go here
            logger.warning(f"Custom extraction not implemented for {mapping.property_name}")
            return None

        else:
            logger.warning(f"Unknown source type: {source}")
            return None

    def _validate_properties(self, properties: Dict[str, str]) -> Dict[str, str]:
        """
        Validate properties according to mappings.

        Args:
            properties: Properties to validate

        Returns:
            Validated properties
        """
        validated = {}

        for prop_name, value in properties.items():
            if prop_name not in self.property_mappings:
                # Allow unmapped properties
                validated[prop_name] = value
                continue

            mapping = self.property_mappings[prop_name]

            # Validate regex if provided
            if mapping.validation_regex:
                import re

                if not re.match(mapping.validation_regex, value):
                    logger.warning(
                        f"Property '{prop_name}' value '{value}' "
                        f"doesn't match regex: {mapping.validation_regex}"
                    )
                    if mapping.default_value is not None:
                        value = str(mapping.default_value)

            # Type conversion
            if mapping.data_type == "number":
                try:
                    value = str(float(value))
                except ValueError:
                    logger.warning(f"Property '{prop_name}' not a number: {value}")
                    continue
            elif mapping.data_type == "date":
                # Date validation could go here
                pass

            validated[prop_name] = value

        return validated
