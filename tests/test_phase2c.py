"""
Test suite for Phase 2C: Standards Learning and PDM Integration.

Tests:
- Confidence scoring
- Layer learner
- Dimension learner
- Title block learner
- Learning engine
- Mock PDM client
- Property handler
- PDM client factory
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from collections import Counter

# Learning system imports
from src.integration.learning.models import Observation, LearnedRule, LearningResult
from src.integration.learning.confidence import ConfidenceScorer
from src.integration.learning.layer_learner import LayerLearner
from src.integration.learning.dimension_learner import DimensionLearner
from src.integration.learning.title_block_learner import TitleBlockLearner
from src.core.parsers.base_parser import ParsedDrawing

# PDM imports
from src.integration.pdm.models import (
    PDMFile,
    PDMFileState,
    CheckInResult,
    VaultConfig,
)
from src.integration.pdm.mock_client import MockPDMClient
from src.integration.pdm.property_handler import PropertyHandler
from src.integration.pdm.factory import PDMClientFactory
from src.data.models.standards import PropertyMapping


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


# ============================================================================
# Confidence Scorer Tests
# ============================================================================


def test_confidence_scorer_perfect_agreement():
    """Test confidence scoring with perfect agreement."""
    scorer = ConfidenceScorer(min_samples=2)

    observations = [
        Observation("layer1", "GEOMETRY", (Path("a.dxf"), Path("b.dxf"))),
        Observation("layer1", "GEOMETRY", (Path("c.dxf"), Path("d.dxf"))),
        Observation("layer1", "GEOMETRY", (Path("e.dxf"), Path("f.dxf"))),
    ]

    confidence = scorer.calculate_confidence(observations)
    assert confidence == 1.0  # Perfect agreement


def test_confidence_scorer_majority():
    """Test confidence scoring with majority agreement."""
    scorer = ConfidenceScorer(min_samples=2)

    observations = [
        Observation("layer1", "GEOMETRY", (Path("a.dxf"), Path("b.dxf"))),
        Observation("layer1", "GEOMETRY", (Path("c.dxf"), Path("d.dxf"))),
        Observation("layer1", "GEOMETRY", (Path("e.dxf"), Path("f.dxf"))),
        Observation("layer1", "OBJECT", (Path("g.dxf"), Path("h.dxf"))),  # Outlier
    ]

    confidence = scorer.calculate_confidence(observations)
    assert confidence > 0.5  # 75% agreement should give reasonable confidence
    assert confidence < 1.0


def test_confidence_scorer_creates_rule():
    """Test rule creation from observations."""
    scorer = ConfidenceScorer(min_samples=2)

    observations = [
        Observation("0", "GEOMETRY", (Path("a.dxf"), Path("b.dxf"))),
        Observation("0", "GEOMETRY", (Path("c.dxf"), Path("d.dxf"))),
    ]

    rule = scorer.create_rule_from_observations(
        "layer_mapping", "0", observations, min_confidence=0.7
    )

    assert rule is not None
    assert rule.source_pattern == "0"
    assert rule.target_value == "GEOMETRY"
    assert rule.confidence >= 0.7


# ============================================================================
# Layer Learner Tests
# ============================================================================


def test_layer_learner_extract_observations():
    """Test layer learner extracts observations correctly."""
    learner = LayerLearner(min_confidence=0.7)

    old_drawing = ParsedDrawing(
        file_path=Path("old.dxf"),
        file_type="DXF",
        layers={
            "0": {
                "entities": [
                    {"type": "LINE"},
                    {"type": "CIRCLE"},
                ],
            },
        },
        entities=[{"type": "LINE"}, {"type": "CIRCLE"}],
        blocks={},
        title_block={},
        attributes={},
        metadata={},
        raw_data=None,
    )

    new_drawing = ParsedDrawing(
        file_path=Path("new.dxf"),
        file_type="DXF",
        layers={
            "GEOMETRY": {
                "entities": [
                    {"type": "LINE"},
                    {"type": "CIRCLE"},
                ],
            },
        },
        entities=[{"type": "LINE"}, {"type": "CIRCLE"}],
        blocks={},
        title_block={},
        attributes={},
        metadata={},
        raw_data=None,
    )

    observations = learner.extract_observations(
        old_drawing, new_drawing, (Path("old.dxf"), Path("new.dxf"))
    )

    assert len(observations) > 0
    assert observations[0].source == "0"
    assert observations[0].target == "GEOMETRY"


# ============================================================================
# Dimension Learner Tests
# ============================================================================


def test_dimension_learner_extract_observations():
    """Test dimension learner extracts property observations."""
    learner = DimensionLearner(min_confidence=0.7)

    old_drawing = ParsedDrawing(
        file_path=Path("old.dxf"),
        file_type="DXF",
        layers={
            "DIMS": {
                "entities": [
                    {"type": "DIMENSION", "arrow_size": 0.1, "text_height": 0.1},
                ],
            },
        },
        entities=[{"type": "DIMENSION"}],
        blocks={},
        title_block={},
        attributes={},
        metadata={},
        raw_data=None,
    )

    new_drawing = ParsedDrawing(
        file_path=Path("new.dxf"),
        file_type="DXF",
        layers={
            "DIMENSIONS": {
                "entities": [
                    {"type": "DIMENSION", "arrow_size": 0.18, "text_height": 0.125},
                ],
            },
        },
        entities=[{"type": "DIMENSION"}],
        blocks={},
        title_block={},
        attributes={},
        metadata={},
        raw_data=None,
    )

    observations = learner.extract_observations(
        old_drawing, new_drawing, (Path("old.dxf"), Path("new.dxf"))
    )

    # Should detect arrow_size and text_height changes
    assert len(observations) == 2
    sources = [obs.source for obs in observations]
    assert "arrow_size:0.1" in sources
    assert "text_height:0.1" in sources


# ============================================================================
# Title Block Learner Tests
# ============================================================================


def test_title_block_learner_exact_match():
    """Test title block learner with exact field matches."""
    learner = TitleBlockLearner(min_confidence=0.7)

    old_drawing = ParsedDrawing(
        file_path=Path("old.dxf"),
        file_type="DXF",
        layers={},
        entities=[],
        blocks={},
        title_block={"title": "Drawing 1", "number": "001"},
        attributes={},
        metadata={},
        raw_data=None,
    )

    new_drawing = ParsedDrawing(
        file_path=Path("new.dxf"),
        file_type="DXF",
        layers={},
        entities=[],
        blocks={},
        title_block={"title": "Drawing 1", "number": "001"},
        attributes={},
        metadata={},
        raw_data=None,
    )

    observations = learner.extract_observations(
        old_drawing, new_drawing, (Path("old.dxf"), Path("new.dxf"))
    )

    # Exact matches
    assert len(observations) == 2
    assert all(obs.source == obs.target for obs in observations)


def test_title_block_learner_levenshtein():
    """Test Levenshtein distance calculation."""
    learner = TitleBlockLearner()

    distance = learner._levenshtein_distance("kitten", "sitting")
    assert distance == 3

    distance = learner._levenshtein_distance("hello", "hello")
    assert distance == 0


# ============================================================================
# Mock PDM Client Tests
# ============================================================================


def test_mock_pdm_client_connect(temp_dir):
    """Test mock PDM client connection."""
    vault_root = temp_dir / "mock_vault"
    config = VaultConfig(vault_name="test_vault", vault_root=vault_root)
    client = MockPDMClient(config)

    assert client.connect()
    assert client.is_connected()

    # Check structure created
    assert (vault_root / "files").exists()
    assert (vault_root / "metadata").exists()
    assert (vault_root / "versions").exists()
    assert (vault_root / "checkouts.json").exists()


def test_mock_pdm_client_add_file(temp_dir):
    """Test adding file to mock vault."""
    vault_root = temp_dir / "mock_vault"
    config = VaultConfig(vault_name="test_vault", vault_root=vault_root)
    client = MockPDMClient(config)
    client.connect()

    # Create test file
    test_file = temp_dir / "test.dxf"
    test_file.write_text("test content")

    # Add to vault
    result = client.add_file(test_file, "drawings", comment="Initial add")

    assert result.success
    assert result.new_version == 1

    # Verify file in vault
    file_state = client.get_file_state("drawings/test.dxf")
    assert file_state.state == PDMFileState.CHECKED_IN
    assert file_state.version == 1


def test_mock_pdm_client_checkout_checkin(temp_dir):
    """Test checkout/checkin cycle."""
    vault_root = temp_dir / "mock_vault"
    config = VaultConfig(vault_name="test_vault", vault_root=vault_root)
    client = MockPDMClient(config)
    client.connect()

    # Add file
    test_file = temp_dir / "test.dxf"
    test_file.write_text("version 1")
    client.add_file(test_file, "drawings")

    # Checkout
    local_path = temp_dir / "local_test.dxf"
    checkout_result = client.checkout("drawings/test.dxf", local_path)

    assert checkout_result.success
    assert local_path.exists()

    # Verify checked out
    file_state = client.get_file_state("drawings/test.dxf")
    assert file_state.state == PDMFileState.CHECKED_OUT

    # Modify and checkin
    local_path.write_text("version 2")
    checkin_result = client.checkin(local_path, "drawings/test.dxf", "Updated")

    assert checkin_result.success
    assert checkin_result.new_version == 2

    # Verify checked in
    file_state = client.get_file_state("drawings/test.dxf")
    assert file_state.state == PDMFileState.CHECKED_IN
    assert file_state.version == 2


def test_mock_pdm_client_custom_properties(temp_dir):
    """Test custom properties operations."""
    vault_root = temp_dir / "mock_vault"
    config = VaultConfig(vault_name="test_vault", vault_root=vault_root)
    client = MockPDMClient(config)
    client.connect()

    # Add file
    test_file = temp_dir / "test.dxf"
    test_file.write_text("test")
    client.add_file(test_file, "drawings")

    # Set properties
    properties = {"Part Number": "12345", "Description": "Test Part"}
    success = client.set_custom_properties("drawings/test.dxf", properties)

    assert success

    # Get properties
    retrieved = client.get_custom_properties("drawings/test.dxf")

    assert retrieved["Part Number"] == "12345"
    assert retrieved["Description"] == "Test Part"


# ============================================================================
# Property Handler Tests
# ============================================================================


def test_property_handler_extract(temp_dir):
    """Test property extraction from drawing."""
    vault_root = temp_dir / "mock_vault"
    config = VaultConfig(vault_name="test_vault", vault_root=vault_root)
    client = MockPDMClient(config)

    property_mappings = {
        "Part Number": PropertyMapping(
            property_name="Part Number",
            source="title_block",
            source_key="number",
            required=True,
        ),
        "Title": PropertyMapping(
            property_name="Title",
            source="title_block",
            source_key="title",
            required=False,
        ),
    }

    handler = PropertyHandler(client, property_mappings)

    drawing = ParsedDrawing(
        file_path=Path("test.dxf"),
        file_type="DXF",
        layers={},
        entities=[],
        blocks={},
        title_block={"number": "12345", "title": "Test Drawing"},
        attributes={},
        metadata={},
        raw_data=None,
    )

    properties = handler.extract_properties(drawing)

    assert "Part Number" in properties
    assert properties["Part Number"] == "12345"
    assert properties["Title"] == "Test Drawing"


# ============================================================================
# PDM Client Factory Tests
# ============================================================================


def test_pdm_factory_creates_mock(temp_dir):
    """Test factory creates mock client."""
    client = PDMClientFactory.create_client(
        vault_name="test_vault", mock=True, vault_root=temp_dir / "mock_vault"
    )

    assert isinstance(client, MockPDMClient)


def test_pdm_factory_auto_detect():
    """Test factory auto-detection."""
    client_type = PDMClientFactory.auto_detect()

    # On Linux, should detect mock
    assert client_type in ["mock", "com"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
