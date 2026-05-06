# mcp-servers

MCP (Model Context Protocol) server adapters used by the
[mozaa-solana/goclaw](https://github.com/mozaa-solana/goclaw) fork and any
other MCP-compatible host (Claude CLI, opencode-go, custom integrations).

Each server lives in its own subdirectory, ships its own deps, and is
deployed independently. They share no code.

## Servers

| Dir | Purpose | Transport | API key env |
|---|---|---|---|
| [socialdata/](./socialdata) | Twitter / X realtime via [socialdata.tools](https://socialdata.tools) | stdio | `SOCIALDATA_API_KEY` |

> Add a new server by creating `<name>/` with `server.py` (or whatever
> language), `requirements.txt`, `README.md`, then update this table.

## Conventions

- **Stdio first.** Goclaw spawns the process; no network port to manage,
  smaller attack surface. Use HTTP transport only when the upstream API
  is itself stream-friendly and stdio buffering is a problem.
- **Auth via env vars only.** Never hard-code keys into the source.
  Goclaw's MCP server registration accepts an `env` map that's passed to
  the spawned process — keys live in goclaw config, not in this repo.
- **Trim payloads.** Each server's tool returns the minimum viable
  fields a research / writer agent needs (id, timestamp, text, URL,
  engagement counts, author handle). Raw upstream JSON pollutes the
  agent's context window.
- **Structured names.** Tool names use `<topic>_<verb>` (e.g.
  `twitter_search`, `twitter_user_tweets`). When goclaw bridges them
  through its bridge, the full callable becomes
  `mcp__<server-slug>__<tool-name>` — stay short.

## Deploy (any host)

```bash
git clone https://github.com/mozaa-solana/mcp-servers.git ~/mcp-servers
cd ~/mcp-servers/<server>
# install deps however the server's README says
# (typically: pip3 install --user --break-system-packages -r requirements.txt)
```

Then register the server with goclaw via its admin HTTP API
(`POST /v1/mcp/servers`) — see each server's README for the exact
payload, including transport, command, args, and the env-var name it
needs.

## Author convention

Servers are written to be host-agnostic — there is nothing
goclaw-specific in the code. Any MCP-aware client can launch them.
