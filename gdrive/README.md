# gdrive-mcp

MCP stdio server giving agents (Claude CLI, opencode-go, goclaw bridge
consumers) access to **Google Drive v3** and **Google Sheets v4** through
a single Service Account.

| | |
|---|---|
| **Tools** | 42 — 21 Drive + 21 Sheets |
| **Auth** | Service Account JSON key (no browser, no OAuth flow) |
| **Scope** | Read + safe write. No permanent delete, no permission mutations, no cell formatting |
| **Safety rail** | Optional `GDRIVE_WORKING_FOLDER_ID` confines all writes to one folder |
| **Tests** | 161 unit tests, 100% offline (mocked googleapiclient) |
| **Architecture** | Layered: `config / drive_client / normalize / safety / api / tools / tests` |

---

## Table of contents

- [Quick start](#quick-start)
- [Setup](#setup)
- [Configuration](#configuration)
- [Tool reference](#tool-reference)
- [Response shapes](#response-shapes)
- [Concepts that bite](#concepts-that-bite)
- [Architecture](#architecture)
- [Tests](#tests)
- [Goclaw integration](#goclaw-integration)

---

## Quick start

```bash
# 1. Install
git clone https://github.com/mozaa-solana/mcp-servers.git ~/mcp-servers
cd ~/mcp-servers/gdrive
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Run (after completing Setup below)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json \
  .venv/bin/python server.py
```

Smoke test the stdio handshake — should return 42 tools:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json \
  .venv/bin/python server.py < <(cat <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"drive_about","arguments":{}}}
EOF
)
```

> **Locked-down distros** (Ubuntu 24.04+ without `python3-venv`):
> `pip3 install --user --break-system-packages -r requirements.txt`

---

## Setup

Service Account = a robot identity with its own email. It authenticates
with a JSON private key — no browser, no OAuth consent flow, no refresh
tokens.

### One-time GCP setup

1. **Create a Google Cloud project** (skip if you already have one).
2. **Enable both APIs** in that project:
   - [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
   - [Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
3. **Create a service account** in IAM & Admin → Service Accounts. Note its email — looks like `mcp-bot@my-project.iam.gserviceaccount.com`.
4. **Create a JSON key** for the SA → download the `.json` file. Treat it like a password.

### Per-resource sharing

5. **Share each Drive folder / spreadsheet** with the SA email — same Drive "Share" button you'd use for a person. Grant **Editor** for read+write, **Viewer** for read-only.

### Run

6. Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json` and start `server.py`.

### What the SA can see / do

- ✅ Anything explicitly shared *with* the SA email.
- ✅ Files in Shared Drives where the SA is a member.
- ❌ Your own Drive content (it's a separate identity).

OAuth scopes used:
- `https://www.googleapis.com/auth/drive` — full Drive access
- `https://www.googleapis.com/auth/spreadsheets` — explicit Sheets access

---

## Configuration

| Env var | Required | Default | Notes |
|---|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ | — | Path to the SA JSON key. Standard Google env var. |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | — | — | Project-specific alias for the above. |
| `GDRIVE_WORKING_FOLDER_ID` | — | — | **Safety rail** — see below. When set, every write tool refuses to mutate files outside this folder. |
| `GDRIVE_DEFAULT_PAGE_SIZE` | — | `100` | Default page size for Drive list calls. |

Config is loaded **lazily** on the first tool call, so importing the
package never touches the environment — keeps tests clean.

---

## Tool reference

Drive list tools accept `cursor` and return `next_cursor` for pagination.
Sheets tools don't paginate (Sheets API doesn't use cursors).

### 🟦 Drive (21)

#### Identity / discovery

| Tool | Purpose |
|---|---|
| `drive_about()` | SA email + Drive storage quota. **Run this first** — verifies auth wired up correctly. |
| `drive_list_shared_with_me(max_results, cursor)` | The canonical "what can the bot see?" view. |
| `drive_list_drives(max_results, cursor)` | Shared Drives the SA is a member of. Empty list is normal on personal Gmail. |

#### Read

| Tool | Purpose |
|---|---|
| `drive_list_files(folder_id?, name_contains?, max_results, cursor)` | List children of a folder, optional name filter. |
| `drive_search(query, max_results, cursor)` | Raw Drive query: `name contains`, `fullText contains`, `mimeType =`, `modifiedTime >`. |
| `drive_get_metadata(file_id)` | name, mimeType, size, parents, owners, modified time. |
| `drive_get_folder_tree(folder_id, max_depth, max_files_per_level)` | Recursive BFS walk; flat list of `{depth, parent, ...}` entries. |

#### Content

| Tool | Purpose |
|---|---|
| `drive_get_content(file_id, export_mime?)` | **Smart export**: Docs→md, Sheets→csv, Slides→text, text/* inline, binary rejected with hint. Capped at 1 MB. |
| `drive_export_file(file_id, export_mime, local_path)` | Save Google native (or any binary) to a local path. Use for PDFs, .docx, images. |

#### Write

| Tool | Purpose |
|---|---|
| `drive_create_folder(name, parent_id?)` | Create folder. |
| `drive_copy_file(file_id, new_name?, parent_id?)` | Duplicate a file ("copy from template" workflow). Defaults to "Copy of <orig>" in the source's parent. |
| `drive_upload_file(local_path, name?, parent_id?, mime_type?)` | Upload binary or text from disk. |
| `drive_create_text_file(name, content, parent_id?, mime_type)` | Create text/markdown/json from inline content. |
| `drive_update_file_content(file_id, content, mime_type)` | Overwrite — old content kept in revision history. |
| `drive_rename_file(file_id, new_name)` | Rename without moving. |
| `drive_move_file(file_id, new_parent_id)` | Reparent (atomically removes old parents). |
| `drive_trash_file(file_id)` | Move to Trash. **Recoverable for 30 days**. NOT permanent delete. |
| `drive_untrash_file(file_id)` | Restore from Trash. Pair with `drive_trash_file`. |

#### Revisions

| Tool | Purpose |
|---|---|
| `drive_list_revisions(file_id, max_results, cursor)` | Version history. |
| `drive_get_revision(file_id, revision_id, export_mime?)` | Read content of a historical revision. **Limitation**: Drive API doesn't allow exporting historical revisions of Google-native files — only text-like revisions are readable. |

#### Permissions (read-only)

| Tool | Purpose |
|---|---|
| `drive_list_permissions(file_id, cursor)` | Who has access (and what role). Use to debug "the bot can't see file X". |

### 🟩 Sheets (21)

Range strings use **A1 notation** for value tools (`Sheet1!A1:B10`, `'My
Sheet'!A:B`). Structure tools (insert/delete rows/cols, sort, merge) use
**GridRange** with 0-based, end-exclusive indices. Wrap sheet names with
spaces in single quotes. The `spreadsheet_id` is the same string as the
Drive file id — find it via `drive_search` / `drive_list_files`.

#### Read

| Tool | Purpose |
|---|---|
| `sheets_get_metadata(spreadsheet_id)` | Title, locale, time zone, list of tabs (sheet ids, titles, dimensions). **Run first** — agents need tab titles to build A1 ranges. |
| `sheets_get_values(spreadsheet_id, range, value_render?, major_dimension?)` | Read a range. `value_render`: `FORMATTED_VALUE` (default), `UNFORMATTED_VALUE`, `FORMULA`. |
| `sheets_batch_get_values(spreadsheet_id, ranges[])` | Multi-range read in one call. Cheaper than N individual gets. |

#### Write — values

| Tool | Purpose |
|---|---|
| `sheets_update_values(spreadsheet_id, range, values[][], value_input?)` | **Overwrite**. `value_input`: `USER_ENTERED` (default — formulas/dates parsed) or `RAW`. |
| `sheets_append_values(spreadsheet_id, range, values[][])` | Append rows after the last row of data. |
| `sheets_clear_values(spreadsheet_id, range)` | Empty cells. Sheet structure unchanged. |
| `sheets_batch_update_values(spreadsheet_id, data[])` | Multi-range overwrite. `data` = `[{"range": ..., "values": [[...]]}]`. |
| `sheets_find_replace(spreadsheet_id, find, replace, sheet_id?, match_case?, match_entire_cell?)` | Find/replace text. Scope: a single tab (`sheet_id`) or all tabs. |

#### Write — structure (tab CRUD)

| Tool | Purpose |
|---|---|
| `sheets_create_spreadsheet(title, parent_id?)` | New spreadsheet. Quota gotcha applies on personal Gmail. |
| `sheets_add_sheet(spreadsheet_id, title)` | Add a new tab. |
| `sheets_delete_sheet(spreadsheet_id, sheet_id)` | **Irreversible** — Drive doesn't keep deleted tabs in revision history reliably. |
| `sheets_rename_sheet(spreadsheet_id, sheet_id, new_title)` | Rename a tab. |
| `sheets_duplicate_sheet(spreadsheet_id, sheet_id, new_title?)` | Defaults to `Copy of <orig>`. |
| `sheets_copy_sheet_to_spreadsheet(source_ss_id, source_sheet_id, dest_ss_id)` | Copy a tab into a *different* spreadsheet. Source unchanged. |

#### Write — structure (rows / cols / sort)

| Tool | Purpose |
|---|---|
| `sheets_insert_rows(spreadsheet_id, sheet_id, start_index, count)` | Insert blank rows at index. Different from `append` (after data) and `clear_values` (empty content only). |
| `sheets_delete_rows(spreadsheet_id, sheet_id, start_index, count)` | Remove rows entirely. |
| `sheets_insert_cols(spreadsheet_id, sheet_id, start_index, count)` | Insert blank columns at index (A=0, B=1, …). |
| `sheets_delete_cols(spreadsheet_id, sheet_id, start_index, count)` | Remove columns entirely. |
| `sheets_sort_range(spreadsheet_id, sheet_id, start_row, end_row, start_col, end_col, sort_column_index, descending?)` | Sort a GridRange by one column. `sort_column_index` is the **absolute** column. |

#### Write — layout

| Tool | Purpose |
|---|---|
| `sheets_freeze(spreadsheet_id, sheet_id, rows=0, cols=0)` | Freeze first N rows and/or first M columns. `rows=0, cols=0` unfreezes. |
| `sheets_merge_cells(spreadsheet_id, sheet_id, start_row, end_row, start_col, end_col, mode)` | `mode`: `MERGE_ALL` (default), `MERGE_COLUMNS`, `MERGE_ROWS`, `UNMERGE`. |

### Intentionally NOT in v1

| Drive | Sheets |
|---|---|
| Permanent delete (irreversible) | Cell formatting (colors, fonts, borders) |
| Share / unshare / change role | Conditional formatting |
| | Charts, named ranges, protected ranges, filter views |

For one-off formatting, use the web UI. Revisit if agents need it.

---

## Response shapes

Every paginated Drive list tool wraps results in:
```json
{ "count": 20, "files": [/* ... */], "next_cursor": "abc..." }
```

**Trimmed Drive file:**
```json
{
  "id": "abc123",
  "name": "Q4 plan.md",
  "mimeType": "text/markdown",
  "size": 2048,
  "modified": "2026-05-01T10:30:00Z",
  "parents": ["FOLDER_ID"],
  "owners": [{"email": "u@x.com", "name": "User"}],
  "url": "https://drive.google.com/file/d/abc123/view",
  "is_folder": false,
  "is_google_native": false
}
```

**Drive content (`drive_get_content`):**
```json
{
  "id": "abc123",
  "name": "Q4 plan.md",
  "mimeType": "text/markdown",
  "exported_as": "text/markdown",
  "content": "# Q4 plan\n...",
  "truncated": false
}
```

**Spreadsheet metadata (`sheets_get_metadata`):**
```json
{
  "id": "1abc...",
  "title": "Q4 Forecast",
  "locale": "en_US",
  "time_zone": "America/Los_Angeles",
  "url": "https://docs.google.com/spreadsheets/d/1abc.../edit",
  "sheets": [
    {"sheet_id": 0, "title": "Summary", "index": 0, "rows": 100, "cols": 26},
    {"sheet_id": 1234567890, "title": "Data", "index": 1, "rows": 1000, "cols": 10}
  ]
}
```

**Cell range (`sheets_get_values`):**
```json
{
  "spreadsheet_id": "1abc...",
  "range": "Summary!A1:C3",
  "major_dimension": "ROWS",
  "values": [
    ["Region", "Q3", "Q4"],
    ["AMER", 1200, 1500],
    ["EMEA", 800, 950]
  ]
}
```

**Errors**: validation/scope errors return `{"error": "<msg>"}`. Upstream
Drive errors raise `DriveAPIError` with HTTP status (404 / 403 / 429).

---

## Concepts that bite

### Quota gotcha (Service Account on personal Gmail)

Service accounts have **no Drive storage quota of their own** in the
personal Gmail context. This affects file *creation* only:

| Operation | Personal Gmail folder shared to SA | Workspace folder / Shared Drive |
|---|---|---|
| Read (Drive + Sheets) | ✅ | ✅ |
| Update content / values | ✅ | ✅ |
| Rename / move / trash | ✅ | ✅ |
| Add / delete / rename / duplicate sheet (tab) | ✅ (modifies existing spreadsheet) | ✅ |
| **Create new file / folder / spreadsheet / upload** | ❌ (SA quota = 0) | ✅ (org quota) |

→ Practical setup: get a Workspace admin to share a folder with you;
re-share with the SA. New files live in the org's quota.

### Safety rail (`GDRIVE_WORKING_FOLDER_ID`)

When set, **every write tool** refuses to act outside the configured
folder (or its descendants):

- `drive_create_folder` / `drive_upload_file` / `drive_create_text_file`
  / `sheets_create_spreadsheet` **require** `parent_id` and verify it.
- `drive_rename_file` / `drive_move_file` / `drive_trash_file` /
  `drive_update_file_content` walk the file's parent chain.
- All **Sheets writes** (values + structure) walk the spreadsheet's
  parent chain — the spreadsheet itself must live inside the rail.
- **Read tools are unaffected** — read is always safe.

```bash
# Lock the agent to a single working folder while you're learning the model
GDRIVE_WORKING_FOLDER_ID=1abc...xyz

# Unset to allow writes anywhere the SA has Editor access
unset GDRIVE_WORKING_FOLDER_ID
```

Implementation: `gdrive_mcp/safety.py` walks `parents[0]` via
`files.get(fields=parents)` until it reaches the rail folder or
exhausts the chain.

### Sheets value semantics

| Field | Values | Meaning |
|---|---|---|
| `value_input` | `USER_ENTERED` (default), `RAW` | How input is parsed. `USER_ENTERED` treats values as if a user typed them (formulas, dates auto-detected). `RAW` stores literally. |
| `value_render` | `FORMATTED_VALUE` (default), `UNFORMATTED_VALUE`, `FORMULA` | How output is returned. `FORMATTED_VALUE` is what users see. `UNFORMATTED_VALUE` returns raw values (dates as serial numbers). `FORMULA` returns `=A1+B1` instead of the computed value. |
| `major_dimension` | `ROWS` (default), `COLUMNS` | Whether `values[r][c]` indexes by row or column. |

---

## Architecture

```
gdrive/
├── server.py                          ← MCP stdio entrypoint
├── gdrive_mcp/
│   ├── config.py                      ← env → frozen Config (fail-fast)
│   ├── drive_client.py                ← Drive v3 + Sheets v4 service factories + DriveAPIError
│   ├── normalize.py                   ← pure trim/MIME helpers (incl. trim_spreadsheet)
│   ├── safety.py                      ← working-folder rail
│   ├── api/                           ← thin REST wrappers (sync; googleapiclient is sync)
│   │   ├── about.py    files.py    content.py
│   │   ├── revisions.py    permissions.py    sheets.py
│   └── tools/                         ← async @mcp.tool() wrappers (asyncio.to_thread)
│       ├── _registry.py               ← FastMCP singleton + lazy get_config / get_service / get_sheets_service
│       ├── about.py    files.py    content.py
│       └── revisions.py    permissions.py    sheets.py
└── tests/                             ← 161 unit tests, fully offline
```

**Layering rules** (enforced by import direction):

| Layer | Knows about | Talks to |
|---|---|---|
| `tools/*` | MCP, normalize, safety, asyncio | `api/*` |
| `api/*` | googleapiclient verbs | `service` (sync) |
| `drive_client.py` | google-auth, googleapiclient | network |
| `normalize.py` | pure data + MIME constants | nothing |
| `safety.py` | ancestor walk via service | nothing else |
| `config.py` | env vars | nothing |

`googleapiclient` is sync — tools wrap calls in `asyncio.to_thread()` so
the MCP event loop stays responsive.

---

## Tests

```bash
.venv/bin/pytest -q          # 161 tests, ~1s
```

100% offline. The conftest builds two `MagicMock` services (Drive +
Sheets) and patches `get_config()` / `get_service()` /
`get_sheets_service()` in every tool module. No real Google credentials
needed.

| Layer | Coverage |
|---|---|
| `config.py` | Env loading, validation, fail-fast on missing key file |
| `safety.py` | Parent-chain walk, descendant detection, rail-disabled noop |
| `normalize.py` | MIME helpers, trim_file/user/revision/permission/spreadsheet, pagination envelope |
| `api/files.py` | Verbs + kwargs sent to googleapiclient (Drive) |
| `api/sheets.py` | Sheets v4 verbs (values get/update/append/clear/batch, structure batchUpdate, create-via-drive) |
| `tools/about.py` | Identity + shared-with-me listing, clamping |
| `tools/files.py` | Query construction, escaping, folder-tree BFS, all safety-rail interactions |
| `tools/content.py` | Smart export per MIME, truncation, file I/O, all safety-rail interactions |
| `tools/revisions.py` | Native-file limitation, text decode, binary rejection |
| `tools/permissions.py` | Listing + envelope |
| `tools/sheets.py` | A1 range passthrough, value-render options, append vs update vs batch, structure mutations, safety-rail on spreadsheet parent |
| `_registry` | All 42 tools registered via `mcp.list_tools()` |

---

## Goclaw integration

```bash
ADMIN_AUTH=(-H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" -H "X-GoClaw-User-Id: admin")

# 1. Register the server (returns SERVER_ID)
SERVER_ID=$(curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST http://localhost:18790/v1/mcp/servers \
  -d '{
    "name": "gdrive",
    "display_name": "Google Drive + Sheets (Service Account)",
    "transport": "stdio",
    "command": "/home/goclaw/mcp-servers/gdrive/.venv/bin/python",
    "args": ["/home/goclaw/mcp-servers/gdrive/server.py"],
    "env": {
      "GOOGLE_APPLICATION_CREDENTIALS": "/home/goclaw/secrets/sa-key.json",
      "GDRIVE_WORKING_FOLDER_ID": "1abc...xyz"
    },
    "tool_prefix": "drive",
    "timeout_sec": 30,
    "enabled": true
  }' | jq -r .id)

# 2. Grant to a specific agent
curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent" \
  -d "{\"agent_id\":\"<agent-uuid>\",\"enabled\":true}"

# 3. Reload + verify (should list all 42 tools)
curl -sS "${ADMIN_AUTH[@]}" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/reconnect"

curl -sS "${ADMIN_AUTH[@]}" \
  "http://localhost:18790/v1/mcp/servers/$SERVER_ID/tools" | jq '.[].name'
```

Only granted agents see the tools in their MCP discovery.
