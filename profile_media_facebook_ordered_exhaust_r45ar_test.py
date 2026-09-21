#!/usr/bin/env python3
from __future__ import annotations

import inspect
import profile_media_facebook_ordered_exhaust_r45ar as r45ar


def test_contract_and_static_assets():
    c = r45ar.contract()
    assert c["marker"] == "YTCE_R45AR_TARGET_LOCKED_EXACT_LABEL_ORDERED_EXHAUST"
    assert c["hidden_platform_api_scraping_enabled"] is False
    assert c["browser_profile_file_parsing_enabled"] is False
    assert r45ar._clean_target_url("[https://x.test/a?b=1](https://x.test/a?b=1\\&c=2)") == "https://x.test/a?b=1&c=2"
    assert r45ar._target_fbid("https://www.facebook.com/permalink.php?story_fbid=pfbidABC&id=123") == "pfbidABC"
    assert "R45AR_TARGET_SURFACE_LOST" in inspect.getsource(r45ar)
    assert "unsafeNavigatingAnchor" in r45ar.R45AR_PROBE_JS
    assert "textRectExact" in r45ar.R45AR_PROBE_JS


if __name__ == "__main__":
    test_contract_and_static_assets()
    print("profile_media_facebook_ordered_exhaust_r45ar_test: PASS")
