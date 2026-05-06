# socialdata-mcp

Realtime Twitter/X data for MCP-aware agents (Claude CLI, opencode-go,
goclaw bridge consumers), via the [socialdata.tools](https://socialdata.tools)
REST API.

**Why this exists.** Tavily/Exa lag X by 6–24h — they index *articles
about* tweets, not the tweets themselves. When an agent needs primary-source
realtime social data, it calls these tools instead of `web_search`.

**30 tools** covering every public socialdata endpoint: search, users,
tweets, lists, communities, spaces, social-action verification.

---

## Table of contents

- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Tool reference](#tool-reference)
- [Response shapes](#response-shapes)
- [Tests](#tests)
- [Goclaw integration](#goclaw-integration)
- [Cost notes](#cost-notes)

---

## Quick start

```bash
# 1. Install
git clone https://github.com/mozaa-solana/mcp-servers.git ~/mcp-servers
cd ~/mcp-servers/socialdata
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Run
SOCIALDATA_API_KEY=<your-key> .venv/bin/python server.py
```

Smoke test the stdio handshake:

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

| Env var | Required | Default | Notes |
|---|---|---|---|
| `SOCIALDATA_API_KEY` | ✅ | — | From the [socialdata.tools dashboard](https://socialdata.tools/app/dashboard) |
| `SOCIALDATA_BASE_URL` | — | `https://api.socialdata.tools` | Override for staging / self-hosted gateway |
| `SOCIALDATA_TIMEOUT` | — | `30` | HTTP timeout (seconds) |

Config is loaded **lazily** — importing `socialdata_mcp` does not touch the
environment. Validation runs the first time a tool is called (or via
`server.py main()` at startup).

---

## Architecture

```
socialdata/
├── server.py                  ← MCP stdio entrypoint
├── socialdata_mcp/
│   ├── config.py              ← env → frozen Config dataclass (fail-fast)
│   ├── http.py                ← httpx wrapper + SocialDataAPIError
│   ├── normalize.py           ← pure trim_tweet / trim_user / clamp / paginated
│   ├── api/                   ← 1 file per REST resource — returns raw JSON
│   │   ├── search.py    users.py     tweets.py
│   │   ├── lists.py     communities.py
│   │   └── spaces.py    social_actions.py
│   └── tools/                 ← 1 file per resource — @mcp.tool() wrappers
│       ├── _registry.py       ← FastMCP singleton + lazy get_config()
│       ├── search.py    users.py     tweets.py
│       ├── lists.py     communities.py
│       └── spaces.py    social_actions.py
└── tests/                     ← 96 unit tests, fully offline
```

**Layering rules** (enforced by import direction):

| Layer | Knows about | Talks to |
|---|---|---|
| `tools/*` | MCP, normalize | `api/*` |
| `api/*` | REST shape | `http.py` |
| `http.py` | httpx, errors | network |
| `normalize.py` | pure data | nothing |
| `config.py` | env vars | nothing |

Tests patch `request_json` once in `conftest.py` → entire suite stays
offline, no API key needed.

---

## Tool reference

All paginated tools accept `cursor` and return `next_cursor`. Pass
`next_cursor` back as `cursor=` to walk the next page.

`max_results` is clamped per tool (typically 1–50 for tweets, 1–100 for
user lists). Set higher than the cap and you get the cap; set lower than
1 and you get 1.

### 🔍 Search (1)

| Tool | Endpoint | Notes |
|---|---|---|
| `twitter_search(query, sort, max_results, cursor)` | `GET /twitter/search` | Operators: `from:`, `since:`, `until:`, `lang:`, `min_faves:`, `"phrase"`, `-exclude`. `sort=Latest` (default) or `Top`. |

### 👤 Users (11)

| Tool | Endpoint |
|---|---|
| `twitter_user_info(handle_or_id)` | `GET /twitter/user/{handle_or_id}` |
| `twitter_users_lookup(ids[])` ≤100 | `POST /twitter/users-by-id` |
| `twitter_user_extended_bio(screen_name)` | `GET /twitter/user/{u}/extended-bio` |
| `twitter_user_tweets(user_id, include_replies, …)` | `GET /twitter/user/{id}/tweets[-and-replies]` |
| `twitter_user_mentions(screen_name, …)` | `GET /twitter/user/{u}/mentions` |
| `twitter_user_highlights(user_id, …)` | `GET /twitter/user/{id}/highlights` |
| `twitter_user_followers(user_id, verified_only, …)` | `GET /twitter/followers/list` *or* `…/verified-followers` |
| `twitter_user_followings(user_id, …)` | `GET /twitter/friends/list` |
| `twitter_user_similar(user_id, …)` | `GET /twitter/user/{id}/similar` |
| `twitter_user_affiliates(user_id, …)` | `GET /twitter/user/{id}/affiliates` |
| `twitter_user_lists(user_id, …)` | `GET /twitter/user/{id}/lists` |

### 🐦 Tweets (7)

| Tool | Endpoint |
|---|---|
| `twitter_tweet(tweet_id)` | `GET /twitter/tweets/{id}` |
| `twitter_tweets_lookup(ids[])` ≤100 | `POST /twitter/tweets-by-ids` |
| `twitter_tweet_comments(tweet_id, …)` | `GET /twitter/tweets/{id}/comments` |
| `twitter_tweet_quotes(tweet_id, …)` | `GET /twitter/tweets/{id}/quotes` |
| `twitter_tweet_retweeters(tweet_id, …)` | `GET /twitter/tweets/{id}/retweeted_by` |
| `twitter_tweet_thread(thread_id, …)` | `GET /twitter/thread/{id}` |
| `twitter_tweet_article(article_id)` | `GET /twitter/article/{id}` |

### 📋 Lists (3)

| Tool | Endpoint |
|---|---|
| `twitter_list_info(list_id)` | `GET /twitter/lists/show` |
| `twitter_list_members(list_id, …)` | `GET /twitter/lists/members` |
| `twitter_list_tweets(list_id, …)` | `GET /twitter/list/{id}/tweets` |

### 🏘️ Communities (4)

| Tool | Endpoint |
|---|---|
| `twitter_community_info(community_id)` | `GET /twitter/community/{id}` |
| `twitter_community_tweets(community_id, sort, …)` | `GET /twitter/community/{id}/tweets` |
| `twitter_community_members(community_id, …)` | `GET /twitter/community/{id}/members` |
| `twitter_community_search(community_id, query, sort, …)` | `GET /twitter/community/{id}/search` |

### 🎙️ Spaces (1)

| Tool | Endpoint |
|---|---|
| `twitter_space_info(space_id)` | `GET /twitter/space/{id}` |

### ✅ Social actions — verification (3)

| Tool | Endpoint |
|---|---|
| `twitter_verify_following(source, target)` | `GET /twitter/user/{s}/following/{t}` |
| `twitter_verify_retweeted(tweet_id, user_id)` | `GET /twitter/tweets/{t}/retweeted_by/{u}` |
| `twitter_verify_commented(tweet_id, user_id)` | `GET /twitter/tweets/{t}/commented_by/{u}` |

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
  "tweets": [ /* …trimmed tweets… */ ],
  "next_cursor": "PAAAAPAtPBwcFoCAsr..."
}
```
Pass `next_cursor` back as `cursor=` to fetch the next page. When
`next_cursor` is `null`, you've reached the end.

Raw socialdata payloads are dropped — agents get only the fields that
matter for research/content generation.

---

## Tests

```bash
.venv/bin/pytest -q          # 96 tests, ~0.4s
.venv/bin/pytest --cov=socialdata_mcp --cov-report=term-missing
```

The full suite is offline. `tests/conftest.py` patches
`socialdata_mcp.http.request_json` with a scripted stub, so:
- no `SOCIALDATA_API_KEY` needed
- no network
- tests are deterministic and fast

Coverage:

| Layer | What's tested |
|---|---|
| `config.py` | Env loading, validation, fail-fast |
| `http.py` | URL building, JSON body, error mapping (4xx/5xx, non-JSON bodies) |
| `normalize.py` | Field fall-backs, `clamp`, `extract_items`, pagination envelope |
| `api/*` | Endpoint paths, query/JSON params, cursor passing |
| `tools/*` | Normalization, clamping, input validation, error responses |
| `_registry` | All 30 tools registered via `mcp.list_tools()` |

---

## Goclaw integration

Goclaw stores MCP servers in its DB and grants them per-agent.

```bash
ADMIN_AUTH=(-H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" -H "X-GoClaw-User-Id: admin")

# 1. Register the server
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

# 2. Grant to an agent
curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent" \
  -d "{\"agent_id\":\"<agent-uuid>\",\"enabled\":true}"

# 3. Reload (no full restart needed)
curl -sS "${ADMIN_AUTH[@]}" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/reconnect"

# 4. Verify discovery — should list all 30 twitter_* tools
curl -sS "${ADMIN_AUTH[@]}" \
  "http://localhost:18790/v1/mcp/servers/$SERVER_ID/tools" | jq '.[].name'
```

Only granted agents see the tools in their MCP discovery.

---

## Cost notes

socialdata.tools meters **per request**, not per result.

- Trim `max_results` to the smallest useful value
- Use search operators (`since:`, `min_faves:`, `lang:`) to filter at source
- Paginate only when you've exhausted the first page's signal
- Cache aggressively at the agent layer — most research turns reuse the
  same result set across multiple draft revisions

For freshness verification, combine `twitter_search` (primary tweet) with
`web_search` (corroborating coverage) — two independent ingest paths
reduce false-positive "this is fresh" calls on republished content.
