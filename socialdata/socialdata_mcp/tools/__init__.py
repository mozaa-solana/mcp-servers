"""MCP tool wrappers (LLM-facing).

Importing this package eagerly imports every submodule so each ``@mcp.tool()``
decorator runs and the FastMCP registry ends up populated.
"""
from . import (  # noqa: F401  — side-effect: registers tools
    communities,
    lists,
    search,
    social_actions,
    spaces,
    tweets,
    users,
)
from ._registry import mcp

__all__ = ["mcp"]
