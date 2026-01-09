"""
Standards data models.

Define data structures for CAD standards including layers, dimensions,
title blocks, and validation rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml


@dataclass
class LayerStandard:
    """Standard for a single layer."""

    name: str
    color: int
    line_type: str = "CONTINUOUS"
    line_weight: int = 13  # In 1/100 mm
    plot: bool = True
    description: str = ""

    # Optional layer grouping
    group: Optional[str] = None  # e.g., "DIMENSIONS", "NOTES"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "color": self.color,
            "line_type": self.line_type,
            "line_weight": self.line_weight,
            "plot": self.plot,
            "description": self.description,
            "group": self.group,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayerStandard":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            color=data["color"],
            line_type=data.get("line_type", "CONTINUOUS"),
            line_weight=data.get("line_weight", 13),
            plot=data.get("plot", True),
            description=data.get("description", ""),
            group=data.get("group"),
        )


@dataclass
class DimensionStandard:
    """Standard for dimensioning."""

    arrow_size: float
    text_height: float
    text_offset: float
    extension_line_offset: float
    precision: int = 2
    units: str = "mm"
    layer: str = "DIMENSIONS"

    # Dimension style
    arrow_style: str = "CLOSED"
    text_alignment: str = "ABOVE"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "arrow_size": self.arrow_size,
            "text_height": self.text_height,
            "text_offset": self.text_offset,
            "extension_line_offset": self.extension_line_offset,
            "precision": self.precision,
            "units": self.units,
            "layer": self.layer,
            "arrow_style": self.arrow_style,
            "text_alignment": self.text_alignment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DimensionStandard":
        """Create from dictionary."""
        return cls(
            arrow_size=data["arrow_size"],
            text_height=data["text_height"],
            text_offset=data["text_offset"],
            extension_line_offset=data["extension_line_offset"],
            precision=data.get("precision", 2),
            units=data.get("units", "mm"),
            layer=data.get("layer", "DIMENSIONS"),
            arrow_style=data.get("arrow_style", "CLOSED"),
            text_alignment=data.get("text_alignment", "ABOVE"),
        )


@dataclass
class TitleBlockStandard:
    """Standard for title block layout."""

    # Required fields
    required_fields: List[str] = field(
        default_factory=lambda: [
            "drawing_number",
            "revision",
            "title",
            "date",
            "author",
            "sheet_number",
        ]
    )

    # Format requirements
    date_format: str = "%Y-%m-%d"
    revision_format: str = r"^[A-Z]\d{3}$"  # e.g., A001

    # Positioning (if applicable)
    position: Dict[str, Any] = field(default_factory=dict)

    # Attributes mapping
    attribute_mapping: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "required_fields": self.required_fields,
            "date_format": self.date_format,
            "revision_format": self.revision_format,
            "position": self.position,
            "attribute_mapping": self.attribute_mapping,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TitleBlockStandard":
        """Create from dictionary."""
        return cls(
            required_fields=data.get("required_fields", cls.required_fields),
            date_format=data.get("date_format", "%Y-%m-%d"),
            revision_format=data.get("revision_format", r"^[A-Z]\d{3}$"),
            position=data.get("position", {}),
            attribute_mapping=data.get("attribute_mapping", {}),
        )


@dataclass
class PropertyMapping:
    """Mapping from drawing data to PDM custom property."""

    property_name: str  # PDM property name
    source: str  # Where to extract from: "title_block", "attribute", "custom"
    source_key: str  # Key in source (e.g., attribute tag)
    data_type: str = "string"  # string, number, date, list
    required: bool = False
    default_value: Any = None
    validation_regex: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "property_name": self.property_name,
            "source": self.source,
            "source_key": self.source_key,
            "data_type": self.data_type,
            "required": self.required,
            "default_value": self.default_value,
            "validation_regex": self.validation_regex,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PropertyMapping":
        """Create from dictionary."""
        return cls(
            property_name=data["property_name"],
            source=data["source"],
            source_key=data["source_key"],
            data_type=data.get("data_type", "string"),
            required=data.get("required", False),
            default_value=data.get("default_value"),
            validation_regex=data.get("validation_regex"),
        )


@dataclass
class ValidationRule:
    """Single validation rule."""

    name: str
    description: str
    severity: str = "error"  # error, warning
    rule_type: str = "custom"  # layer_exists, entity_count, custom

    # Rule-specific configuration
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "rule_type": self.rule_type,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationRule":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            severity=data.get("severity", "error"),
            rule_type=data.get("rule_type", "custom"),
            config=data.get("config", {}),
        )


@dataclass
class StandardConfig:
    """Complete standards configuration."""

    name: str
    version: str
    description: str = ""

    # Layer standards
    layer_standards: Dict[str, LayerStandard] = field(default_factory=dict)
    layer_mapping: Dict[str, str] = field(default_factory=dict)  # old -> new

    # Entity layer rules (which entities go on which layers)
    entity_layer_rules: Dict[str, str] = field(default_factory=dict)

    # Dimension standards
    dimension_standards: Dict[str, DimensionStandard] = field(default_factory=dict)

    # Title block standards
    title_block_standard: Optional[TitleBlockStandard] = None

    # PDM property mappings
    property_mappings: Dict[str, PropertyMapping] = field(default_factory=dict)

    # Validation rules
    validation_rules: List[ValidationRule] = field(default_factory=list)

    # Drawing type (electrical, mechanical)
    drawing_type: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "layer_standards": {
                name: std.to_dict() for name, std in self.layer_standards.items()
            },
            "layer_mapping": self.layer_mapping,
            "entity_layer_rules": self.entity_layer_rules,
            "dimension_standards": {
                name: std.to_dict() for name, std in self.dimension_standards.items()
            },
            "title_block_standard": (
                self.title_block_standard.to_dict()
                if self.title_block_standard
                else None
            ),
            "property_mappings": {
                name: mapping.to_dict() for name, mapping in self.property_mappings.items()
            },
            "validation_rules": [rule.to_dict() for rule in self.validation_rules],
            "drawing_type": self.drawing_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandardConfig":
        """Deserialize from dictionary."""
        # Parse layer standards
        layer_standards = {}
        for name, std_data in data.get("layer_standards", {}).items():
            layer_standards[name] = LayerStandard.from_dict(std_data)

        # Parse dimension standards
        dimension_standards = {}
        for name, std_data in data.get("dimension_standards", {}).items():
            dimension_standards[name] = DimensionStandard.from_dict(std_data)

        # Parse title block standard
        title_block_data = data.get("title_block_standard")
        title_block_standard = (
            TitleBlockStandard.from_dict(title_block_data) if title_block_data else None
        )

        # Parse property mappings
        property_mappings = {}
        for name, mapping_data in data.get("property_mappings", {}).items():
            property_mappings[name] = PropertyMapping.from_dict(mapping_data)

        # Parse validation rules
        validation_rules = []
        for rule_data in data.get("validation_rules", []):
            validation_rules.append(ValidationRule.from_dict(rule_data))

        return cls(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            layer_standards=layer_standards,
            layer_mapping=data.get("layer_mapping", {}),
            entity_layer_rules=data.get("entity_layer_rules", {}),
            dimension_standards=dimension_standards,
            title_block_standard=title_block_standard,
            property_mappings=property_mappings,
            validation_rules=validation_rules,
            drawing_type=data.get("drawing_type", "general"),
        )

    def save_to_file(self, path: Path) -> None:
        """Save configuration to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load_from_file(cls, path: Path) -> "StandardConfig":
        """Load configuration from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
