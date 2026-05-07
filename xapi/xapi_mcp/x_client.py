"""Tweepy v2 + v1.1 client wrapper with consistent error mapping.

Tweepy is sync; tools wrap calls in ``asyncio.to_thread()`` to keep the
MCP event loop responsive (matches the pattern used by gdrive_mcp).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import tweepy

from .config import Config


class XAPIError(RuntimeError):
    """Wraps a tweepy error with HTTP status + raw body for the LLM."""

    def __init__(self, message: str, status_code: int = 0, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def wrap_tweepy_error(exc: Exception) -> XAPIError:
    """Normalise tweepy.errors.* → XAPIError.

    tweepy raises Forbidden, Unauthorized, NotFound, TooManyRequests,
    BadRequest, TwitterServerError — all subclass HTTPException with
    ``response.status_code`` and ``api_messages``."""
    status = 0
    body: Any = None
    msg = str(exc)
    resp = getattr(exc, "response", None)
    if resp is not None:
        status = getattr(resp, "status_code", 0) or 0
        try:
            body = resp.json()
        except Exception:
            body = getattr(resp, "text", None)
    api_messages = getattr(exc, "api_messages", None)
    if api_messages:
        msg = "; ".join(str(m) for m in api_messages) or msg
    return XAPIError(msg, status_code=status, body=body)


@dataclass(frozen=True)
class XClient:
    """Bundles v2 (tweepy.Client) + v1.1 (tweepy.API) auth.

    v1.1 is needed for media upload — v2 still routes media through the
    legacy endpoint as of 2026."""
    v2: tweepy.Client
    v1: tweepy.API
    cfg: Config


def build_client(cfg: Config) -> XClient:
    v2 = tweepy.Client(
        consumer_key=cfg.api_key,
        consumer_secret=cfg.api_secret,
        access_token=cfg.access_token,
        access_token_secret=cfg.access_token_secret,
        wait_on_rate_limit=False,  # surface rate limits as errors, not silent sleeps
    )
    auth = tweepy.OAuth1UserHandler(
        cfg.api_key,
        cfg.api_secret,
        cfg.access_token,
        cfg.access_token_secret,
    )
    v1 = tweepy.API(auth)
    return XClient(v2=v2, v1=v1, cfg=cfg)
