# gdrive-mcp

Google Drive v3 access for MCP-aware agents. Auth via Service Account.
**18 tools, v1 = read + write** (no permanent delete, no permission
mutations — those are deferred to v2).

> Same layered architecture as `socialdata`: `config / drive_client /
> normalize / safety / api / tools / tests`.

---

## Table of contents

- [Quick start](#quick-start)
- [Auth model — Service Account](#auth-model--service-account)
- [Configuration](#configuration)
- [Tool reference](#tool-reference)
- [Response shapes](#response-shapes)
- [Safety rail (`GDRIVE_WORKING_FOLDER_ID`)](#safety-rail-gdrive_working_folder_id)
- [Quota gotcha](#quota-gotcha)
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

# 2. Get a service-account JSON key (see "Auth model" below)

# 3. Run
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json \
  .venv/bin/python server.py
```

Smoke test:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json \
  .venv/bin/python server.py < <(cat <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
EOF
)
```
Expect 18 entries.

---

## Auth model — Service Account

Service accounts are robot identities with their own email
(`mcp-bot@my-project.iam.gserviceaccount.com`). They authenticate via a
JSON private key — no browser, no OAuth consent flow, no refresh tokens.

### Setup steps

1. **Create a Google Cloud project** (if you don't already have one).
2. **Enable the Google Drive API** in that project.
3. **Create a service account** in IAM & Admin → Service Accounts. Note
   its email address.
4. **Create a JSON key** for the service account → download the `.json` file.
5. **Share each Drive folder/file** you want the bot to access **with the
   service account email** (use the regular Drive "Share" button — same as
   sharing with a person). Grant `Editor` for read+write, `Viewer` for
   read-only.
6. Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json` and run the server.

### What it sees

- ✅ Anything explicitly shared *with* the service account email.
- ✅ Files in Shared Drives where the SA is a member.
- ❌ Your other Drive content (it's a separate identity).

### What it can do

- ✅ **Edit, rename, move, trash** any file shared with `Editor` role.
- ⚠️ **Create new files**: works on **Workspace folders** / **Shared Drives**
  (quota comes from the org). On personal Gmail, see [Quota gotcha](#quota-gotcha).

---

## Configuration

| Env var | Required | Default | Notes |
|---|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ | — | Path to the service-account JSON key file. Standard Google env var. |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | — | — | Alias for the above (project-specific name). |
| `GDRIVE_WORKING_FOLDER_ID` | — | — | **Safety rail.** When set, every write tool refuses to mutate files outside this folder (or its descendants). See below. |
| `GDRIVE_DEFAULT_PAGE_SIZE` | — | `100` | Default page size for list calls. |

Config is loaded **lazily** on the first tool invocation, so importing
the package never touches the environment — keeps tests clean.

---

## Tool reference

All paginated tools accept `cursor` and return `next_cursor`. Pass it
back as `cursor=` to walk the next page.

### 🪪 Identity / discovery (2)

| Tool | Purpose |
|---|---|
| `drive_about()` | Service-account email + Drive storage quota. **Run this first** — verifies auth wired up correctly. |
| `drive_list_shared_with_me(max_results, cursor)` | Files/folders shared *with* the SA. The canonical "what can the bot see?" view. |

### 🔍 Read (4)

| Tool | Purpose |
|---|---|
| `drive_list_files(folder_id?, name_contains?, max_results, cursor)` | List children of a folder, optionally filtered by name. |
| `drive_search(query, max_results, cursor)` | Raw Drive query string. Operators: `name contains`, `fullText contains`, `mimeType =`, `modifiedTime >`, etc. |
| `drive_get_metadata(file_id)` | name, mimeType, size, parents, owners, modified time. |
| `drive_get_folder_tree(folder_id, max_depth, max_files_per_level)` | Recursive BFS walk of a folder; flat list of `{depth, parent, ...}` entries. |

### 📖 Content (2)

| Tool | Purpose |
|---|---|
| `drive_get_content(file_id, export_mime?)` | **Smart export**: Google Docs → markdown, Sheets → CSV, Slides → text. text/* downloaded inline. Binary rejected with hint. Capped at 1 MB. |
| `drive_export_file(file_id, export_mime, local_path)` | Save a Google native file (or any binary) to a local path. Use for PDFs, .docx, images, etc. |

### ✏️ Write (8)

| Tool | Purpose |
|---|---|
| `drive_create_folder(name, parent_id?)` | Create a new folder. |
| `drive_upload_file(local_path, name?, parent_id?, mime_type?)` | Upload a binary or text file from disk. |
| `drive_create_text_file(name, content, parent_id?, mime_type)` | Create a new text/markdown/json file from inline content. |
| `drive_update_file_content(file_id, content, mime_type)` | Overwrite content of an existing file. Old content kept in revision history. |
| `drive_rename_file(file_id, new_name)` | Rename without moving. |
| `drive_move_file(file_id, new_parent_id)` | Reparent a file (atomically removes old parents). |
| `drive_trash_file(file_id)` | Move to Trash. **Recoverable for 30 days** via the Drive web UI — not a permanent delete. |
| `drive_export_file(...)` | (also listed under Content — used for both reading and "saving a copy"). |

### 🕘 Revisions (2)

| Tool | Purpose |
|---|---|
| `drive_list_revisions(file_id, max_results, cursor)` | File version history. |
| `drive_get_revision(file_id, revision_id, export_mime?)` | Read content of a historical revision. **Limitation**: Drive API doesn't allow exporting historical revisions of Google-native files — only text-like revisions are readable here. |

### 🛡️ Permissions (1, read-only)

| Tool | Purpose |
|---|---|
| `drive_list_permissions(file_id, cursor)` | Who has access (and what role). Use to debug "the bot can't see file X". |

### Intentionally NOT in v1

- **Permanent delete** (bypasses Trash) — irreversible, deferred to v2.
- **Share / unshare / change role** — alters security boundary, deferred to v2.

---

## Response shapes

**Trimmed file:**
```json
{
  "id": "abc123",
  "name": "Q4 plan.md",
  "mimeType": "text/markdown",
  "size": 2048,
  "modified": "2026-05-01T10:30:00Z",
  "created": "2026-04-01T08:00:00Z",
  "parents": ["FOLDER_ID"],
  "owners": [{"email": "u@x.com", "name": "User"}],
  "trashed": false,
  "url": "https://drive.google.com/file/d/abc123/view",
  "is_folder": false,
  "is_google_native": false
}
```

**Paginated envelope:**
```json
{ "count": 20, "files": [/* …trimmed files… */], "next_cursor": "abc..." }
```

**Content (text):**
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

**Error:** all tools return `{"error": "<message>"}` for input validation
or unsupported scenarios. Upstream Drive errors raise `DriveAPIError`
with HTTP status (404 / 403 / 429 etc.).

---

## Safety rail (`GDRIVE_WORKING_FOLDER_ID`)

Set this env var to restrict **all write operations** to a single folder
(and its descendants). When set:

- `drive_create_folder` / `drive_upload_file` / `drive_create_text_file`
  **require** `parent_id` and verify it's inside the rail.
- `drive_rename_file` / `drive_move_file` / `drive_trash_file` /
  `drive_update_file_content` walk the file's parent chain to verify it.
- Read tools (list/search/get_content/etc.) are **unaffected** — read is
  always safe.

```bash
# Lock the agent to a single working folder while you're learning the model
GDRIVE_WORKING_FOLDER_ID=1abc...xyz

# Unset to allow writes anywhere the SA has been granted Editor
unset GDRIVE_WORKING_FOLDER_ID
```

Implementation: `gdrive_mcp/safety.py` — walks `parents[0]` chain via
`files.get(fields=parents)` until it finds the rail folder or exhausts
the chain.

---

## Quota gotcha

Service accounts on **personal Gmail** have **no Drive storage quota of
their own**. This affects file *creation*:

| Operation | Personal Gmail folder shared to SA | Workspace folder / Shared Drive shared to SA |
|---|---|---|
| Read | ✅ | ✅ |
| Update content of existing file | ✅ | ✅ |
| Rename / move / trash | ✅ | ✅ |
| **Create new file / folder / upload** | ❌ (SA quota = 0) | ✅ (org quota) |

→ For real write workflows on personal Gmail, the practical setup is
**have the Workspace admin share a folder with you**, then re-share with
your SA. Files created live in the org's quota, not yours and not the SA's.

---

## Architecture

```
gdrive/
├── server.py                  ← MCP stdio entrypoint
├── gdrive_mcp/
│   ├── config.py              ← env → frozen Config (fail-fast)
│   ├── drive_client.py        ← googleapiclient service factory + DriveAPIError
│   ├── normalize.py           ← pure trim_file/trim_user/trim_revision/trim_permission/clamp/paginated/MIME helpers
│   ├── safety.py              ← working-folder rail (assert_in_working_folder)
│   ├── api/                   ← thin REST wrappers (sync, googleapiclient is sync)
│   │   ├── about.py
│   │   ├── files.py           ← list/get/create-folder/rename/move/trash
│   │   ├── content.py         ← download_bytes/export_bytes/upload/create_text/update
│   │   ├── revisions.py
│   │   └── permissions.py
│   └── tools/                 ← @mcp.tool() wrappers (async via asyncio.to_thread)
│       ├── _registry.py       ← FastMCP singleton + lazy get_config / get_service
│       ├── about.py
│       ├── files.py
│       ├── content.py
│       ├── revisions.py
│       └── permissions.py
└── tests/                     ← 93 unit tests, fully offline (mocked googleapiclient)
```

**Layering rules:**

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
.venv/bin/pytest -q          # 93 tests, ~0.6s
```

Fully offline. The conftest builds a `MagicMock` Drive service and
patches `get_config()` + `get_service()` in every tool module. No real
Google credentials needed.

| Layer | What's tested |
|---|---|
| `config.py` | Env loading, validation, fail-fast on missing key file |
| `safety.py` | Parent-chain walk, descendant detection, rail-disabled noop |
| `normalize.py` | MIME helpers, trim_file/user/revision/permission, pagination envelope |
| `api/files.py` | Verbs + kwargs sent to googleapiclient |
| `tools/about.py` | Identity + shared-with-me listing, clamping |
| `tools/files.py` | Query construction, escaping, folder tree BFS, all safety-rail interactions |
| `tools/content.py` | Smart export logic per MIME, truncation, file I/O, all safety-rail interactions |
| `tools/revisions.py` | Native-file limitation, text decode, binary rejection |
| `tools/permissions.py` | Listing + envelope |
| `_registry` | All 18 tools registered via `mcp.list_tools()` |

---

## Goclaw integration

```bash
ADMIN_AUTH=(-H "Authorization: Bearer $GOCLAW_GATEWAY_TOKEN" -H "X-GoClaw-User-Id: admin")

SERVER_ID=$(curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST http://localhost:18790/v1/mcp/servers \
  -d '{
    "name": "gdrive",
    "display_name": "Google Drive (Service Account)",
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

# Grant to a specific agent
curl -sS "${ADMIN_AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/grants/agent" \
  -d "{\"agent_id\":\"<agent-uuid>\",\"enabled\":true}"

# Reload + verify
curl -sS "${ADMIN_AUTH[@]}" \
  -X POST "http://localhost:18790/v1/mcp/servers/$SERVER_ID/reconnect"

curl -sS "${ADMIN_AUTH[@]}" \
  "http://localhost:18790/v1/mcp/servers/$SERVER_ID/tools" | jq '.[].name'
```

Should return all 18 `drive_*` tools.
