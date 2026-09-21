#!/usr/bin/env python3
from __future__ import annotations

import inspect
import profile_media_facebook_ordered_exhaust_r45aq as r45aq


def test_contract_and_static_assets():
    c = r45aq.contract()
    assert c["marker"] == "YTCE_R45AQ_CONTAINER_AWARE_ORDERED_EXHAUST"
    assert c["hidden_platform_api_scraping_enabled"] is False
    assert c["browser_profile_file_parsing_enabled"] is False
    assert r45aq._clean_target_url("[https://x.test/a?b=1](https://x.test/a?b=1\\&c=2)") == "https://x.test/a?b=1&c=2"
    assert "scrollParent" in r45aq.R45AQ_PROBE_JS
    assert "R45AQ_BLOCKED_REMAINING_EXPAND_CONTROLS" in inspect.getsource(r45aq)
    assert "R45AQ_COMPLETE" in inspect.getsource(r45aq)


if __name__ == "__main__":
    test_contract_and_static_assets()
    print("profile_media_facebook_ordered_exhaust_r45aq_test: PASS")
