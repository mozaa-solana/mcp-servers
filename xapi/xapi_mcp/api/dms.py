"""Direct message verbs. Sync — wrap in to_thread."""
from __future__ import annotations

from typing import Any

from ..x_client import XClient


def send_to_user(client: XClient, recipient_user_id: str, text: str) -> dict[str, Any]:
    """Send a 1:1 DM. Recipient must follow the sender (X DM rules)."""
    resp = client.v2.create_direct_message(
        participant_id=recipient_user_id,
        text=text,
    )
    return resp.data or {}
