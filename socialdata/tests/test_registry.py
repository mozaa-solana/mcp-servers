"""Tool registration smoke test — ensures every @mcp.tool() decorator ran."""
from __future__ import annotations

import pytest

import socialdata_mcp.tools  # noqa: F401  — triggers registration
from socialdata_mcp.tools._registry import mcp


EXPECTED_TOOLS = {
    "twitter_search",
    # users
    "twitter_user_info",
    "twitter_users_lookup",
    "twitter_user_extended_bio",
    "twitter_user_tweets",
    "twitter_user_mentions",
    "twitter_user_highlights",
    "twitter_user_followers",
    "twitter_user_followings",
    "twitter_user_similar",
    "twitter_user_affiliates",
    "twitter_user_lists",
    # tweets
    "twitter_tweet",
    "twitter_tweets_lookup",
    "twitter_tweet_comments",
    "twitter_tweet_quotes",
    "twitter_tweet_retweeters",
    "twitter_tweet_thread",
    "twitter_tweet_article",
    # lists
    "twitter_list_info",
    "twitter_list_members",
    "twitter_list_tweets",
    # communities
    "twitter_community_info",
    "twitter_community_tweets",
    "twitter_community_members",
    "twitter_community_search",
    # spaces
    "twitter_space_info",
    # social actions
    "twitter_verify_following",
    "twitter_verify_retweeted",
    "twitter_verify_commented",
}


@pytest.mark.asyncio
async def test_all_tools_registered():
    listed = await mcp.list_tools()
    names = {t.name for t in listed}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"missing tools: {sorted(missing)}"
