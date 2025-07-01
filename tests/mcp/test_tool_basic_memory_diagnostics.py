"""Tests for basic_memory_diagnostics MCP tool."""

import json
import platform
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import basic_memory
from basic_memory.mcp.tools.basic_memory_diagnostics import basic_memory_diagnostics


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_basic_functionality():
    """Test basic diagnostic functionality without project parameter."""
    result = await basic_memory_diagnostics.fn()

    # Check that key sections are present
    assert "# Basic Memory Diagnostics" in result
    assert "## Version Information" in result
    assert "## System Information" in result
    assert "## Configuration" in result
    assert "## Default Project Context" in result

    # Check version information
    assert f"**Basic Memory Version**: {basic_memory.__version__}" in result
    assert f"**API Version**: {basic_memory.__api_version__}" in result

    # Check system information
    assert f"**Python Version**: {sys.version.split()[0]}" in result
    assert f"**Platform**: {platform.system()} {platform.release()}" in result
    assert f"**Architecture**: {platform.machine()}" in result


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_with_project_parameter():
    """Test diagnostic with valid project parameter."""
    # Mock project session to return a valid project
    mock_project = MagicMock()
    mock_project.name = "test-project"
    mock_project.home = "/path/to/test-project"

    with patch("basic_memory.mcp.tools.basic_memory_diagnostics.get_active_project") as mock_get_project:
        mock_get_project.return_value = mock_project

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            result = await basic_memory_diagnostics.fn(project="test-project")

    # Check project-specific information
    assert "## Project Context" in result
    assert "**Requested Project**: test-project" in result
    assert "**Active Project Name**: test-project" in result
    assert "**Project Path**: /path/to/test-project" in result
    assert "**Project Exists**: ✅ Yes" in result


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_with_invalid_project():
    """Test diagnostic with invalid project parameter."""
    with patch("basic_memory.mcp.tools.basic_memory_diagnostics.get_active_project") as mock_get_project:
        mock_get_project.side_effect = Exception("Project not found")

        result = await basic_memory_diagnostics.fn(project="invalid-project")

    # Check error handling for invalid project
    assert "## Project Context" in result
    assert "**Requested Project**: invalid-project" in result
    assert "❌ **Project Error**: Project not found" in result
    assert "**Troubleshooting:**" in result


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_configuration_success():
    """Test diagnostic with successful configuration access."""
    # Mock app config
    mock_config = MagicMock()
    mock_config.env = "test"
    mock_config.projects = {"main": "/path/to/main", "secondary": "/path/to/secondary"}
    mock_config.default_project = "main"
    mock_config.log_level = "INFO"
    mock_config.debug = False
    mock_config.database_url = "sqlite:///test.db"
    mock_config._config_file_path = "/path/to/config.json"

    with patch("basic_memory.mcp.tools.basic_memory_diagnostics.app_config", mock_config):
        result = await basic_memory_diagnostics.fn()

    # Check configuration information
    assert "**Config File Path**: /path/to/config.json" in result
    assert "**Configuration JSON**:" in result
    assert '"env": "test"' in result
    assert '"main": "/path/to/main"' in result
    assert '"default_project": "main"' in result


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_configuration_error():
    """Test diagnostic when configuration access fails."""
    with patch("basic_memory.mcp.tools.basic_memory_diagnostics.app_config") as mock_config:
        # Simulate import error for configuration
        mock_config.side_effect = ImportError("Configuration not available")

        result = await basic_memory_diagnostics.fn()

    # Check error handling for configuration
    assert "❌ **Unable to access configuration**:" in result
    assert "**Troubleshooting:**" in result
    assert "configuration system may not be initialized" in result


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_exception_handling():
    """Test diagnostic handles unexpected exceptions gracefully."""
    # Mock basic_memory module to raise an exception when accessing version
    with patch.object(basic_memory, '__version__', side_effect=Exception("Unexpected error")):
        result = await basic_memory_diagnostics.fn()

    # Should return error format but still include minimal info
    assert "# Basic Memory Diagnostics - Error" in result
    assert "❌ **Unable to generate diagnostic information**:" in result
    assert "**Troubleshooting:**" in result
    assert "**Minimal Information Available:**" in result


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_default_project_info():
    """Test diagnostic shows default project information correctly."""
    # Mock app config with default project
    mock_config = MagicMock()
    mock_config.default_project = "main"
    mock_config.projects = {"main": "/path/to/main"}

    with patch("basic_memory.mcp.tools.basic_memory_diagnostics.app_config", mock_config):
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            result = await basic_memory_diagnostics.fn()

    # Check default project information
    assert "## Default Project Context" in result
    assert "**Default Project**: main" in result
    assert "**Default Project Path**: /path/to/main" in result
    assert "**Project Exists**: ✅ Yes" in result


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_default_project_missing():
    """Test diagnostic handles missing default project gracefully."""
    # Mock app config with default project that doesn't exist
    mock_config = MagicMock()
    mock_config.default_project = "main"
    mock_config.projects = {"main": "/path/to/nonexistent"}

    with patch("basic_memory.mcp.tools.basic_memory_diagnostics.app_config", mock_config):
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            result = await basic_memory_diagnostics.fn()

    # Check missing project indication
    assert "**Project Exists**: ❌ No" in result


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_json_serialization():
    """Test that configuration JSON serialization works correctly."""
    # Mock app config with complex data types
    mock_config = MagicMock()
    mock_config.env = "test"
    mock_config.projects = {"main": "/path/to/main"}
    mock_config.default_project = "main"
    mock_config.log_level = "DEBUG"
    mock_config.debug = True
    mock_config.database_url = "sqlite:///memory.db"

    with patch("basic_memory.mcp.tools.basic_memory_diagnostics.app_config", mock_config):
        result = await basic_memory_diagnostics.fn()

    # Extract and validate JSON content
    json_start = result.find("```json\n") + 8
    json_end = result.find("\n```", json_start)
    json_content = result[json_start:json_end]

    # Should be valid JSON
    parsed_config = json.loads(json_content)
    assert parsed_config["env"] == "test"
    assert parsed_config["projects"]["main"] == "/path/to/main"
    assert parsed_config["default_project"] == "main"
    assert parsed_config["debug"] is True


@pytest.mark.asyncio
async def test_basic_memory_diagnostics_project_nonexistent_path():
    """Test diagnostic with project that has non-existent path."""
    # Mock project session to return a project with non-existent path
    mock_project = MagicMock()
    mock_project.name = "test-project"
    mock_project.home = "/nonexistent/path"

    with patch("basic_memory.mcp.tools.basic_memory_diagnostics.get_active_project") as mock_get_project:
        mock_get_project.return_value = mock_project

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            result = await basic_memory_diagnostics.fn(project="test-project")

    # Check that non-existent path is indicated
    assert "**Project Exists**: ❌ No" in result