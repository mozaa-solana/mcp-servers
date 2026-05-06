#!/usr/bin/env python3
"""gdrive-mcp — MCP stdio server wrapping Google Drive v3 (Service Account auth).

Implementation lives under :mod:`gdrive_mcp` (config / drive_client /
normalize / safety / api / tools).

Required env vars:
  GOOGLE_APPLICATION_CREDENTIALS — path to a service-account JSON key file.

Optional env vars:
  GDRIVE_WORKING_FOLDER_ID  — when set, every write tool refuses to act on
                              files outside this folder (or its descendants).
  GDRIVE_DEFAULT_PAGE_SIZE  — default page size for list calls (default 100).

Transport: stdio.
"""
from __future__ import annotations

import sys

from gdrive_mcp.config import ConfigError
from gdrive_mcp.tools import mcp
from gdrive_mcp.tools._registry import get_config


def main() -> None:
    try:
        get_config()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
