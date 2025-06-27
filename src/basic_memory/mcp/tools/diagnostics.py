"""Diagnostic tool for Basic Memory MCP server."""

import platform
import sys
from typing import Optional
from pathlib import Path

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.mcp.project_session import get_active_project
import basic_memory


def _get_system_info() -> list[str]:
    """Get system information for diagnostic output."""
    info_lines = []
    
    try:
        info_lines.extend([
            f"**Python Version**: {sys.version.split()[0]}",
            f"**Platform**: {platform.system()} {platform.release()}",
            f"**Architecture**: {platform.machine()}",
            f"**Python Implementation**: {platform.python_implementation()}",
        ])
        
        # Add Python executable path
        info_lines.append(f"**Python Executable**: {sys.executable}")
        
        # Add current working directory
        info_lines.append(f"**Working Directory**: {Path.cwd()}")
        
    except Exception as e:
        logger.debug(f"Could not get some system info: {e}")
        info_lines.append(f"**System Info Error**: {str(e)}")
    
    return info_lines


def _get_configuration_summary() -> list[str]:
    """Get configuration summary for diagnostic output."""
    config_lines = []
    
    try:
        from basic_memory.config import app_config, config_manager
        
        config_lines.extend([
            f"**Environment**: {app_config.env}",
            f"**Log Level**: {app_config.log_level}",
            f"**Default Project**: {app_config.default_project}",
            f"**Total Projects**: {len(app_config.projects)}",
            f"**Sync Delay**: {app_config.sync_delay}ms",
            f"**Update Permalinks on Move**: {app_config.update_permalinks_on_move}",
            f"**Sync Changes**: {app_config.sync_changes}",
        ])
        
        # Add database info
        config_lines.append(f"**Database Path**: {app_config.app_database_path}")
        config_lines.append(f"**Config Directory**: {config_manager.config_dir}")
        
        # Add project list
        if app_config.projects:
            config_lines.extend(["", "**Configured Projects**:"])
            for name, path in app_config.projects.items():
                is_default = " (default)" if name == app_config.default_project else ""
                config_lines.append(f"- {name}: {path}{is_default}")
        
    except Exception as e:
        logger.debug(f"Could not get configuration info: {e}")
        config_lines.append(f"**Configuration Error**: {str(e)}")
    
    return config_lines


def _get_tool_availability() -> list[str]:
    """Get available MCP tools for diagnostic output."""
    tool_lines = []
    
    try:
        # List of expected tools based on the __init__.py file
        expected_tools = [
            "build_context", "canvas", "create_project", "delete_note",
            "delete_project", "edit_note", "get_current_project", "list_directory",
            "list_projects", "move_note", "read_content", "read_note",
            "recent_activity", "search_notes", "set_default_project",
            "switch_project", "sync_status", "view_note", "write_note",
            "diagnostics"  # Include this tool itself
        ]
        
        tool_lines.extend([
            f"**Available Tools**: {len(expected_tools)}",
            "",
            "**Tool List**:"
        ])
        
        # Group tools by category for better readability
        categories = {
            "Content Management": [
                "write_note", "read_note", "edit_note", "delete_note", 
                "move_note", "view_note", "read_content"
            ],
            "Project Management": [
                "list_projects", "switch_project", "get_current_project",
                "create_project", "delete_project", "set_default_project"
            ],
            "Navigation & Discovery": [
                "build_context", "list_directory", "search_notes", "recent_activity"
            ],
            "Visualization": ["canvas"],
            "System": ["sync_status", "diagnostics"]
        }
        
        for category, tools in categories.items():
            tool_lines.append(f"- **{category}**: {', '.join(tools)}")
        
    except Exception as e:
        logger.debug(f"Could not get tool availability: {e}")
        tool_lines.append(f"**Tool Availability Error**: {str(e)}")
    
    return tool_lines


@mcp.tool(
    description="""Get comprehensive diagnostic information for Basic Memory installation.
    
    This tool provides:
    - Basic Memory version and build information
    - System environment details (Python, OS, architecture)
    - Configuration summary and project status
    - Available MCP tools and their categories
    - Current project context
    
    Use this tool to:
    - Troubleshoot installation issues
    - Verify feature availability
    - Confirm system compatibility
    - Support debugging and issue reporting
    - Check configuration status
    """,
)
async def diagnostics(project: Optional[str] = None) -> str:
    """Get comprehensive diagnostic information for Basic Memory.

    This tool provides detailed information about the Basic Memory installation,
    system environment, configuration, and available functionality.

    Args:
        project: Optional project name to include project-specific context

    Returns:
        Comprehensive diagnostic report with version, system, and status information
    """
    logger.info("MCP tool call tool=diagnostics")

    diagnostic_lines = []

    try:
        # Header
        diagnostic_lines.extend([
            "# Basic Memory Diagnostics",
            "",
            f"**Version**: {basic_memory.__version__}",
            f"**API Version**: {basic_memory.__api_version__}",
            "",
        ])

        # System Information
        diagnostic_lines.extend(["## System Information", ""])
        diagnostic_lines.extend(_get_system_info())
        diagnostic_lines.extend(["", ""])

        # Configuration Summary
        diagnostic_lines.extend(["## Configuration", ""])
        diagnostic_lines.extend(_get_configuration_summary())
        diagnostic_lines.extend(["", ""])

        # Tool Availability
        diagnostic_lines.extend(["## Tool Availability", ""])
        diagnostic_lines.extend(_get_tool_availability())
        diagnostic_lines.extend(["", ""])

        # Project Context
        diagnostic_lines.extend(["## Project Context", ""])
        if project:
            try:
                active_project = get_active_project(project)
                diagnostic_lines.extend([
                    f"**Requested Project**: {project}",
                    f"**Active Project Name**: {active_project.name}",
                    f"**Project Path**: {active_project.home}",
                ])
            except Exception as e:
                diagnostic_lines.extend([
                    f"**Requested Project**: {project}",
                    f"**Project Error**: {str(e)}",
                ])
        else:
            try:
                from basic_memory.config import app_config
                diagnostic_lines.extend([
                    f"**Default Project**: {app_config.default_project}",
                    "**Note**: Use the 'project' parameter to get specific project context",
                ])
            except Exception as e:
                diagnostic_lines.append(f"**Project Context Error**: {str(e)}")

        diagnostic_lines.extend(["", ""])

        # Footer with usage info
        diagnostic_lines.extend([
            "## Usage Notes",
            "",
            "- This diagnostic tool helps troubleshoot Basic Memory installations",
            "- Share this output when reporting issues for faster support",
            "- All sensitive paths and personal information should be reviewed before sharing",
            "- For more detailed logging, check the Basic Memory log files in ~/.basic-memory/",
        ])

        return "\n".join(diagnostic_lines)

    except Exception as e:
        return f"""# Basic Memory Diagnostics - Error

❌ **Unable to generate diagnostic information**: {str(e)}

**Troubleshooting:**
- The system may still be starting up
- Try waiting a few seconds and checking again
- Check logs for detailed error information
- Consider restarting if the issue persists

**Basic Information:**
- Basic Memory Version: {getattr(basic_memory, '__version__', 'Unknown')}
- Python Version: {sys.version.split()[0]}
- Platform: {platform.system()} {platform.release()}
"""