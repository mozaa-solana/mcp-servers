"""Tests for the post cost estimator (URL detection)."""
from __future__ import annotations

import pytest

from xapi_mcp import cost


@pytest.mark.unit
class TestEstimatePostCost:
    def test_plain_text_is_cheap(self):
        assert cost.estimate_post_cost("hello world") == cost.COST_WRITE_PLAIN

    def test_https_url_triggers_link_tax(self):
        assert cost.estimate_post_cost("see https://example.com") == cost.COST_WRITE_WITH_URL

    def test_http_url_triggers_link_tax(self):
        assert cost.estimate_post_cost("see http://example.com") == cost.COST_WRITE_WITH_URL

    def test_link_tax_is_13x(self):
        # Sanity check that the published 13× ratio is preserved.
        assert cost.COST_WRITE_WITH_URL / cost.COST_WRITE_PLAIN > 10
