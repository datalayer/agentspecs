# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Agentspecs
"""

from .composition.executor import CodeModeExecutor
from .discovery.codegen import PythonCodeGenerator
from .discovery.registry import ToolRegistry
from .types import (
    CodeModeConfig,
    MCPServerConfig,
    SearchResult,
    ServerInfo,
    ToolCallResult,
    ToolDefinition,
    ToolParameter,
)
from .proxy.mcp_client import MCPClient
from .proxy.meta_tools import MetaToolProvider

# Import skills functionality from agent_skills
from agent_skills import (
    Skill,
    SkillDirectory,
    SkillFile,
    SkillsManager,
    SimpleSkill,
    SimpleSkillsManager,
    SimpleSkillManager,  # Alias for backward compatibility
    SkillManager,  # Alias for backward compatibility
    setup_skills_directory,
    wait_for,
    retry,
    run_with_timeout,
    parallel,
    RateLimiter,
)

from .server import mcp as codemode_server, configure as configure_server
from .toolset import CodemodeToolset, PYDANTIC_AI_AVAILABLE

__all__ = [
    # Core components
    "ToolRegistry",
    "CodeModeExecutor",
    "PythonCodeGenerator",
    # Proxy
    "MCPClient",
    "MetaToolProvider",
    # Skills (from agent_skills)
    "Skill",
    "SkillsManager",
    "SimpleSkill",
    "SimpleSkillsManager",
    "SimpleSkillManager",  # Alias for backward compatibility
    "SkillManager",  # Alias for backward compatibility
    "SkillDirectory",
    "SkillFile",
    "setup_skills_directory",
    # Helpers (from agent_skills)
    "wait_for",
    "retry",
    "run_with_timeout",
    "parallel",
    "RateLimiter",
    # MCP Server
    "codemode_server",
    "configure_server",
    # Pydantic AI Toolset
    "CodemodeToolset",
    "PYDANTIC_AI_AVAILABLE",
    # Models
    "ToolDefinition",
    "ToolParameter",
    "ToolCallResult",
    "MCPServerConfig",
    "CodeModeConfig",
    "SearchResult",
    "ServerInfo",
]
