# xapi MCP server

Twitter / X **official API** adapter for authenticated write, engagement, DMs, profile, and analytics.

**37 tools** over [X API v2](https://docs.x.com/) with OAuth 1.0a User Context. Designed for **single-user** operation: one process holds one user's access token. Multi-user is achieved by registering N MCP server configs in goclaw, each with its own env (Option 1).

> **This is the write path.** For realtime read-only Twitter data, use the [socialdata](../socialdata/) server instead (cheaper, no quota).

---

## Cost model — read this first

X moved to **pay-per-use** in Feb 2026. Every tool call costs real money. Approximate rates (USD, post-2026-04-20):

| Action | Cost |
|---|---|
| Read your own data (`x_get_me`, `x_get_my_recent_posts`) | **$0.001** / item |
| Read someone else's tweet/user (`x_get_tweet`, `x_get_user`) | $0.005 |
| Post / like / retweet / follow / block (no URL) | $0.015 |
| Post **containing a URL** | **$0.20** (13x link tax) |
| Send DM | $0.015 |
| Hard cap: 2M reads / month or pay $42K/mo Enterprise | — |

Every tool returns `estimated_cost_usd` in its response. Set `X_BUDGET_USD_PER_DAY=N` to fail-fast before exceeding a daily cap.

Pricing source: <https://docs.x.com/x-api/getting-started/pricing>

---

## Quick start

```bash
cd ~/mcp-servers/xapi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Verify the handshake (env values can be fake — handshake doesn't hit X):

```bash
X_API_KEY=fake X_API_SECRET=fake \
X_ACCESS_TOKEN=fake X_ACCESS_TOKEN_SECRET=fake \
.venv/bin/python server.py < <(cat <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
EOF
)
```

Expect 37 tools in the `tools/list` response.

> **Locked-down distros** (Ubuntu 24.04+ without `python3-venv`):
> `pip3 install --user --break-system-packages -r requirements.txt`

---

## Configuration

| Env var | Required | Default | Purpose |
|---|---|---|---|
| `X_API_KEY` | Yes | — | App consumer key |
| `X_API_SECRET` | Yes | — | App consumer secret |
| `X_ACCESS_TOKEN` | Yes | — | User access token |
| `X_ACCESS_TOKEN_SECRET` | Yes | — | User access token secret |
| `X_HANDLE` | No | — | Cosmetic label (e.g. `@alice`). Returned by `x_budget_status`. |
| `X_BUDGET_USD_PER_DAY` | No | — | Daily USD cap. Calls beyond it return `{"violation": "budget"}`. |
| `X_DRY_RUN` | No | — | `1` / `true` — write tools return shape without hitting the API. |

Config is loaded **lazily** on the first tool call.

---

## Auth — generate OAuth 1.0a tokens

You only post on behalf of users who have authorized your developer app. For Option 1 (single user = yourself), the dashboard gives you the 4 credentials directly:

1. <https://developer.x.com/en/portal/dashboard> → your app
2. **Keys & Tokens** tab
3. Copy: `API Key`, `API Key Secret`
4. Click **Generate** under "Access Token and Secret" → copy `Access Token`, `Access Token Secret`
5. App permissions must be **Read + Write** (or **Read + Write + DM** if you need `x_send_dm`)

> Posting on behalf of **other** users requires 3-legged OAuth + callback server — out of scope for v1. Either have each user generate their own tokens, or build a multi-user token store (Phase 2).

---

## Tool reference

### Owned reads — $0.001

| Tool | Description |
|---|---|
| `x_get_me` | Authenticated user's profile |
| `x_get_my_recent_posts(max_results=10)` | Your own recent tweets |

### Posts

| Tool | Description |
|---|---|
| `x_post_tweet(text, reply_to_tweet_id?, quote_tweet_id?, media_ids?)` | Publish. URLs trigger 13x cost. |
| `x_delete_tweet(tweet_id)` | Delete a tweet you authored. Cannot be undone. |
| `x_get_tweet(tweet_id)` | Lookup a single tweet (any author). |
| `x_pin_tweet(tweet_id)` | Pin to your profile. |
| `x_unpin_tweet(tweet_id)` | Unpin from your profile. |

### Engagement

| Tool | Description |
|---|---|
| `x_like_tweet(tweet_id)` | Like. |
| `x_unlike_tweet(tweet_id)` | Unlike. |
| `x_retweet(tweet_id)` | Retweet. |
| `x_unretweet(tweet_id)` | Undo retweet. |

### Users

| Tool | Description |
|---|---|
| `x_get_user(handle_or_id)` | Lookup by `@handle` or numeric id. |
| `x_follow_user(handle_or_id)` | Follow. |
| `x_unfollow_user(handle_or_id)` | Unfollow. |
| `x_block_user(handle_or_id)` | Block. |
| `x_unblock_user(handle_or_id)` | Unblock. |
| `x_mute_user(handle_or_id)` | Mute. |
| `x_unmute_user(handle_or_id)` | Unmute. |
| `x_get_my_followers(max=100, cursor?)` | Your followers — owned tier. |
| `x_get_my_following(max=100, cursor?)` | Accounts you follow — owned tier. |

### DMs

| Tool | Description |
|---|---|
| `x_send_dm(recipient_handle_or_id, text)` | 1:1 DM. Recipient must follow you. |

### Media

| Tool | Description |
|---|---|
| `x_upload_media(local_path)` | Upload image/video/GIF (v1.1 endpoint). Returns `media_id` for `x_post_tweet(media_ids=[...])`. |

### Profile (v1.1, free)

| Tool | Description |
|---|---|
| `x_update_profile(name?, description?, location?, url?)` | Edit display name / bio / location / website. |
| `x_update_profile_image(local_path)` | Replace avatar (PNG/JPG/GIF, 700KB max). |

### Bookmarks

| Tool | Description |
|---|---|
| `x_bookmark_tweet(tweet_id)` | Add to bookmarks. |
| `x_remove_bookmark(tweet_id)` | Remove from bookmarks. |
| `x_get_my_bookmarks(max=10)` | List bookmarks — owned tier. |

### Research / discovery

| Tool | Description |
|---|---|
| `x_search_recent_tweets(query, max=10, cursor?)` | Last-7-day search with X operators. |
| `x_get_user_recent_posts(handle_or_id, max=10)` | Another user's recent tweets. |
| `x_get_trending_topics(woeid=1)` | Trending topics by location (v1.1). |
| `x_get_user_followers(handle_or_id, max=100, cursor?)` | Other user's followers — standard tier. |

> **Cost note**: Search and standard reads are $0.005/result. For bulk research, prefer the [socialdata](../socialdata/) server (free scraping).

### Analytics — track post performance

| Tool | Description |
|---|---|
| `x_get_tweet_metrics(tweet_id)` | Public + non-public + organic metrics (impressions, clicks, video views — own tweets only). |
| `x_get_liking_users(tweet_id, max=100)` | Who liked the tweet. |
| `x_get_retweeters(tweet_id, max=100)` | Who retweeted. |
| `x_get_quote_tweets(tweet_id, max=10)` | Quote-tweets of this post. |
| `x_get_replies(tweet_id, max=10)` | Replies in same conversation (search-based, last 7 days). |

### Diagnostics

| Tool | Description |
|---|---|
| `x_budget_status` | Today's spend / cap / remaining. In-memory, resets at UTC midnight or on process restart. |

---

## Multi-user via per-config grant (Option 1)

For each X user you want to post as, register a separate server config:

```bash
ADMIN_AUTH=(-H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" -H "X-GoClaw-User-Id: admin")

# Register one config per user — env vars carry that user's token
SERVER_ID=$(curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST http://localhost:18790/v1/mcp/servers \
  -d '{
    "name": "xapi-alice",
    "transport": "stdio",
    "command": "/home/goclaw/mcp-servers/xapi/.venv/bin/python",
    "args": ["/home/goclaw/mcp-servers/xapi/server.py"],
    "env": {
      "X_API_KEY": "<app-key>",
      "X_API_SECRET": "<app-secret>",
      "X_ACCESS_TOKEN": "<alice-access-token>",
      "X_ACCESS_TOKEN_SECRET": "<alice-access-token-secret>",
      "X_HANDLE": "@alice",
      "X_BUDGET_USD_PER_DAY": "5.00"
    },
    "tool_prefix": "x",
    "enabled": true
  }' | jq -r .id)

# Grant to agents that should post as Alice
curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent" \
  -d "{\"agent_id\":\"<agent-uuid>\",\"enabled\":true}"
```

Repeat with `xapi-bob`, `xapi-charlie`, etc. Each runs its own process with isolated tokens. Cross-user posting is **physically impossible** — the agent only sees the bound config's tools.

Trade-off: ~30–50MB RAM idle per process. Fine up to ~20–50 users. Beyond that, switch to a token-store / `as_user` model (Phase 2).

---

## Safety rails

- **Pay-per-use guard**: `X_BUDGET_USD_PER_DAY` enforced *before* every API call. Blocked calls return `{"violation": "budget"}`.
- **Dry-run mode**: `X_DRY_RUN=1` makes every write tool return the shape it *would* send without hitting X.
- **Empty-string guard**: `x_post_tweet` and `x_send_dm` reject blank text before spending the request.
- **Username sanitisation**: strips `@`, accepts numeric ids untouched.
- **No silent rate-limit waits**: `wait_on_rate_limit=False` — 429s surface as `{"status_code": 429}` so the agent can back off.

---

## What's NOT included (yet)

| Missing | Why | Workaround |
|---|---|---|
| OAuth 2.0 PKCE flow | Needs HTTP callback server — out of scope for stdio MCP | Use OAuth 1.0a tokens from dashboard |
| Multi-user token store | Option 1 covers up to 50 users; refactor when needed | Register N server configs |
| Streaming endpoints | MCP is request-response; streaming needs SSE | Out of scope |
| Lists, Spaces, Trends (write) | Niche; can be added later if needed | — |
| Polls in tweets | Not exposed by tweepy.Client | Wait for tweepy update |

---

## Architecture

```
xapi/
├── server.py              MCP stdio entrypoint
├── xapi_mcp/
│   ├── config.py          env → frozen Config
│   ├── x_client.py        tweepy v2 + v1 wrapper, error mapping
│   ├── cost.py            per-operation USD estimates
│   ├── budget.py          in-memory daily spend tracker
│   ├── normalize.py       trim_tweet, trim_user, paginated
│   ├── api/               thin tweepy verb wrappers
│   │   ├── posts.py       create / delete / like / retweet / get_tweet
│   │   ├── users.py       get / follow / block (and reverses)
│   │   ├── me.py          owned-read endpoints
│   │   ├── dms.py         create_direct_message
│   │   └── media.py       v1.1 media_upload
│   └── tools/             @mcp.tool() wrappers (LLM-facing)
│       ├── _registry.py   FastMCP singleton + handle_x_errors
│       ├── me.py          x_get_me, x_get_my_recent_posts
│       ├── posts.py       x_post_tweet, x_like_tweet, etc.
│       ├── users.py       x_get_user, x_follow_user, etc.
│       ├── dms.py         x_send_dm
│       ├── media.py       x_upload_media
│       └── budget.py      x_budget_status
└── tests/                 93 offline unit tests (no real X API)
```

Imports flow downward only:

| Layer | Responsibility | Depends on |
|---|---|---|
| `tools/*` | LLM-facing contract — docstrings, validation, trimming, cost | `api/*`, normalize, budget |
| `api/*` | tweepy verb wrappers | `x_client.py` |
| `x_client.py` | SDK auth / transport / error mapping | Network |
| `cost.py` | Per-operation USD estimates | Nothing |
| `budget.py` | In-memory daily spend tracker | `cost.py` |
| `normalize.py` | Pure data transformations | Nothing |
| `config.py` | Environment variable loading | Nothing |

---

## Tests

```bash
PYTHONPATH=. .venv/bin/pytest -q       # 93 tests, < 1s
```

Fully offline. `conftest.py` patches the tweepy client factory — no real tokens needed.
