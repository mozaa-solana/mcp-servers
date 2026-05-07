# gdrive MCP server

**Google Drive v3 + Sheets v4 + Docs v1** access for MCP agents through a single Service Account.

62 tools: 21 Drive + 21 Sheets + 20 Docs. No browser, no OAuth consent flow, no refresh tokens.

> **Scope.** Read + safe write. No permanent delete, no permission mutations, no cell formatting.

---

## Quick start

```bash
cd ~/mcp-servers/gdrive
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json .venv/bin/python server.py
```

Verify the handshake:

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

Expect 62 tools in the `tools/list` response.

> **Locked-down distros** (Ubuntu 24.04+ without `python3-venv`):
> `pip3 install --user --break-system-packages -r requirements.txt`

---

## Setup

### One-time GCP setup

1. **Create a Google Cloud project** (skip if you have one).
2. **Enable both APIs**: [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) + [Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com).
3. **Create a service account** in IAM & Admin → Service Accounts. Note its email (e.g. `mcp-bot@my-project.iam.gserviceaccount.com`).
4. **Create a JSON key** for the SA → download the `.json` file. Treat it like a password.
5. **Share each Drive folder / spreadsheet** with the SA email using the Drive "Share" button. Grant **Editor** for read+write, **Viewer** for read-only.

### What the SA can access

- Anything explicitly shared *with* the SA email
- Files in Shared Drives where the SA is a member
- Your own Drive content — **no** (it's a separate identity)

OAuth scopes: `drive` (full access) + `spreadsheets` (explicit Sheets access).

---

## Configuration

| Env var | Required | Default | Purpose |
|---|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | — | Path to the SA JSON key |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | No | — | Alternative alias for the above |
| `GDRIVE_WORKING_FOLDER_ID` | No | — | **Drive write rail** — write tools refuse to mutate files outside this folder tree |
| `GDRIVE_LOCAL_SANDBOX_DIR` | No | — | **Local-disk rail** — upload/download reject paths outside this directory |
| `GDRIVE_DEFAULT_PAGE_SIZE` | No | `100` | Default page size for Drive list calls |

Config is loaded **lazily** on the first tool call.

---

## Tool reference

Drive list tools accept `cursor` and return `next_cursor` for pagination. Sheets tools don't paginate (Sheets API doesn't use cursors).

### Drive — Identity & discovery (3 tools)

| Tool | Description |
|---|---|
| `drive_about()` | SA email + storage quota. **Run this first** to verify auth. |
| `drive_list_shared_with_me(max_results, cursor)` | Everything shared with the SA. |
| `drive_list_drives(max_results, cursor)` | Shared Drives the SA belongs to. |

### Drive — Read (4 tools)

| Tool | Description |
|---|---|
| `drive_list_files(folder_id?, name_contains?, max_results, cursor)` | Children of a folder, optional name filter. |
| `drive_search(query, max_results, cursor)` | Raw Drive query: `name contains`, `fullText contains`, `mimeType =`, `modifiedTime >`. |
| `drive_get_metadata(file_id)` | Name, mimeType, size, parents, owners, modified time. |
| `drive_get_folder_tree(folder_id, max_depth, max_files_per_level)` | Recursive BFS walk; flat list of `{depth, parent, ...}` entries. |

### Drive — Content (2 tools)

| Tool | Description |
|---|---|
| `drive_get_content(file_id, export_mime?)` | Smart export: Docs→md, Sheets→csv, Slides→text, text/* inline, binary rejected with hint. Capped at 1 MB. |
| `drive_export_file(file_id, export_mime, local_path)` | Save any file (native or binary) to a local path. Use for PDFs, .docx, images. |

### Drive — Write (8 tools)

| Tool | Description |
|---|---|
| `drive_create_folder(name, parent_id?)` | Create folder. |
| `drive_copy_file(file_id, new_name?, parent_id?)` | Duplicate. Defaults to "Copy of \<orig\>" in the source's parent. |
| `drive_upload_file(local_path, name?, parent_id?, mime_type?)` | Upload from disk. |
| `drive_create_text_file(name, content, parent_id?, mime_type)` | Create text/markdown/json from inline content. |
| `drive_update_file_content(file_id, content, mime_type)` | Overwrite — old content kept in revision history. |
| `drive_rename_file(file_id, new_name)` | Rename without moving. |
| `drive_move_file(file_id, new_parent_id)` | Reparent (atomically removes old parents). |
| `drive_trash_file(file_id)` | Move to Trash. **Recoverable for 30 days.** |
| `drive_untrash_file(file_id)` | Restore from Trash. |

### Drive — Revisions (2 tools)

| Tool | Description |
|---|---|
| `drive_list_revisions(file_id, max_results, cursor)` | Version history. |
| `drive_get_revision(file_id, revision_id, export_mime?)` | Read a historical revision. Google-native file revisions are limited to text-like formats. |

### Drive — Permissions (1 tool)

| Tool | Description |
|---|---|
| `drive_list_permissions(file_id, cursor)` | Who has access and what role. Use to debug "the bot can't see file X". |

### Sheets — Read (3 tools)

Range strings use **A1 notation**: `Sheet1!A1:B10`, `'My Sheet'!A:B`. Structure tools use **GridRange** (0-based, end-exclusive). Wrap sheet names with spaces in single quotes.

| Tool | Description |
|---|---|
| `sheets_get_metadata(spreadsheet_id)` | Title, locale, time zone, tab list. **Run first** — agents need tab titles to build ranges. |
| `sheets_get_values(spreadsheet_id, cell_range, value_render?, major_dimension?)` | Read a range. `value_render`: `FORMATTED_VALUE` (default), `UNFORMATTED_VALUE`, `FORMULA`. |
| `sheets_batch_get_values(spreadsheet_id, ranges[])` | Multi-range read in one call. |

### Sheets — Write values (5 tools)

| Tool | Description |
|---|---|
| `sheets_update_values(spreadsheet_id, cell_range, values[][], value_input?)` | Overwrite. `value_input`: `USER_ENTERED` (default — formulas/dates parsed) or `RAW`. |
| `sheets_append_values(spreadsheet_id, cell_range, values[][])` | Append rows after the last row of data. |
| `sheets_clear_values(spreadsheet_id, cell_range)` | Empty cells. Sheet structure unchanged. |
| `sheets_batch_update_values(spreadsheet_id, data[])` | Multi-range overwrite. `data = [{"range": ..., "values": [[...]]}]`. |
| `sheets_find_replace(spreadsheet_id, find, replace, sheet_id?, match_case?, match_entire_cell?)` | Find/replace. Scope: one tab or all tabs. |

### Sheets — Tab CRUD (6 tools)

| Tool | Description |
|---|---|
| `sheets_create_spreadsheet(title, parent_id?)` | New spreadsheet. Quota gotcha applies on personal Gmail. |
| `sheets_add_sheet(spreadsheet_id, title)` | Add a tab. |
| `sheets_delete_sheet(spreadsheet_id, sheet_id)` | **Irreversible** — deleted tabs aren't kept in revision history reliably. |
| `sheets_rename_sheet(spreadsheet_id, sheet_id, new_title)` | Rename a tab. |
| `sheets_duplicate_sheet(spreadsheet_id, sheet_id, new_title?)` | Defaults to `Copy of <orig>`. |
| `sheets_copy_sheet_to_spreadsheet(source_ss_id, source_sheet_id, dest_ss_id)` | Copy a tab into a different spreadsheet. Source unchanged. |

### Sheets — Rows / Cols / Sort (4 tools)

| Tool | Description |
|---|---|
| `sheets_insert_rows(spreadsheet_id, sheet_id, start_index, count)` | Insert blank rows at index. |
| `sheets_delete_rows(spreadsheet_id, sheet_id, start_index, count)` | Remove rows entirely. |
| `sheets_insert_cols(spreadsheet_id, sheet_id, start_index, count)` | Insert blank columns. |
| `sheets_delete_cols(spreadsheet_id, sheet_id, start_index, count)` | Remove columns entirely. |
| `sheets_sort_range(spreadsheet_id, sheet_id, start_row, end_row, start_col, end_col, sort_column_index, descending?)` | Sort a GridRange by one column. `sort_column_index` is absolute. |

### Sheets — Layout (2 tools)

| Tool | Description |
|---|---|
| `sheets_freeze(spreadsheet_id, sheet_id, rows=0, cols=0)` | Freeze first N rows/cols. `rows=0, cols=0` unfreezes. |
| `sheets_merge_cells(spreadsheet_id, sheet_id, start_row, end_row, start_col, end_col, mode)` | `mode`: `MERGE_ALL` (default), `MERGE_COLUMNS`, `MERGE_ROWS`, `UNMERGE`. |

### Docs — Read (2 tools)

| Tool | Description |
|---|---|
| `docs_get(document_id)` | Full document structure: paragraphs, tables, named ranges, headers/footers, inline objects. |
| `docs_get_text(document_id)` | Extract plain text from the document body. |

### Docs — Create (1 tool)

| Tool | Description |
|---|---|
| `docs_create(title, parent_id?)` | Create a blank Google Doc. Quota gotcha applies on personal Gmail. |

### Docs — Text editing (3 tools)

| Tool | Description |
|---|---|
| `docs_insert_text(document_id, text, index?)` | Insert text at position (appends to end if no index). |
| `docs_delete_range(document_id, start_index, end_index)` | Delete content between two UTF-16 indices. |
| `docs_replace_text(document_id, find, replace, match_case?)` | Find & replace across entire document. |

### Docs — Styling (2 tools)

| Tool | Description |
|---|---|
| `docs_update_text_style(document_id, start, end, bold?, italic?, underline?, strikethrough?, font_size?, font_family?, link_url?)` | Apply text formatting to a range. |
| `docs_update_paragraph_style(document_id, start, end, alignment?, heading?, indent_start?, line_spacing?)` | Set paragraph alignment, heading level, spacing. |

### Docs — Lists (2 tools)

| Tool | Description |
|---|---|
| `docs_create_bullets(document_id, start, end, preset?)` | Convert paragraphs to bullet/numbered list. |
| `docs_delete_bullets(document_id, start, end)` | Remove bullets from paragraphs. |

### Docs — Tables (5 tools)

| Tool | Description |
|---|---|
| `docs_insert_table(document_id, rows, cols, index?)` | Insert table at position (or end). |
| `docs_insert_table_row(document_id, table_start, row_index, column_index?, insert_below?)` | Insert row above/below reference cell. |
| `docs_delete_table_row(document_id, table_start, row_index, column_index?)` | Delete row. |
| `docs_insert_table_column(document_id, table_start, column_index, row_index?, insert_right?)` | Insert column left/right of reference cell. |
| `docs_delete_table_column(document_id, table_start, column_index, row_index?)` | Delete column. |

### Docs — Images (2 tools)

| Tool | Description |
|---|---|
| `docs_insert_image(document_id, image_uri, index?, width_pt?, height_pt?)` | Insert image from URL. |
| `docs_replace_image(document_id, image_object_id, image_uri)` | Replace an existing image. |

### Docs — Headers / Footers / Footnotes (3 tools)

| Tool | Description |
|---|---|
| `docs_create_header(document_id)` | Create header. Returns header ID. |
| `docs_create_footer(document_id)` | Create footer. Returns footer ID. |
| `docs_create_footnote(document_id, index?)` | Insert footnote at position. Returns footnote ID. |

### Not included in v1

| Drive | Sheets |
|---|---|
| Permanent delete (irreversible) | Cell formatting (colors, fonts, borders) |
| Share / unshare / change role | Conditional formatting, charts, named ranges, protected ranges, filter views |

---

## Response shapes

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

**Spreadsheet metadata:**

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

**Cell range:**

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

**Errors:** validation/scope errors return `{"error": "<msg>"}`. Upstream Drive errors return `{"error": "<msg>", "status_code": 404}`.

---

## Concepts that bite

### Quota gotcha (Service Account on personal Gmail)

Service accounts have **no Drive storage quota** in the personal Gmail context. This affects file *creation* only:

| Operation | Personal Gmail (shared to SA) | Workspace / Shared Drive |
|---|---|---|
| Read (Drive + Sheets) | Works | Works |
| Update content / values | Works | Works |
| Rename / move / trash | Works | Works |
| Add / delete / rename tab | Works (modifies existing spreadsheet) | Works |
| **Create new file / folder / spreadsheet / upload** | **Fails** (SA quota = 0) | Works (org quota) |

Workaround: get a Workspace admin to share a folder with you, then re-share with the SA.

### Safety rails

Two independent rails. Both are no-ops when their env var is unset.

**Drive write rail** (`GDRIVE_WORKING_FOLDER_ID`) — every write tool verifies the target file/folder is inside the configured folder tree. Read tools are unaffected. Rejected calls return `{"error": ..., "violation": "working_folder"}`.

```bash
GDRIVE_WORKING_FOLDER_ID=1abc...xyz   # lock writes to one folder
unset GDRIVE_WORKING_FOLDER_ID        # allow writes anywhere SA has Editor
```

**Local-disk rail** (`GDRIVE_LOCAL_SANDBOX_DIR`) — `drive_upload_file` and `drive_export_file` reject local paths outside the configured directory. Symlinks are resolved via `os.path.realpath`. Defends against path-traversal attacks. Rejected calls return `{"error": ..., "violation": "local_sandbox"}`.

```bash
GDRIVE_LOCAL_SANDBOX_DIR=/var/agent-workspace
```

### Sheets value semantics

| Field | Options | Meaning |
|---|---|---|
| `value_input` | `USER_ENTERED` (default), `RAW` | How input is parsed. `USER_ENTERED` treats values as if typed (formulas, dates auto-detected). `RAW` stores literally. |
| `value_render` | `FORMATTED_VALUE` (default), `UNFORMATTED_VALUE`, `FORMULA` | How output is returned. `FORMATTED_VALUE` is what users see. `FORMULA` returns `=A1+B1` instead of the computed value. |
| `major_dimension` | `ROWS` (default), `COLUMNS` | Whether `values[r][c]` indexes by row or column. |

---

## Architecture

```
gdrive/
├── server.py                          MCP stdio entrypoint
├── gdrive_mcp/
│   ├── config.py                      env → frozen Config (fail-fast)
│   ├── drive_client.py                Drive v3 + Sheets v4 service factories + DriveAPIError
│   ├── normalize.py                   pure trim/MIME helpers
│   ├── safety.py                      working-folder rail
│   ├── api/                           thin REST wrappers (sync — googleapiclient is sync)
│   │   ├── about.py    files.py       content.py
│   │   ├── docs.py                    Docs v1: get, create, batchUpdate helpers
│   │   ├── revisions.py               permissions.py    sheets.py
│   └── tools/                         async @mcp.tool() wrappers (asyncio.to_thread)
│       ├── _registry.py               FastMCP singleton + lazy getters
│       ├── about.py    files.py       content.py
│       ├── docs.py                    20 Docs tools
│       └── revisions.py               permissions.py    sheets.py
└── tests/                             267 unit tests, fully offline
```

Imports flow downward only:

| Layer | Responsibility | Depends on |
|---|---|---|
| `tools/*` | LLM-facing contract — docstrings, validation, trimming | `api/*`, normalize, safety |
| `api/*` | googleapiclient verb wrappers | `drive_client.py` (sync) |
| `drive_client.py` | Auth + transport + error mapping | Network |
| `normalize.py` | Pure data + MIME constants | Nothing |
| `safety.py` | Ancestor walk via service (read-only) | Nothing else |
| `config.py` | Environment variable loading | Nothing |

`googleapiclient` is sync — tools wrap calls in `asyncio.to_thread()` to keep the MCP event loop responsive.

---

## Tests

```bash
.venv/bin/pytest -q          # 302 tests, ~1s
```

Fully offline. `conftest.py` builds mock services (Drive + Sheets + Docs) and patches all getters in every tool module. No real Google credentials needed.

---

## Goclaw integration

```bash
ADMIN_AUTH=(-H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" -H "X-GoClaw-User-Id: admin")

# Register
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

# Grant to an agent
curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent" \
  -d "{\"agent_id\":\"<agent-uuid>\",\"enabled\":true}"

# Verify — should list all 62 tools
curl -sS "${ADMIN_AUTH[@]}" \
  "http://localhost:18790/v1/mcp/servers/$SERVER_ID/tools" | jq '.[].name'
```
