"""Drive REST resource clients.

Each submodule is sync (googleapiclient is sync). Tools wrap calls in
``asyncio.to_thread`` so the MCP event loop stays responsive.

The functions here return the raw upstream JSON unmodified — normalization
happens in the tool layer to keep api/* reusable.
"""
