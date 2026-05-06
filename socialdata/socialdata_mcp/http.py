"""Thin HTTP layer around ``httpx.AsyncClient``.

All API calls go through :func:`request_json` so error mapping, headers, and
client construction live in exactly one place. Tests can patch
:func:`make_async_client` to inject mocks without monkey-patching every caller.
"""
from __future__ import annotations

from typing import Any, Mapping

import httpx

from .config import Config


class SocialDataAPIError(RuntimeError):
    """Raised when the upstream API returns a non-2xx response."""

    def __init__(self, status_code: int, body: Any, *, method: str, url: str) -> None:
        self.status_code = status_code
        self.body = body
        self.method = method
        self.url = url
        super().__init__(f"{method} {url} -> {status_code}: {body!r}")


def make_async_client(config: Config) -> httpx.AsyncClient:
    """Create a fresh AsyncClient pre-configured with auth + JSON headers."""
    return httpx.AsyncClient(
        timeout=config.timeout_seconds,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Accept": "application/json",
        },
    )


async def request_json(
    config: Config,
    method: str,
    path: str,
    *,
    params: Mapping[str, Any] | None = None,
    json: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a single request and return parsed JSON.

    `path` may be absolute (``http(s)://...``) or relative (``/twitter/...``).
    """
    url = path if path.startswith("http") else f"{config.base_url}{path}"
    async with make_async_client(config) as client:
        resp = await client.request(method, url, params=params, json=json)
    if resp.status_code >= 400:
        try:
            body: Any = resp.json()
        except ValueError:
            body = resp.text
        raise SocialDataAPIError(resp.status_code, body, method=method, url=url)
    return resp.json()
