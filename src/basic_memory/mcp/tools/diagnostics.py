"""Diagnostic tool for Basic Memory system information."""

import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import basic_memory
from basic_memory.config import config_manager
from basic_memory.mcp.tools.utils import build_mcp_tool, logger


@build_mcp_tool(
    name="diagnostics",
    description="""
    Provides comprehensive diagnostic information for Basic Memory including:
    - Version information from package
    - System details (Python, OS, architecture)
    - Current configuration dump
    - Project context
    
    This tool helps with troubleshooting installations and gathering system
    information for support requests.
    """,
)
async def diagnostics(project: Optional[str] = None) -> Dict[str, Any]:
    """
    Get comprehensive diagnostic information for Basic Memory.
    
    Args:
        project: Optional project name to get specific project context
        
    Returns:
        Dictionary containing diagnostic information
    """
    try:
        # Version information
        version_info = {
            "basic_memory_version": basic_memory.__version__,
            "api_version": basic_memory.__api_version__,
        }
        
        # System information
        system_info = {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
        }
        
        # Configuration information
        try:
            config = config_manager.load_config()
            config_info = {
                "config_file_path": str(config_manager.config_file),
                "config_exists": config_manager.config_file.exists(),
                "configuration": config.model_dump(),
            }
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            config_info = {
                "config_file_path": str(config_manager.config_file),
                "config_exists": config_manager.config_file.exists(),
                "error": f"Failed to load configuration: {str(e)}",
            }
        
        # Project context
        project_context = {}
        if project:
            try:
                project_name, project_path = config_manager.get_project(project)
                if project_name:
                    project_context = {
                        "requested_project": project,
                        "resolved_project_name": project_name,
                        "project_path": project_path,
                        "project_exists": Path(project_path).exists(),
                    }
                else:
                    project_context = {
                        "requested_project": project,
                        "error": f"Project '{project}' not found",
                    }
            except Exception as e:
                project_context = {
                    "requested_project": project,
                    "error": f"Error accessing project: {str(e)}",
                }
        else:
            try:
                default_project = config_manager.default_project
                default_path = config_manager.config.get_project_path()
                project_context = {
                    "default_project": default_project,
                    "default_project_path": str(default_path),
                    "default_project_exists": default_path.exists(),
                }
            except Exception as e:
                project_context = {
                    "error": f"Error accessing default project: {str(e)}",
                }
        
        # Compile diagnostic information
        diagnostic_info = {
            "version": version_info,
            "system": system_info,
            "configuration": config_info,
            "project_context": project_context,
        }
        
        return diagnostic_info
        
    except Exception as e:
        logger.error(f"Error generating diagnostics: {e}")
        return {
            "error": f"Failed to generate diagnostics: {str(e)}",
            "troubleshooting": {
                "suggestions": [
                    "Check if Basic Memory is properly installed",
                    "Verify configuration file permissions",
                    "Ensure project paths are accessible",
                    "Check system dependencies",
                ]
            },
        }