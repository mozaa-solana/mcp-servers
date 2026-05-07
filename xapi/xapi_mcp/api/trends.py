"""Trending topics — v1.1 endpoint via tweepy.API.

Note: ``trends/place`` access tier has shifted over time. If X returns
a 403, the calling user/app likely needs Pro tier — the tool layer
surfaces that as a regular error dict."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def get_place_trends(client: XClient, woeid: int = 1) -> list[dict[str, Any]]:
    """``woeid=1`` is worldwide. Country / city ids: see Yahoo WOEID lookup."""
    raw = client.v1.get_place_trends(woeid)
    if not raw:
        return []
    first = raw[0]
    if isinstance(first, dict):
        return list(first.get("trends", []))
    trends = getattr(first, "trends", None)
    if trends is None:
        return []
    return [getattr(t, "_json", t) if not isinstance(t, dict) else t for t in trends]
