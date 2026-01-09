"""
File utility functions.

Provides file comparison, statistics, and helper functions.
"""

from pathlib import Path
from typing import List, Dict, Tuple
import hashlib
from ..core.parsers.dxf_parser import DXFParser
from ..core.parsers.base_parser import ParsedDrawing


def calculate_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """
    Calculate file hash.

    Args:
        file_path: File to hash
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hex digest of file hash
    """
    hash_func = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def compare_files(file1: Path, file2: Path) -> Dict[str, any]:
    """
    Compare two CAD files.

    Args:
        file1: First file
        file2: Second file

    Returns:
        Comparison results with differences
    """
    parser = DXFParser()

    # Parse both files
    drawing1 = parser.parse(file1)
    drawing2 = parser.parse(file2)

    # Compare layers
    layers_added, layers_removed, layers_changed = _compare_layers(drawing1, drawing2)

    # Compare entities
    entity_diff = _compare_entities(drawing1, drawing2)

    # Compare title blocks
    title_block_diff = _compare_title_blocks(drawing1, drawing2)

    return {
        "files": {"file1": str(file1), "file2": str(file2)},
        "identical": (
            not layers_added
            and not layers_removed
            and not layers_changed
            and entity_diff["added"] == 0
            and entity_diff["removed"] == 0
        ),
        "layers": {
            "added": layers_added,
            "removed": layers_removed,
            "changed": layers_changed,
        },
        "entities": entity_diff,
        "title_block": title_block_diff,
    }


def _compare_layers(
    drawing1: ParsedDrawing, drawing2: ParsedDrawing
) -> Tuple[List[str], List[str], List[str]]:
    """Compare layers between two drawings."""
    layers1 = set(drawing1.layers.keys())
    layers2 = set(drawing2.layers.keys())

    added = list(layers2 - layers1)
    removed = list(layers1 - layers2)

    # Check for property changes in common layers
    changed = []
    common_layers = layers1 & layers2
    for layer_name in common_layers:
        layer1 = drawing1.layers[layer_name]
        layer2 = drawing2.layers[layer_name]

        # Compare layer properties
        if layer1.get("color") != layer2.get("color"):
            changed.append(f"{layer_name} (color changed)")
        elif layer1.get("linetype") != layer2.get("linetype"):
            changed.append(f"{layer_name} (linetype changed)")

    return added, removed, changed


def _compare_entities(
    drawing1: ParsedDrawing, drawing2: ParsedDrawing
) -> Dict[str, int]:
    """Compare entity counts between drawings."""
    entities1_by_type = {}
    entities2_by_type = {}

    for entity in drawing1.entities:
        entity_type = entity.get("type", "UNKNOWN")
        entities1_by_type[entity_type] = entities1_by_type.get(entity_type, 0) + 1

    for entity in drawing2.entities:
        entity_type = entity.get("type", "UNKNOWN")
        entities2_by_type[entity_type] = entities2_by_type.get(entity_type, 0) + 1

    all_types = set(entities1_by_type.keys()) | set(entities2_by_type.keys())

    diff = {}
    added = 0
    removed = 0

    for entity_type in all_types:
        count1 = entities1_by_type.get(entity_type, 0)
        count2 = entities2_by_type.get(entity_type, 0)
        delta = count2 - count1

        if delta != 0:
            diff[entity_type] = delta

        if delta > 0:
            added += delta
        else:
            removed += abs(delta)

    return {"added": added, "removed": removed, "by_type": diff}


def _compare_title_blocks(
    drawing1: ParsedDrawing, drawing2: ParsedDrawing
) -> Dict[str, any]:
    """Compare title blocks between drawings."""
    tb1 = drawing1.title_block
    tb2 = drawing2.title_block

    all_keys = set(tb1.keys()) | set(tb2.keys())

    added = {}
    removed = {}
    changed = {}

    for key in all_keys:
        val1 = tb1.get(key)
        val2 = tb2.get(key)

        if val1 is None and val2 is not None:
            added[key] = val2
        elif val1 is not None and val2 is None:
            removed[key] = val1
        elif val1 != val2:
            changed[key] = {"from": val1, "to": val2}

    return {"added": added, "removed": removed, "changed": changed}


def get_file_statistics(file_paths: List[Path]) -> Dict[str, any]:
    """
    Get statistics for a collection of CAD files.

    Args:
        file_paths: List of file paths

    Returns:
        Statistics dictionary
    """
    total_size = 0
    total_entities = 0
    layer_counts = {}
    entity_type_counts = {}

    parser = DXFParser()

    for file_path in file_paths:
        try:
            # File size
            total_size += file_path.stat().st_size

            # Parse and count
            drawing = parser.parse(file_path)

            # Entity counts
            total_entities += len(drawing.entities)

            # Layer counts
            for layer_name in drawing.layers.keys():
                layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1

            # Entity type counts
            for entity in drawing.entities:
                entity_type = entity.get("type", "UNKNOWN")
                entity_type_counts[entity_type] = (
                    entity_type_counts.get(entity_type, 0) + 1
                )

        except Exception:
            pass  # Skip files that can't be parsed

    return {
        "file_count": len(file_paths),
        "total_size": total_size,
        "avg_size": total_size / len(file_paths) if file_paths else 0,
        "total_entities": total_entities,
        "avg_entities": total_entities / len(file_paths) if file_paths else 0,
        "unique_layers": len(layer_counts),
        "layer_usage": layer_counts,
        "entity_types": entity_type_counts,
    }
