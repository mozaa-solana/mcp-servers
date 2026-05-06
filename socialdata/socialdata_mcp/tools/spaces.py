"""Twitter Spaces MCP tools."""
from __future__ import annotations

from typing import Any

from ..api import spaces as api
from ._registry import get_config, mcp


@mcp.tool()
async def twitter_space_info(space_id: str) -> dict[str, Any]:
    """Twitter Space metadata (host, participants, state).

    Endpoint: ``GET /twitter/space/{space_id}``.
    """
    return await api.get_space(get_config(), space_id=space_id)
