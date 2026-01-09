"""
PDM CLI commands.

Commands for PDM vault operations (checkout, checkin, properties).
"""

from pathlib import Path
import click
import yaml

from ..integration.pdm.factory import PDMClientFactory
from ..integration.pdm.property_handler import PropertyHandler
from ..data.models.standards import StandardConfig
from ..core.parsers.dxf_parser import DXFParser
from .utils import (
    validate_file_exists,
    echo_success,
    echo_error,
    echo_warning,
    echo_info,
    handle_error,
    confirm_action,
)


@click.group(name="pdm")
def pdm_group():
    """PDM vault operation commands."""
    pass


@pdm_group.command(name="connect")
@click.option(
    "--vault-name",
    required=True,
    help="PDM vault name",
)
@click.option(
    "--mock",
    is_flag=True,
    help="Use mock PDM client",
)
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    help="Mock vault root directory",
)
def test_connection(vault_name, mock, vault_root):
    """Test PDM vault connection."""
    try:
        echo_info(f"Connecting to vault: {vault_name}")

        # Create client
        client = PDMClientFactory.create_client(
            vault_name=vault_name, mock=mock, vault_root=vault_root
        )

        # Try connection
        if client.connect():
            echo_success(f"Successfully connected to vault '{vault_name}'")
            echo_info(f"Client type: {type(client).__name__}")

            if client.is_connected():
                echo_success("Connection verified")
            else:
                echo_warning("Connection successful but not verified")
        else:
            echo_error("Failed to connect to vault")

    except Exception as e:
        handle_error(e)


@pdm_group.command(name="checkout")
@click.argument("vault_path")
@click.argument("local_path", type=click.Path(path_type=Path))
@click.option(
    "--vault-name",
    required=True,
    help="PDM vault name",
)
@click.option(
    "--mock",
    is_flag=True,
    help="Use mock PDM client",
)
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    help="Mock vault root directory",
)
def checkout_file(vault_path, local_path, vault_name, mock, vault_root):
    """Check out file from PDM vault."""
    try:
        echo_info(f"Checking out: {vault_path}")

        # Create client
        client = PDMClientFactory.create_client(
            vault_name=vault_name, mock=mock, vault_root=vault_root
        )

        if not client.connect():
            echo_error("Failed to connect to vault")
            return

        # Check file state
        file_state = client.get_file_state(vault_path)
        echo_info(f"Current state: {file_state.state.value}")
        echo_info(f"Version: {file_state.version}")

        if file_state.checked_out_by:
            echo_warning(f"Checked out by: {file_state.checked_out_by}")

        # Checkout
        result = client.checkout(vault_path, local_path)

        if result.success:
            echo_success(f"File checked out to {local_path}")
            echo_info(f"Version: {result.version}")
        else:
            echo_error(f"Checkout failed: {result.error}")

    except Exception as e:
        handle_error(e)


@pdm_group.command(name="checkin")
@click.argument("local_path", type=click.Path(exists=True, path_type=Path))
@click.argument("vault_path")
@click.option(
    "--comment",
    "-m",
    default="",
    help="Check-in comment",
)
@click.option(
    "--vault-name",
    required=True,
    help="PDM vault name",
)
@click.option(
    "--mock",
    is_flag=True,
    help="Use mock PDM client",
)
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    help="Mock vault root directory",
)
def checkin_file(local_path, vault_path, comment, vault_name, mock, vault_root):
    """Check in file to PDM vault."""
    try:
        local_path = validate_file_exists(local_path)

        echo_info(f"Checking in: {local_path} → {vault_path}")

        # Create client
        client = PDMClientFactory.create_client(
            vault_name=vault_name, mock=mock, vault_root=vault_root
        )

        if not client.connect():
            echo_error("Failed to connect to vault")
            return

        # Confirm
        if not confirm_action(f"Check in {local_path.name}?", default=True):
            echo_warning("Check-in cancelled")
            return

        # Checkin
        result = client.checkin(local_path, vault_path, comment=comment)

        if result.success:
            echo_success(f"File checked in successfully")
            echo_info(f"New version: {result.new_version}")
            if result.previous_version:
                echo_info(f"Previous version: {result.previous_version}")
        else:
            echo_error(f"Check-in failed: {result.error}")

    except Exception as e:
        handle_error(e)


@pdm_group.command(name="status")
@click.argument("vault_path")
@click.option(
    "--vault-name",
    required=True,
    help="PDM vault name",
)
@click.option(
    "--mock",
    is_flag=True,
    help="Use mock PDM client",
)
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    help="Mock vault root directory",
)
def file_status(vault_path, vault_name, mock, vault_root):
    """Check file status in PDM vault."""
    try:
        # Create client
        client = PDMClientFactory.create_client(
            vault_name=vault_name, mock=mock, vault_root=vault_root
        )

        if not client.connect():
            echo_error("Failed to connect to vault")
            return

        # Get state
        file_state = client.get_file_state(vault_path)

        # Display status
        click.echo()
        click.echo(f"File: {vault_path}")
        click.echo(f"State: {file_state.state.value}")
        click.echo(f"Version: {file_state.version}")

        if file_state.checked_out_by:
            click.echo(f"Checked out by: {file_state.checked_out_by}")

        if file_state.custom_properties:
            click.echo()
            click.echo("Custom Properties:")
            for key, value in file_state.custom_properties.items():
                click.echo(f"  {key}: {value}")

    except Exception as e:
        handle_error(e)


@pdm_group.command(name="set-properties")
@click.argument("vault_path")
@click.argument("properties_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--vault-name",
    required=True,
    help="PDM vault name",
)
@click.option(
    "--mock",
    is_flag=True,
    help="Use mock PDM client",
)
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path),
    help="Mock vault root directory",
)
def set_properties(vault_path, properties_file, vault_name, mock, vault_root):
    """Set custom properties from YAML file."""
    try:
        properties_file = validate_file_exists(properties_file)

        # Load properties
        with open(properties_file) as f:
            properties = yaml.safe_load(f)

        if not isinstance(properties, dict):
            echo_error("Properties file must contain a dictionary")
            return

        echo_info(f"Setting {len(properties)} properties on {vault_path}")

        # Create client
        client = PDMClientFactory.create_client(
            vault_name=vault_name, mock=mock, vault_root=vault_root
        )

        if not client.connect():
            echo_error("Failed to connect to vault")
            return

        # Set properties
        success = client.set_custom_properties(vault_path, properties)

        if success:
            echo_success(f"Properties set successfully")
            click.echo()
            for key, value in properties.items():
                click.echo(f"  {key}: {value}")
        else:
            echo_error("Failed to set properties")

    except Exception as e:
        handle_error(e)


@pdm_group.command(name="extract-properties")
@click.argument("drawing_file", type=click.Path(exists=True, path_type=Path))
@click.argument("standards_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output YAML file (defaults to stdout)",
)
def extract_properties(drawing_file, standards_file, output):
    """Extract custom properties from CAD drawing based on standards."""
    try:
        drawing_file = validate_file_exists(drawing_file)
        standards_file = validate_file_exists(standards_file)

        echo_info(f"Extracting properties from: {drawing_file}")

        # Load standards
        with open(standards_file) as f:
            standards_data = yaml.safe_load(f)
        standards_config = StandardConfig.from_dict(standards_data)

        # Parse drawing
        parser = DXFParser()
        drawing = parser.parse(drawing_file)

        # Extract properties
        # Create mock client just for property handler
        from ..integration.pdm.models import VaultConfig
        from ..integration.pdm.mock_client import MockPDMClient

        vault_config = VaultConfig(vault_name="temp", vault_root=Path("/tmp"))
        mock_client = MockPDMClient(vault_config)

        property_mappings = standards_config.property_mappings or {}
        handler = PropertyHandler(mock_client, property_mappings)
        properties = handler.extract_properties(drawing)

        # Display or save
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w") as f:
                yaml.dump(properties, f, default_flow_style=False)
            echo_success(f"Properties saved to {output}")
        else:
            click.echo()
            click.echo(yaml.dump(properties, default_flow_style=False))

        echo_info(f"Extracted {len(properties)} properties")

    except Exception as e:
        handle_error(e)
