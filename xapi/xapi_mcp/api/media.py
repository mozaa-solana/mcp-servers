"""Media upload — uses v1.1 endpoint (X has no v2 media upload yet)."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def upload(client: XClient, local_path: str) -> dict[str, Any]:
    media = client.v1.media_upload(filename=local_path)
    return {
        "media_id": getattr(media, "media_id_string", str(media.media_id)),
        "size": getattr(media, "size", None),
        "type": getattr(media, "type", None),
    }
