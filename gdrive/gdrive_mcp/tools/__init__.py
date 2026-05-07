"""MCP tool wrappers — importing this package registers all tools."""
from . import (  # noqa: F401  — side-effect: registers tools
    about,
    content,
    docs,
    files,
    permissions,
    revisions,
    sheets,
)
from ._registry import mcp

__all__ = ["mcp"]
