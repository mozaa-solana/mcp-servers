"""Direct message tools.

X DM rules: recipient must be following the sender, OR have DMs open
to everyone. The API will return 403 otherwise — surfaced as an error
dict."""
from __future__ import annotations

import asyncio
from typing import Any

from .. import cost
from ..api import dms as api_dms
from ._registry import get_budget, get_client, get_config, handle_x_errors, mcp
from .users import _resolve_user_id


@mcp.tool()
@handle_x_errors
async def x_send_dm(recipient_handle_or_id: str, text: str) -> dict[str, Any]:
    """Send a 1:1 direct message. Recipient is ``@handle`` or numeric id.
    Cost ≈ $0.015. Honours ``X_DRY_RUN=1``."""
    if not text or not text.strip():
        return {"error": "text must not be empty"}
    cost_usd = cost.COST_DM_SEND
    get_budget().check(cost_usd)
    if get_config().dry_run:
        return {
            "dry_run": True,
            "would_send_to": recipient_handle_or_id,
            "text": text,
            "estimated_cost_usd": cost_usd,
        }
    target_id = await _resolve_user_id(recipient_handle_or_id)
    raw = await asyncio.to_thread(api_dms.send_to_user, get_client(), target_id, text)
    get_budget().record(cost_usd)
    return {"sent": True, "target_id": target_id, "raw": raw, "estimated_cost_usd": cost_usd}
