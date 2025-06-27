"""Tests for diagnostics MCP tool."""

import pytest
from unittest.mock import MagicMock, patch
import platform
import sys

from basic_memory.mcp.tools.diagnostics import diagnostics
import basic_memory


@pytest.mark.asyncio
async def test_diagnostics_basic_functionality():
    """Test diagnostics tool returns expected basic information."""
    result = await diagnostics.fn()
    
    # Check basic structure
    assert "# Basic Memory Diagnostics" in result
    assert f"**Version**: {basic_memory.__version__}" in result
    assert f"**API Version**: {basic_memory.__api_version__}" in result
    
    # Check system information
    assert "## System Information" in result
    assert f"**Python Version**: {sys.version.split()[0]}" in result
    assert f"**Platform**: {platform.system()}" in result
    assert f"**Architecture**: {platform.machine()}" in result
    
    # Check tool availability section
    assert "## Tool Availability" in result
    assert "**Available Tools**:" in result
    assert "Content Management" in result
    assert "Project Management" in result
    
    # Check configuration section
    assert "## Configuration" in result
    
    # Check project context section
    assert "## Project Context" in result
    
    # Check usage notes
    assert "## Usage Notes" in result


@pytest.mark.asyncio
async def test_diagnostics_with_project():
    """Test diagnostics tool with project parameter."""
    # Mock get_active_project to return a test project
    mock_project = MagicMock()
    mock_project.name = "test-project"
    mock_project.home = "/path/to/test-project"
    
    with patch("basic_memory.mcp.tools.diagnostics.get_active_project", return_value=mock_project):
        result = await diagnostics.fn(project="test-project")
    
    assert "**Requested Project**: test-project" in result
    assert "**Active Project Name**: test-project" in result
    assert "**Project Path**: /path/to/test-project" in result


@pytest.mark.asyncio
async def test_diagnostics_with_invalid_project():
    """Test diagnostics tool with invalid project parameter."""
    # Mock get_active_project to raise an exception
    with patch("basic_memory.mcp.tools.diagnostics.get_active_project", side_effect=ValueError("Project not found")):
        result = await diagnostics.fn(project="invalid-project")
    
    assert "**Requested Project**: invalid-project" in result
    assert "**Project Error**: Project not found" in result


@pytest.mark.asyncio
async def test_diagnostics_configuration_section():
    """Test that configuration section includes expected information."""
    # Mock app_config for predictable testing
    mock_config = MagicMock()
    mock_config.env = "test"
    mock_config.log_level = "INFO"
    mock_config.default_project = "main"
    mock_config.projects = {"main": "/home/user/basic-memory", "work": "/home/user/work-notes"}
    mock_config.sync_delay = 1000
    mock_config.update_permalinks_on_move = False
    mock_config.sync_changes = True
    mock_config.app_database_path = "/home/user/.basic-memory/memory.db"
    
    mock_config_manager = MagicMock()
    mock_config_manager.config_dir = "/home/user/.basic-memory"
    
    with patch("basic_memory.mcp.tools.diagnostics.app_config", mock_config), \
         patch("basic_memory.mcp.tools.diagnostics.config_manager", mock_config_manager):
        result = await diagnostics.fn()
    
    assert "**Environment**: test" in result
    assert "**Log Level**: INFO" in result
    assert "**Default Project**: main" in result
    assert "**Total Projects**: 2" in result
    assert "**Sync Delay**: 1000ms" in result
    assert "**Update Permalinks on Move**: False" in result
    assert "**Sync Changes**: True" in result
    assert "**Database Path**: /home/user/.basic-memory/memory.db" in result
    assert "**Config Directory**: /home/user/.basic-memory" in result
    assert "- main: /home/user/basic-memory (default)" in result
    assert "- work: /home/user/work-notes" in result


@pytest.mark.asyncio
async def test_diagnostics_handles_configuration_error():
    """Test diagnostics tool handles configuration errors gracefully."""
    # Mock configuration to raise an exception
    with patch("basic_memory.mcp.tools.diagnostics.app_config", side_effect=ImportError("Config error")):
        result = await diagnostics.fn()
    
    # Should still return basic information
    assert "# Basic Memory Diagnostics" in result
    assert f"**Version**: {basic_memory.__version__}" in result
    assert "**Configuration Error**: Config error" in result


@pytest.mark.asyncio
async def test_diagnostics_exception_handling():
    """Test diagnostics tool handles major exceptions gracefully."""
    # Mock basic_memory to raise an exception when accessing __version__
    with patch.object(basic_memory, '__version__', side_effect=AttributeError("Version error")):
        result = await diagnostics.fn()
    
    # Should return error format
    assert "# Basic Memory Diagnostics - Error" in result
    assert "Unable to generate diagnostic information" in result
    assert "Troubleshooting:" in result


def test_get_system_info():
    """Test the _get_system_info helper function."""
    from basic_memory.mcp.tools.diagnostics import _get_system_info
    
    info_lines = _get_system_info()
    
    # Should include basic system info
    assert any("**Python Version**:" in line for line in info_lines)
    assert any("**Platform**:" in line for line in info_lines)
    assert any("**Architecture**:" in line for line in info_lines)
    assert any("**Python Implementation**:" in line for line in info_lines)


def test_get_tool_availability():
    """Test the _get_tool_availability helper function."""
    from basic_memory.mcp.tools.diagnostics import _get_tool_availability
    
    tool_lines = _get_tool_availability()
    
    # Should include tool categories
    assert any("**Available Tools**:" in line for line in tool_lines)
    assert any("**Content Management**:" in line for line in tool_lines)
    assert any("**Project Management**:" in line for line in tool_lines)
    assert any("**Navigation & Discovery**:" in line for line in tool_lines)
    assert any("**Visualization**:" in line for line in tool_lines)
    assert any("**System**:" in line for line in tool_lines)


def test_get_configuration_summary_with_mocked_config():
    """Test the _get_configuration_summary helper function with mocked config."""
    from basic_memory.mcp.tools.diagnostics import _get_configuration_summary
    
    # Mock the config imports
    mock_config = MagicMock()
    mock_config.env = "test"
    mock_config.log_level = "DEBUG"
    mock_config.default_project = "main"
    mock_config.projects = {"main": "/test/path"}
    mock_config.sync_delay = 500
    mock_config.update_permalinks_on_move = True
    mock_config.sync_changes = False
    mock_config.app_database_path = "/test/db.sqlite"
    
    mock_config_manager = MagicMock()
    mock_config_manager.config_dir = "/test/config"
    
    with patch("basic_memory.mcp.tools.diagnostics.app_config", mock_config), \
         patch("basic_memory.mcp.tools.diagnostics.config_manager", mock_config_manager):
        config_lines = _get_configuration_summary()
    
    # Should include all expected config info
    assert any("**Environment**: test" in line for line in config_lines)
    assert any("**Log Level**: DEBUG" in line for line in config_lines)
    assert any("**Default Project**: main" in line for line in config_lines)
    assert any("**Total Projects**: 1" in line for line in config_lines)