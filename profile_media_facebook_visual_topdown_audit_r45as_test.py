#!/usr/bin/env python3
from __future__ import annotations
import profile_media_facebook_visual_topdown_audit_r45as as r45as

def test_basics():
    c = r45as.contract()
    assert c["marker"] == "YTCE_R45AS_VISUAL_TOPDOWN_AUDIT_EXHAUST"
    assert c["hidden_platform_api_scraping_enabled"] is False
    assert c["browser_profile_file_parsing_enabled"] is False
    assert "full visible top-to-bottom audit" in c["success_rule"]
    assert r45as._clean_url("[https://x/a?b=1](https://x/a?b=1\\&c=2)") == "https://x/a?b=1&c=2"
    assert r45as._target_story("https://www.facebook.com/permalink.php?story_fbid=pfbidabc&id=123") == "pfbidabc"

if __name__ == "__main__":
    test_basics()
    print("profile_media_facebook_visual_topdown_audit_r45as_test: PASS")
