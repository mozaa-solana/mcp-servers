"""Media upload — only piece still using the v1.1 endpoint as of 2026.

Result: ``{media_id}`` to be passed into ``x_post_tweet(media_ids=[...])``.
Up to 4 images, or 1 video / GIF per tweet."""
from __future__ import annotations

import asyncio
import os
from typing import Any

from ..api import media as api_media
from ._registry import get_client, handle_x_errors, mcp


@mcp.tool()
@handle_x_errors
async def x_upload_media(local_path: str) -> dict[str, Any]:
    """Upload an image / video / GIF from local disk. Returns ``{media_id}``.

    Use the returned id with ``x_post_tweet(media_ids=[id, ...])``.
    Free per X (no per-call cost), but a tweet posting it still incurs
    the standard write rate."""
    if not os.path.exists(local_path):
        return {"error": f"local file not found: {local_path}"}
    raw = await asyncio.to_thread(api_media.upload, get_client(), local_path)
    return raw
