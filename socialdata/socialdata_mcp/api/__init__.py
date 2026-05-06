"""REST-resource clients for socialdata.tools.

Each submodule is a thin async wrapper over :mod:`socialdata_mcp.http`. They
return the upstream JSON unmodified — normalization is applied one layer up in
:mod:`socialdata_mcp.tools` so api/* stays reusable for non-MCP callers.
"""
