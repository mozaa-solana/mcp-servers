# mcp-servers

Production-ready [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) servers for [goclaw](https://github.com/mozaa-solana/goclaw) and any MCP-compatible host.

Three servers. 129 tools. Zero external dependencies at runtime beyond each server's SDK.

| Server | Purpose | Tools | Auth |
|---|---|---|---|
| [socialdata](./socialdata) | Twitter/X realtime **read** via [socialdata.tools](https://socialdata.tools) | 30 | `SOCIALDATA_API_KEY` |
| [gdrive](./gdrive) | Google Drive v3 + Sheets v4 + Docs v1 (Service Account) | 62 | `GOOGLE_APPLICATION_CREDENTIALS` |
| [xapi](./xapi) | Twitter/X **official** API — write, engagement, DMs, profile, analytics | 37 | `X_API_KEY` + 3 OAuth1 tokens |

Each server has its own README with full tool reference, response shapes, and integration notes.

---

## Quick start

```bash
git clone https://github.com/mozaa-solana/mcp-servers.git ~/mcp-servers
cd ~/mcp-servers/<server>           # pick: socialdata | gdrive | xapi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run a server (replace env vars for your chosen server):

```bash
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

> **Locked-down distros** (Ubuntu 24.04+ without `python3-venv`):
> `pip3 install --user --break-system-packages -r requirements.txt`

---

## Architecture

Every server follows the same layered pattern. Adding a new server mirrors this layout:

```
<server>/
├── server.py                  MCP stdio entrypoint
├── <server>_mcp/
│   ├── config.py              env → frozen Config (fail-fast)
│   ├── <client>.py            upstream SDK / HTTP wrapper + error mapping
│   ├── normalize.py           pure trim / clamp / paginated helpers
│   ├── safety.py              optional rails for write tools
│   ├── api/                   thin per-resource REST wrappers
│   └── tools/                 @mcp.tool() wrappers (LLM-facing)
│       ├── _registry.py       FastMCP singleton + lazy service getters
│       └── <one file per resource>
└── tests/                     unit tests, fully offline (mocked clients)
```

### Layering rules

Imports flow downward only. No upward or circular dependencies.

| Layer | Responsibility | Depends on |
|---|---|---|
| `tools/*` | LLM-facing contract — docstrings, validation, response trimming | `api/*`, normalize, safety |
| `api/*` | Upstream SDK verb wrappers | `<client>.py` |
| `<client>.py` | SDK auth / transport / error mapping | Network |
| `normalize.py` | Pure data transformations | Nothing |
| `safety.py` | Resource-boundary enforcement | Service (read-only) |
| `config.py` | Environment variable loading | Nothing |

**Why this separation matters:**

- **`api/*` is reusable** — any non-MCP caller can consume it directly.
- **`tools/*` owns the LLM contract** — docstrings, validation, trimming, and error messages live here.
- **Tests mock at the client boundary** — patch one factory, the whole suite stays offline. No real API key needed for `pytest`.

---

## Conventions

- **stdio first.** No port to manage, smaller attack surface. Use HTTP only if upstream needs streaming and stdio buffering becomes a problem.
- **Auth via env vars.** Never hard-code keys. Goclaw's `POST /v1/mcp/servers` accepts an `env` map passed to the spawned process.
- **Trim payloads.** Tools return only the fields an agent needs (id, timestamp, text, URL, engagement counts, author handle). Raw upstream JSON pollutes context.
- **Structured tool names.** `<topic>_<verb>` — `twitter_search`, `drive_list_files`, `sheets_get_values`. Goclaw bridges them as `mcp__<server-slug>__<tool-name>`.
- **Lazy config.** `Config.from_env()` only runs on the first tool call. Importing the package never touches the environment.
- **Uniform pagination.** List-returning tools wrap results in `{count, items[], next_cursor}`. Pass `next_cursor` back as `cursor=` to walk pages.

---

## Tests

All 491 tests are fully offline. No real API keys or network access required.

```bash
cd ~/mcp-servers/<server>
PYTHONPATH=. .venv/bin/pytest -q
```

Each server's test suite mocks at the client boundary — one patch in `conftest.py` covers the entire suite.

---

## Goclaw integration

Goclaw stores MCP server configs in its DB and grants them per-agent.

```bash
ADMIN_AUTH=(-H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" -H "X-GoClaw-User-Id: admin")

# Register a server
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

# Grant to an agent
curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent" \
  -d "{\"agent_id\":\"<agent-uuid>\",\"enabled\":true}"

# Verify discovery
curl -sS "${ADMIN_AUTH[@]}" \
  "http://localhost:18790/v1/mcp/servers/$SERVER_ID/tools" | jq '.[].name'
```

See each server's README for its specific registration payload.

---

## Adding a new server

1. Create `<name>/` mirroring the layout in [Architecture](#architecture).
2. Copy `pytest.ini` + `requirements.txt` patterns from an existing server.
3. Write tests at the same coverage tiers (config / client / api / tools / registry).
4. Update the server table at the top of this file.

Servers are **host-agnostic** — there is nothing goclaw-specific in the code. Any MCP-aware client can launch them.
