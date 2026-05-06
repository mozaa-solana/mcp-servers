"""Social-action verification endpoints (follow / retweet / comment)."""
from __future__ import annotations

from typing import Any

from ..config import Config
from ..http import request_json


async def verify_following(
    config: Config, *, source_user_id: str, target_user_id: str
) -> dict[str, Any]:
    """`GET /twitter/user/{source}/following/{target}`."""
    return await request_json(
        config,
        "GET",
        f"/twitter/user/{source_user_id}/following/{target_user_id}",
    )


async def verify_retweeted(
    config: Config, *, tweet_id: str, user_id: str
) -> dict[str, Any]:
    """`GET /twitter/tweets/{tweet_id}/retweeted_by/{user_id}`."""
    return await request_json(
        config, "GET", f"/twitter/tweets/{tweet_id}/retweeted_by/{user_id}"
    )


async def verify_commented(
    config: Config, *, tweet_id: str, user_id: str
) -> dict[str, Any]:
    """`GET /twitter/tweets/{tweet_id}/commented_by/{user_id}`."""
    return await request_json(
        config, "GET", f"/twitter/tweets/{tweet_id}/commented_by/{user_id}"
    )
