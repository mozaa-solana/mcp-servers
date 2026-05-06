"""``about.get`` — sanity check + identity introspection."""
from __future__ import annotations

from typing import Any


ABOUT_FIELDS = "user(emailAddress,displayName),storageQuota"


def get_about(service: Any) -> dict[str, Any]:
    return service.about().get(fields=ABOUT_FIELDS).execute()
