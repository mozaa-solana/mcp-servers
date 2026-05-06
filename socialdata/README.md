# socialdata — Twitter / X realtime MCP server

stdio MCP server wrapping the [socialdata.tools](https://socialdata.tools)
REST API. Gives MCP-aware agents (Claude CLI, opencode-go, goclaw bridge
consumers) live access to X / Twitter data that mainstream web search
engines (Tavily, Exa) miss or lag by 6–24h.

## Tools exposed

| Tool | Purpose |
|---|---|
| `twitter_search` | Full-text recent tweet search. Operators: `from:`, `since:`, `until:`, `lang:`, `min_faves:`, `"phrase"`, `-exclude`. `sort=Latest\|Top`, `max_results` 1–50. |
| `twitter_user_tweets` | Most recent tweets for a handle (no `@`). |
| `twitter_user_info` | Profile lookup by handle. |
| `twitter_tweet` | Fetch a single tweet by numeric id. |

Tweets are trimmed to the fields a research/content agent actually
needs: `id`, `created_at` (UTC), `text`, `lang`, engagement counts
(`retweet`, `favorite`, `reply`, `quote`, `view`), canonical x.com
permalink `url`, `author` (screen_name / name / verified /
followers_count), `is_retweet`, `is_quote`. Raw socialdata payloads
are dropped.

## Install

```bash
git clone https://github.com/mozaa-solana/mcp-servers.git ~/mcp-servers
cd ~/mcp-servers/socialdata

# System Python (Ubuntu 24.04+ blocks pip in system site-packages —
# `--user --break-system-packages` is the documented escape hatch when
# python3-venv is unavailable).
pip3 install --user --break-system-packages -r requirements.txt
```

Or with a venv (preferred when python3-venv is installed):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Goclaw command becomes: /home/<user>/mcp-servers/socialdata/.venv/bin/python
# Args:                  /home/<user>/mcp-servers/socialdata/server.py
```

## Configuration

| Env var | Required | Default | Notes |
|---|---|---|---|
| `SOCIALDATA_API_KEY` | yes | — | Get from socialdata.tools dashboard |
| `SOCIALDATA_BASE_URL` | no | `https://api.socialdata.tools` | Override for self-hosted gateway / staging |
| `SOCIALDATA_TIMEOUT` | no | `30` (seconds) | HTTP timeout for upstream calls |

## Local smoke test

```bash
SOCIALDATA_API_KEY=<key> \
  python3 -c '
import asyncio, importlib.util
spec = importlib.util.spec_from_file_location("s", "./server.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import httpx
async def go():
    async with httpx.AsyncClient(timeout=20, headers={"Authorization": f"Bearer {m.API_KEY}"}) as c:
        r = await c.get(f"{m.BASE_URL}/twitter/search", params={"query":"Solana","type":"Latest"})
        print(r.status_code, len((r.json().get("tweets") or [])), "tweets")
asyncio.run(go())
'
```

Or via the MCP stdio handshake:

```bash
SOCIALDATA_API_KEY=<key> python3 server.py < <(cat <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
EOF
)
```

You should see four tools listed in the response.

## Register with goclaw

Goclaw stores MCP servers in its DB and grants them per-agent. Use the
admin HTTP API (auth: `GOCLAW_GATEWAY_TOKEN` as bearer + `X-GoClaw-User-Id: admin`).

### 1. Create the server

```bash
curl -sS -X POST http://localhost:18790/v1/mcp/servers \
  -H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" \
  -H "X-GoClaw-User-Id: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "socialdata-twitter",
    "display_name": "SocialData (Twitter/X)",
    "transport": "stdio",
    "command": "python3",
    "args": ["/home/goclaw/mcp-servers/socialdata/server.py"],
    "env": {"SOCIALDATA_API_KEY": "<your-key>"},
    "tool_prefix": "twitter",
    "timeout_sec": 30,
    "enabled": true
  }'
```

Response includes the new server `id` (a UUID). Save it for step 2.

### 2. Grant to specific agents

```bash
SERVER_ID=<uuid-from-step-1>
AGENT_ID=<agent-uuid>
curl -sS -X POST http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent \
  -H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" \
  -H "X-GoClaw-User-Id: admin" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":\"$AGENT_ID\",\"enabled\":true}"
```

Only granted agents see the tools in their MCP discovery. Other agents
in the same tenant don't.

### 3. Reload (no full restart needed)

```bash
curl -sS -X POST http://localhost:18790/v1/mcp/servers/$SERVER_ID/reconnect \
  -H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" \
  -H "X-GoClaw-User-Id: admin"
```

Goclaw spawns the process, runs `tools/list`, and caches the four
twitter tools. Granted agents pick them up on their next session start.

### 4. Verify discovery

```bash
curl -sS http://localhost:18790/v1/mcp/servers/$SERVER_ID/tools \
  -H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" \
  -H "X-GoClaw-User-Id: admin"
```

Should return `twitter_search`, `twitter_user_tweets`, `twitter_user_info`,
`twitter_tweet`.

## Agent usage notes (research workflow)

Tavily and Exa lag for X content by 6–24h — they index news articles
ABOUT tweets, not tweets directly. When an agent needs primary-source
realtime tweet data, it calls `twitter_search` instead of `web_search`.
Prefer `sort=Latest` for breaking news (chronological), `Top` for
distilling engagement-weighted commentary.

For freshness verification, agents combine `twitter_search` (for the
primary tweet) with `web_search` (for corroborating news coverage) —
two independent ingest paths reduce false-positive "this is fresh"
calls on republished tweets.

## API costs

socialdata.tools meters per-request. Trim `max_results`, lean on
`since:` operators, and cache aggressively at the agent level — most
research turns reuse the same result set across multiple draft revisions.
