# mcp-servers

MCP (Model Context Protocol) server adapters for the
[mozaa-solana/goclaw](https://github.com/mozaa-solana/goclaw) fork and
any other MCP-compatible host (Claude CLI, opencode-go, custom
integrations).

| | |
|---|---|
| **Servers** | 2 |
| **Total tools** | 72 |
| **Transport** | stdio (host spawns the process) |
| **Architecture** | Layered: `config / client / normalize / api / tools / tests` |
| **Tests** | 257 unit tests across all servers, 100% offline |

---

## Servers

| Dir | Purpose | Tools | Auth env |
|---|---|---|---|
| [socialdata/](./socialdata) | Twitter/X realtime via [socialdata.tools](https://socialdata.tools) | **30** — search, users, tweets, lists, communities, spaces, social actions | `SOCIALDATA_API_KEY` |
| [gdrive/](./gdrive) | Google Drive v3 + Sheets v4 (Service Account) | **42** — 21 Drive + 21 Sheets | `GOOGLE_APPLICATION_CREDENTIALS` |

Each server has its own `README.md` with full tool reference, response
shapes, and integration notes.

---

## Shared architecture

Both servers follow the same layered pattern. Adding a new server should
mirror this layout:

```
<server>/
├── server.py                  ← MCP stdio entrypoint
├── <server>_mcp/
│   ├── config.py              ← env → frozen Config (fail-fast)
│   ├── <client>.py            ← upstream SDK / HTTP wrapper + error mapping
│   ├── normalize.py           ← pure trim / clamp / paginated helpers
│   ├── safety.py              ← optional rails for write tools
│   ├── api/                   ← thin per-resource REST wrappers
│   └── tools/                 ← @mcp.tool() wrappers (LLM-facing)
│       ├── _registry.py       ← FastMCP singleton + lazy service getters
│       └── <one file per resource>
└── tests/                     ← unit tests, fully offline (mocked clients)
```

**Layering rules** (enforced by import direction):

| Layer | Knows about | Talks to |
|---|---|---|
| `tools/*` | MCP, normalize, safety, asyncio | `api/*` |
| `api/*` | upstream SDK verbs | upstream client |
| `<client>.py` | SDK auth / transport | network |
| `normalize.py` | pure data | nothing |
| `safety.py` | resource walks via service | nothing else |
| `config.py` | env vars | nothing |

Why the strict separation:
- **`api/*` is reusable** — any non-MCP caller can consume it.
- **`tools/*` carries the LLM contract** — docstrings, validation,
  response trimming, error messages.
- **Tests mock at the client boundary** — patch one factory, the whole
  suite stays offline. No real API key needed for `pytest`.

---

## Conventions

- **stdio first.** Goclaw spawns the process; no port to manage, smaller
  attack surface. Use HTTP only if upstream needs streaming and stdio
  buffering is a problem.
- **Auth via env vars.** Never hard-code keys in source. Goclaw's
  `POST /v1/mcp/servers` accepts an `env` map that's passed to the
  spawned process.
- **Trim payloads.** Tools return only the fields a research/writer
  agent needs (id, timestamp, text, URL, engagement counts, author
  handle). Raw upstream JSON pollutes the agent's context.
- **Structured tool names.** `<topic>_<verb>` — `twitter_search`,
  `drive_list_files`, `sheets_get_values`. Goclaw bridges them as
  `mcp__<server-slug>__<tool-name>` — keep both halves short.
- **Lazy config.** `Config.from_env()` only runs when the first tool is
  called. Importing the package never touches the environment — keeps
  tests clean.
- **Pagination uniformly.** List-returning tools wrap results in
  `{count, items[], next_cursor}`. Pass `next_cursor` back as `cursor=`
  to walk pages.

---

## Deploy

```bash
git clone https://github.com/mozaa-solana/mcp-servers.git ~/mcp-servers

# Install one server's deps
cd ~/mcp-servers/<server>
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

> **Locked-down distros** (Ubuntu 24.04+ without `python3-venv`):
> `pip3 install --user --break-system-packages -r requirements.txt`

Smoke test the stdio handshake (replace `<server>` and the env var):

```bash
SOCIALDATA_API_KEY=<key> \  # or GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
  .venv/bin/python ~/mcp-servers/<server>/server.py < <(cat <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
EOF
)
```

`tools/list` should return the expected tool count for that server.

---

## Goclaw integration

Goclaw stores MCP server configs in its DB and grants them per-agent.

```bash
ADMIN_AUTH=(-H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" -H "X-GoClaw-User-Id: admin")

# 1. Register
SERVER_ID=$(curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST http://localhost:18790/v1/mcp/servers \
  -d '{
    "name": "<server-slug>",
    "transport": "stdio",
    "command": "/home/goclaw/mcp-servers/<server>/.venv/bin/python",
    "args": ["/home/goclaw/mcp-servers/<server>/server.py"],
    "env": {"<AUTH_ENV>": "<value>"},
    "tool_prefix": "<topic>",
    "enabled": true
  }' | jq -r .id)

# 2. Grant to an agent
curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent" \
  -d "{\"agent_id\":\"<agent-uuid>\",\"enabled\":true}"

# 3. Verify discovery
curl -sS "${ADMIN_AUTH[@]}" "http://localhost:18790/v1/mcp/servers/$SERVER_ID/tools" | jq '.[].name'
```

See each server's README for its specific registration payload (env vars,
tool_prefix).

---

## Adding a new server

1. Create `<name>/` mirroring the layout in [Shared architecture](#shared-architecture).
2. Copy `pytest.ini` + `requirements.txt` patterns from an existing server.
3. Write tests at the same coverage tiers (config / client / api / tools / registry).
4. Update the [Servers](#servers) table above with dir / purpose / tool count / auth env.

Servers are written **host-agnostic** — there is nothing goclaw-specific
in the code. Any MCP-aware client can launch them.
