"""Diagnostic tool for Basic Memory MCP server."""

import json
import platform
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

import basic_memory
from basic_memory.mcp.server import mcp
from basic_memory.mcp.project_session import get_active_project


@mcp.tool(
    description="""Get comprehensive diagnostic information for Basic Memory installation.
    
    Use this tool to:
    - Check Basic Memory version and build information
    - Get system details (Python, OS, architecture)
    - View current configuration settings
    - Get project context information
    - Troubleshoot installation issues
    
    This information is helpful for:
    - Verifying which version is running
    - Troubleshooting compatibility issues
    - Gathering system info for support requests
    - Confirming configuration settings
    """,
)
async def basic_memory_diagnostics(project: Optional[str] = None) -> str:
    """Get diagnostic information about Basic Memory installation and system.

    This tool provides comprehensive diagnostic information including version,
    system details, configuration, and project context.

    Args:
        project: Optional project name to get project-specific context

    Returns:
        Formatted diagnostic information with version, system, and config details
    """
    logger.info("MCP tool call tool=basic_memory_diagnostics")

    diagnostic_lines = []

    try:
        # Header
        diagnostic_lines.extend([
            "# Basic Memory Diagnostics",
            "",
        ])

        # Version Information
        diagnostic_lines.extend([
            "## Version Information",
            "",
            f"**Basic Memory Version**: {basic_memory.__version__}",
            f"**API Version**: {basic_memory.__api_version__}",
            "",
        ])

        # System Information
        diagnostic_lines.extend([
            "## System Information",
            "",
            f"**Python Version**: {sys.version.split()[0]}",
            f"**Platform**: {platform.system()} {platform.release()}",
            f"**Architecture**: {platform.machine()}",
            f"**Python Executable**: {sys.executable}",
            "",
        ])

        # Configuration Information
        diagnostic_lines.extend([
            "## Configuration",
            "",
        ])

        try:
            from basic_memory.config import app_config
            
            # Configuration file path
            config_file_path = getattr(app_config, '_config_file_path', 'Unknown')
            diagnostic_lines.extend([
                f"**Config File Path**: {config_file_path}",
                "",
            ])

            # Dump configuration as JSON
            config_dict = {
                "env": app_config.env,
                "projects": app_config.projects,
                "default_project": app_config.default_project,
                "log_level": app_config.log_level,
                "debug": app_config.debug,
                "database_url": app_config.database_url,
            }

            diagnostic_lines.extend([
                "**Configuration JSON**:",
                "```json",
                json.dumps(config_dict, indent=2, default=str),
                "```",
                "",
            ])

        except Exception as e:
            diagnostic_lines.extend([
                f"❌ **Unable to access configuration**: {str(e)}",
                "",
                "**Troubleshooting:**",
                "- The configuration system may not be initialized",
                "- Check if Basic Memory is properly installed",
                "- Verify configuration file permissions",
                "",
            ])

        # Project Context
        if project:
            diagnostic_lines.extend([
                "## Project Context",
                "",
            ])

            try:
                active_project = get_active_project(project)
                diagnostic_lines.extend([
                    f"**Requested Project**: {project}",
                    f"**Active Project Name**: {active_project.name}",
                    f"**Project Path**: {active_project.home}",
                    f"**Project Exists**: {'✅ Yes' if Path(active_project.home).exists() else '❌ No'}",
                    "",
                ])
            except Exception as e:
                diagnostic_lines.extend([
                    f"**Requested Project**: {project}",
                    f"❌ **Project Error**: {str(e)}",
                    "",
                    "**Troubleshooting:**",
                    "- Check if the project name is correct",
                    "- Verify the project is configured in config.json",
                    "- Ensure project directory exists and is accessible",
                    "",
                ])
        else:
            # Show default project info
            diagnostic_lines.extend([
                "## Default Project Context",
                "",
            ])

            try:
                from basic_memory.config import app_config
                default_project_name = app_config.default_project
                diagnostic_lines.extend([
                    f"**Default Project**: {default_project_name}",
                ])

                if default_project_name and default_project_name in app_config.projects:
                    project_path = app_config.projects[default_project_name]
                    diagnostic_lines.extend([
                        f"**Default Project Path**: {project_path}",
                        f"**Project Exists**: {'✅ Yes' if Path(project_path).exists() else '❌ No'}",
                    ])
                
                diagnostic_lines.append("")

            except Exception as e:
                diagnostic_lines.extend([
                    f"❌ **Unable to get default project info**: {str(e)}",
                    "",
                ])

        # Footer with usage information
        diagnostic_lines.extend([
            "---",
            "",
            "**Usage**: This diagnostic information can help troubleshoot issues and verify your Basic Memory installation.",
            "**Support**: Include this information when reporting issues or requesting support.",
        ])

        return "\n".join(diagnostic_lines)

    except Exception as e:
        return f"""# Basic Memory Diagnostics - Error

❌ **Unable to generate diagnostic information**: {str(e)}

**Troubleshooting:**
- The system may still be starting up
- Try waiting a few seconds and running diagnostics again
- Check logs for detailed error information
- Verify Basic Memory is properly installed
- Consider restarting if the issue persists

**Minimal Information Available:**
- Python Version: {sys.version.split()[0]}
- Platform: {platform.system()} {platform.release()}
- Basic Memory Version: {getattr(basic_memory, '__version__', 'Unknown')}
"""