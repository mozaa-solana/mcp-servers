"""Pay-per-use cost estimates for X API v2 operations.

Numbers reflect the post-2026-04-20 schedule. Update if X changes pricing.
These are estimates only — used for the per-tool ``estimated_cost_usd``
field and the daily budget guard. Real billing is whatever X charges.

References:
- https://docs.x.com/x-api/getting-started/pricing
"""
from __future__ import annotations

# Reads
COST_OWNED_READ = 0.001          # your own posts/bookmarks/followers/lists
COST_STANDARD_READ = 0.005       # other people's posts

# Writes
COST_WRITE_PLAIN = 0.015         # post text/media (no URL)
COST_WRITE_WITH_URL = 0.20       # post containing a URL (link tax)

# Engagement (likes/retweets/follows) — billed as writes per X docs.
# Treated at plain-write rate; refine if X publishes a different number.
COST_ENGAGEMENT = 0.015

# Direct messages — billed as writes
COST_DM_SEND = 0.015


def estimate_post_cost(text: str) -> float:
    """A post containing a URL costs 13× a plain post. Detect naively
    via 'http://' or 'https://' substring — same heuristic X uses."""
    has_url = "http://" in text or "https://" in text
    return COST_WRITE_WITH_URL if has_url else COST_WRITE_PLAIN
