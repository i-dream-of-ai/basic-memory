"""Tests for diagnostics MCP tool."""

import pytest
from unittest.mock import MagicMock, patch, mock_open

from basic_memory.mcp.tools.diagnostics import diagnostics
from basic_memory.config import BasicMemoryConfig, ConfigManager


@pytest.mark.asyncio
async def test_diagnostics_basic_functionality():
    """Test basic diagnostics functionality."""
    # Mock config manager
    mock_config = BasicMemoryConfig(
        projects={"main": "/path/to/main", "test": "/path/to/test"},
        default_project="main"
    )
    
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        mock_manager.default_project = "main"
        mock_manager.get_project.return_value = ("main", "/path/to/main")
        
        with patch("pathlib.Path.exists", return_value=True):
            result = await diagnostics.fn()
    
    assert "version" in result
    assert "system" in result
    assert "configuration" in result
    assert "project_context" in result
    
    # Check version information
    assert "basic_memory_version" in result["version"]
    assert "api_version" in result["version"]
    
    # Check system information
    assert "python_version" in result["system"]
    assert "platform" in result["system"]
    
    # Check configuration information
    assert "config_file_path" in result["configuration"]
    assert "configuration" in result["configuration"]


@pytest.mark.asyncio
async def test_diagnostics_with_project_parameter():
    """Test diagnostics with specific project parameter."""
    mock_config = BasicMemoryConfig(
        projects={"main": "/path/to/main", "test": "/path/to/test"},
        default_project="main"
    )
    
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        mock_manager.get_project.return_value = ("test", "/path/to/test")
        
        with patch("pathlib.Path.exists", return_value=True):
            result = await diagnostics.fn(project="test")
    
    assert "project_context" in result
    assert result["project_context"]["requested_project"] == "test"
    assert result["project_context"]["resolved_project_name"] == "test"
    assert result["project_context"]["project_path"] == "/path/to/test"


@pytest.mark.asyncio
async def test_diagnostics_project_not_found():
    """Test diagnostics when requested project is not found."""
    mock_config = BasicMemoryConfig(
        projects={"main": "/path/to/main"},
        default_project="main"
    )
    
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        mock_manager.get_project.return_value = (None, None)
        
        result = await diagnostics.fn(project="nonexistent")
    
    assert "project_context" in result
    assert result["project_context"]["requested_project"] == "nonexistent"
    assert "error" in result["project_context"]
    assert "not found" in result["project_context"]["error"]


@pytest.mark.asyncio
async def test_diagnostics_config_loading_error():
    """Test diagnostics when config loading fails."""
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_manager.load_config.side_effect = Exception("Config loading failed")
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        
        result = await diagnostics.fn()
    
    assert "configuration" in result
    assert "error" in result["configuration"]
    assert "Config loading failed" in result["configuration"]["error"]


@pytest.mark.asyncio
async def test_diagnostics_project_access_error():
    """Test diagnostics when project access fails."""
    mock_config = BasicMemoryConfig(
        projects={"main": "/path/to/main"},
        default_project="main"
    )
    
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        mock_manager.get_project.side_effect = Exception("Access denied")
        
        result = await diagnostics.fn(project="main")
    
    assert "project_context" in result
    assert "error" in result["project_context"]
    assert "Access denied" in result["project_context"]["error"]


@pytest.mark.asyncio
async def test_diagnostics_default_project_context():
    """Test diagnostics without project parameter uses default project."""
    mock_config = BasicMemoryConfig(
        projects={"main": "/path/to/main"},
        default_project="main"
    )
    
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        mock_manager.default_project = "main"
        mock_manager.config = mock_config
        
        with patch("pathlib.Path.exists", return_value=True):
            result = await diagnostics.fn()
    
    assert "project_context" in result
    assert result["project_context"]["default_project"] == "main"
    assert "default_project_path" in result["project_context"]


@pytest.mark.asyncio
async def test_diagnostics_default_project_error():
    """Test diagnostics when default project access fails."""
    mock_config = BasicMemoryConfig(
        projects={"main": "/path/to/main"},
        default_project="main"
    )
    
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        mock_manager.default_project = "main"
        mock_manager.config.get_project_path.side_effect = Exception("Path error")
        
        result = await diagnostics.fn()
    
    assert "project_context" in result
    assert "error" in result["project_context"]
    assert "Path error" in result["project_context"]["error"]


@pytest.mark.asyncio
async def test_diagnostics_general_exception():
    """Test diagnostics handles general exceptions gracefully."""
    with patch("basic_memory.mcp.tools.diagnostics.basic_memory") as mock_basic_memory:
        mock_basic_memory.__version__ = None  # This should cause an error
        
        result = await diagnostics.fn()
    
    assert "error" in result
    assert "troubleshooting" in result
    assert "suggestions" in result["troubleshooting"]
    assert len(result["troubleshooting"]["suggestions"]) > 0


@pytest.mark.asyncio
async def test_diagnostics_config_file_not_exists():
    """Test diagnostics when config file doesn't exist."""
    mock_config = BasicMemoryConfig(
        projects={"main": "/path/to/main"},
        default_project="main"
    )
    
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = False
        mock_manager.default_project = "main"
        mock_manager.config = mock_config
        
        with patch("pathlib.Path.exists", return_value=True):
            result = await diagnostics.fn()
    
    assert "configuration" in result
    assert result["configuration"]["config_exists"] is False
    assert "config_file_path" in result["configuration"]


@pytest.mark.asyncio
async def test_diagnostics_version_information():
    """Test that version information is correctly extracted."""
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_config = BasicMemoryConfig()
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        mock_manager.default_project = "main"
        mock_manager.config = mock_config
        
        with patch("pathlib.Path.exists", return_value=True):
            result = await diagnostics.fn()
    
    assert "version" in result
    version_info = result["version"]
    
    # These should contain the actual values from basic_memory.__version__ and __api_version__
    assert "basic_memory_version" in version_info
    assert "api_version" in version_info
    assert isinstance(version_info["basic_memory_version"], str)
    assert isinstance(version_info["api_version"], str)


@pytest.mark.asyncio
async def test_diagnostics_system_information():
    """Test that system information is correctly gathered."""
    with patch("basic_memory.mcp.tools.diagnostics.config_manager") as mock_manager:
        mock_config = BasicMemoryConfig()
        mock_manager.load_config.return_value = mock_config
        mock_manager.config_file = "/home/user/.basic-memory/config.json"
        mock_manager.config_file.exists.return_value = True
        mock_manager.default_project = "main"
        mock_manager.config = mock_config
        
        with patch("pathlib.Path.exists", return_value=True):
            result = await diagnostics.fn()
    
    assert "system" in result
    system_info = result["system"]
    
    # Check that all expected system fields are present
    expected_fields = [
        "python_version", "python_executable", "platform", 
        "machine", "processor", "architecture"
    ]
    
    for field in expected_fields:
        assert field in system_info