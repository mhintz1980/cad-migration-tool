"""
Part card data models.

Define data structures for extracting and managing part card data
from CAD drawings for PDM integration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class PartType(Enum):
    """Type of part in electrical distribution equipment."""

    ENCLOSURE = "enclosure"
    BUSBAR = "busbar"
    TERMINAL = "terminal"
    CONTACTOR = "contactor"
    RELAY = "relay"
    TRANSFORMER = "transformer"
    BREAKER = "breaker"
    FUSE = "fuse"
    SWITCH = "switch"
    INDICATOR = "indicator"
    WIRE = "wire"
    CUSTOM = "custom"


@dataclass
class PartCardData:
    """Extracted part card data from drawing."""

    # Basic identification
    drawing_number: str
    revision: str
    title: str

    # Part information
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    part_type: Optional[PartType] = None
    description: Optional[str] = None

    # Material/Specifications
    material: Optional[str] = None
    gauge: Optional[str] = None  # For sheet metal
    finish: Optional[str] = None

    # Dimensions
    dimensions: Dict[str, float] = field(default_factory=dict)

    # Quantities
    quantity: int = 1
    unit_of_measure: str = "each"

    # Custom properties
    custom_properties: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    source_attributes: Dict[str, str] = field(default_factory=dict)

    def to_pdm_properties(self, mappings: Dict[str, Any]) -> Dict[str, Any]:
        """Convert to PDM custom properties based on mappings."""
        properties = {}

        for prop_name, mapping in mappings.items():
            value = self._get_value(mapping)
            if value is not None:
                properties[prop_name] = value

        return properties

    def _get_value(self, mapping: Dict[str, Any]) -> Any:
        """Extract value based on mapping configuration."""
        source = mapping.get("source")
        source_key = mapping.get("source_key")

        if source == "title_block":
            return getattr(self, source_key, None)
        elif source == "attribute":
            return self.source_attributes.get(source_key)
        elif source == "custom":
            return self.custom_properties.get(source_key)

        return None

    def validate_required_fields(self, required_fields: List[str]) -> List[str]:
        """Validate that all required fields are present."""
        missing = []
        for field_name in required_fields:
            if not hasattr(self, field_name) or getattr(self, field_name) is None:
                missing.append(field_name)
        return missing

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "drawing_number": self.drawing_number,
            "revision": self.revision,
            "title": self.title,
            "part_number": self.part_number,
            "part_name": self.part_name,
            "part_type": self.part_type.value if self.part_type else None,
            "description": self.description,
            "material": self.material,
            "gauge": self.gauge,
            "finish": self.finish,
            "dimensions": self.dimensions,
            "quantity": self.quantity,
            "unit_of_measure": self.unit_of_measure,
            "custom_properties": self.custom_properties,
            "source_attributes": self.source_attributes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PartCardData":
        """Deserialize from dictionary."""
        part_type = data.get("part_type")
        part_type_enum = PartType(part_type) if part_type else None

        return cls(
            drawing_number=data["drawing_number"],
            revision=data["revision"],
            title=data["title"],
            part_number=data.get("part_number"),
            part_name=data.get("part_name"),
            part_type=part_type_enum,
            description=data.get("description"),
            material=data.get("material"),
            gauge=data.get("gauge"),
            finish=data.get("finish"),
            dimensions=data.get("dimensions", {}),
            quantity=data.get("quantity", 1),
            unit_of_measure=data.get("unit_of_measure", "each"),
            custom_properties=data.get("custom_properties", {}),
            source_attributes=data.get("source_attributes", {}),
        )
