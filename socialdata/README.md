# socialdata MCP server

Realtime Twitter/X **read-only** data for MCP agents, powered by [socialdata.tools](https://socialdata.tools).

**30 tools** covering every public socialdata endpoint: search, users, tweets, lists, communities, spaces, social-action verification.

> **Why this exists.** Tavily/Exa lag X by 6–24h — they index articles *about* tweets, not the tweets themselves. When an agent needs primary-source realtime social data, it calls these tools instead of `web_search`.

For authenticated **write** access (post, like, DM, follow), use the [xapi](../xapi/) server instead.

---

## Quick start

```bash
cd ~/mcp-servers/socialdata
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
SOCIALDATA_API_KEY=<key> .venv/bin/python server.py
```

Verify the handshake:

```bash
SOCIALDATA_API_KEY=<key> .venv/bin/python server.py < <(cat <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
EOF
)
```

Expect 30 entries in the `tools/list` response.

> **Locked-down distros** (Ubuntu 24.04+ without `python3-venv`):
> `pip3 install --user --break-system-packages -r requirements.txt`

---

## Configuration

| Env var | Required | Default | Purpose |
|---|---|---|---|
| `SOCIALDATA_API_KEY` | Yes | — | From the [socialdata.tools dashboard](https://socialdata.tools/app/dashboard) |
| `SOCIALDATA_BASE_URL` | No | `https://api.socialdata.tools` | Override for staging / self-hosted gateway |
| `SOCIALDATA_TIMEOUT` | No | `30` | HTTP timeout (seconds) |

Config is loaded **lazily** — importing `socialdata_mcp` does not touch the environment. Validation runs on the first tool call.

---

## Tool reference

All paginated tools accept `cursor` and return `next_cursor`. Pass it back as `cursor=` to fetch the next page.

`max_results` is clamped per tool (typically 1–50 for tweets, 1–100 for user lists). Values above the cap silently clamp; values below 1 default to 1.

### Search

| Tool | Description |
|---|---|
| `twitter_search(query, sort, max_results, cursor)` | Operators: `from:`, `since:`, `until:`, `lang:`, `min_faves:`, `"phrase"`, `-exclude`. `sort=Latest` (default) or `Top`. |

### Users (11 tools)

| Tool | Description |
|---|---|
| `twitter_user_info(handle_or_id)` | Profile by `@handle` or numeric id |
| `twitter_users_lookup(ids[])` | Batch lookup, up to 100 ids |
| `twitter_user_extended_bio(screen_name)` | Full bio with links and entities |
| `twitter_user_tweets(user_id, include_replies, max_results, cursor)` | User's tweets (optionally with replies) |
| `twitter_user_mentions(screen_name, max_results, cursor)` | Tweets mentioning this user |
| `twitter_user_highlights(user_id, max_results, cursor)` | Highlighted/pinned tweets |
| `twitter_user_followers(user_id, verified_only, max_results, cursor)` | Followers list (or verified-only) |
| `twitter_user_followings(user_id, max_results, cursor)` | Accounts this user follows |
| `twitter_user_similar(user_id, max_results, cursor)` | Similar accounts |
| `twitter_user_affiliates(user_id, max_results, cursor)` | Affiliated accounts |
| `twitter_user_lists(user_id, max_results, cursor)` | Lists this user owns |

### Tweets (7 tools)

| Tool | Description |
|---|---|
| `twitter_tweet(tweet_id)` | Single tweet by id |
| `twitter_tweets_lookup(ids[])` | Batch lookup, up to 100 ids |
| `twitter_tweet_comments(tweet_id, max_results, cursor)` | Replies to a tweet |
| `twitter_tweet_quotes(tweet_id, max_results, cursor)` | Quote-tweets of a tweet |
| `twitter_tweet_retweeters(tweet_id, max_results, cursor)` | Who retweeted |
| `twitter_tweet_thread(thread_id, max_results, cursor)` | Full thread |
| `twitter_tweet_article(article_id)` | Long-form article content |

### Lists (3 tools)

| Tool | Description |
|---|---|
| `twitter_list_info(list_id)` | List metadata |
| `twitter_list_members(list_id, max_results, cursor)` | Members of a list |
| `twitter_list_tweets(list_id, max_results, cursor)` | Tweets from a list |

### Communities (4 tools)

| Tool | Description |
|---|---|
| `twitter_community_info(community_id)` | Community metadata |
| `twitter_community_tweets(community_id, sort, max_results, cursor)` | Posts in the community |
| `twitter_community_members(community_id, max_results, cursor)` | Members list |
| `twitter_community_search(community_id, query, sort, max_results, cursor)` | Search within a community |

### Spaces (1 tool)

| Tool | Description |
|---|---|
| `twitter_space_info(space_id)` | Space metadata |

### Social actions — verification (3 tools)

| Tool | Description |
|---|---|
| `twitter_verify_following(source, target)` | Does `source` follow `target`? |
| `twitter_verify_retweeted(tweet_id, user_id)` | Did `user_id` retweet this? |
| `twitter_verify_commented(tweet_id, user_id)` | Did `user_id` reply to this? |

---

## Response shapes

**Trimmed tweet** (returned by every tweet-yielding tool):

```json
{
  "id": "1729591119699124560",
  "created_at": "Wed Jan 15 12:00:00 +0000 2026",
  "text": "Hello world",
  "lang": "en",
  "retweet_count": 5, "favorite_count": 42,
  "reply_count": 3, "quote_count": 1, "view_count": 1000,
  "url": "https://x.com/elonmusk/status/1729591119699124560",
  "author": {
    "screen_name": "elonmusk", "name": "Elon Musk",
    "verified": true, "followers_count": 200000000
  },
  "is_retweet": false, "is_quote": false
}
```

**Trimmed user** (returned by every user-yielding tool):

```json
{
  "id": "44196397",
  "screen_name": "elonmusk",
  "name": "Elon Musk",
  "description": "...",
  "verified": true,
  "followers_count": 200000000,
  "friends_count": 500,
  "statuses_count": 50000,
  "created_at": "2009-06-02",
  "url": "https://x.com/elonmusk"
}
```

**Paginated envelope** (every list-returning tool):

```json
{
  "count": 20,
  "tweets": [],
  "next_cursor": "PAAAAPAtPBwcFoCAsr..."
}
```

When `next_cursor` is `null`, you've reached the end.

---

## Architecture

```
socialdata/
├── server.py                  MCP stdio entrypoint
├── socialdata_mcp/
│   ├── config.py              env → frozen Config dataclass (fail-fast)
│   ├── http.py                httpx wrapper + SocialDataAPIError
│   ├── normalize.py           pure trim_tweet / trim_user / clamp / paginated
│   ├── api/                   1 file per REST resource — returns raw JSON
│   │   ├── search.py    users.py     tweets.py
│   │   ├── lists.py     communities.py
│   │   └── spaces.py    social_actions.py
│   └── tools/                 1 file per resource — @mcp.tool() wrappers
│       ├── _registry.py       FastMCP singleton + lazy get_config()
│       ├── search.py    users.py     tweets.py
│       ├── lists.py     communities.py
│       └── spaces.py    social_actions.py
└── tests/                     96 unit tests, fully offline
```

Imports flow downward only:

| Layer | Responsibility | Depends on |
|---|---|---|
| `tools/*` | LLM-facing contract — docstrings, validation, trimming | `api/*`, normalize |
| `api/*` | REST endpoint wrappers | `http.py` |
| `http.py` | HTTP transport + error mapping | Network |
| `normalize.py` | Pure data transformations | Nothing |
| `config.py` | Environment variable loading | Nothing |

---

## Tests

```bash
.venv/bin/pytest -q                                        # 96 tests, ~0.4s
.venv/bin/pytest --cov=socialdata_mcp --cov-report=term-missing
```

Fully offline. `tests/conftest.py` patches `socialdata_mcp.http.request_json` with a scripted stub — no API key, no network, deterministic results.

---

## Goclaw integration

```bash
ADMIN_AUTH=(-H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" -H "X-GoClaw-User-Id: admin")

# Register
SERVER_ID=$(curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST http://localhost:18790/v1/mcp/servers \
  -d '{
    "name": "socialdata-twitter",
    "display_name": "SocialData (Twitter/X)",
    "transport": "stdio",
    "command": "/home/goclaw/mcp-servers/socialdata/.venv/bin/python",
    "args": ["/home/goclaw/mcp-servers/socialdata/server.py"],
    "env": {"SOCIALDATA_API_KEY": "<your-key>"},
    "tool_prefix": "twitter",
    "timeout_sec": 30,
    "enabled": true
  }' | jq -r .id)

# Grant to an agent
curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent" \
  -d "{\"agent_id\":\"<agent-uuid>\",\"enabled\":true}"

# Verify discovery — should list all 30 twitter_* tools
curl -sS "${ADMIN_AUTH[@]}" \
  "http://localhost:18790/v1/mcp/servers/$SERVER_ID/tools" | jq '.[].name'
```

---

## Cost notes

socialdata.tools meters **per request**, not per result.

- Trim `max_results` to the smallest useful value
- Use search operators (`since:`, `min_faves:`, `lang:`) to filter at source
- Paginate only when you've exhausted the first page's signal
- Cache aggressively at the agent layer — most research turns reuse the same result set across multiple draft revisions

For freshness verification, combine `twitter_search` (primary tweet) with `web_search` (corroborating coverage) — two independent ingest paths reduce false-positive "this is fresh" calls on republished content.
