"""Twitter Spaces endpoints."""
from __future__ import annotations

from typing import Any

from ..config import Config
from ..http import request_json


async def get_space(config: Config, *, space_id: str) -> dict[str, Any]:
    """`GET /twitter/space/{space_id}`."""
    return await request_json(config, "GET", f"/twitter/space/{space_id}")
