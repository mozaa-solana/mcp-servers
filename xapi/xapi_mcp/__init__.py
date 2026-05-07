"""xapi_mcp — Twitter/X official API adapter for MCP (single-user model).

Layered architecture:
- config.py    → env → frozen Config (fail-fast)
- x_client.py  → tweepy wrapper + error mapping
- cost.py      → per-operation pay-per-use cost estimation
- budget.py    → daily USD spend cap (in-memory)
- normalize.py → trim payloads to LLM-friendly shape
- api/*        → thin per-resource verb wrappers
- tools/*      → @mcp.tool() wrappers (LLM-facing)

This server runs as ONE process per X user. Goclaw should register a
separate MCP server config per user, each with its own access tokens
in env. See README.md → "Multi-user via per-config grant".
"""
