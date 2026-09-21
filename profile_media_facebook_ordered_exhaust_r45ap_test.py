#!/usr/bin/env python3
from __future__ import annotations

import inspect
import profile_media_facebook_ordered_exhaust_r45ap as r45ap


def test_contract_and_static_assets():
    contract = r45ap.contract()
    assert contract["marker"] == "YTCE_R45AP_SIMPLE_ORDERED_EXHAUST_ENGINE"
    assert contract["hidden_platform_api_scraping_enabled"] is False
    assert contract["browser_profile_file_parsing_enabled"] is False
    assert "view_all_replies" in r45ap.R45AP_PROBE_JS
    assert "view_hidden" in r45ap.R45AP_PROBE_JS
    assert "replied_buckets" in r45ap.R45AP_PROBE_JS
    assert "R45AP_BLOCKED_REMAINING_EXPAND_CONTROLS" in inspect.getsource(r45ap)
    assert "R45AP_COMPLETE" in inspect.getsource(r45ap)
    assert "pre_expand_pause" not in inspect.getsource(r45ap.build_parser)


if __name__ == "__main__":
    test_contract_and_static_assets()
    print("profile_media_facebook_ordered_exhaust_r45ap_test: PASS")
