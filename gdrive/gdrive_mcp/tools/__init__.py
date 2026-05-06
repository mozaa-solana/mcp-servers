"""MCP tool wrappers — importing this package registers all 18 tools."""
from . import (  # noqa: F401  — side-effect: registers tools
    about,
    content,
    files,
    permissions,
    revisions,
)
from ._registry import mcp

__all__ = ["mcp"]
