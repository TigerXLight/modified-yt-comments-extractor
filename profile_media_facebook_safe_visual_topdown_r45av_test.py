#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

SRC = Path(__file__).with_name("profile_media_facebook_safe_visual_topdown_r45av.py").read_text(encoding="utf-8")

def require(needle: str) -> None:
    assert needle in SRC, f"missing {needle!r}"

def test_contract_static_assets() -> None:
    require("YTCE_R45AV_SAFE_VISUAL_TOPDOWN_SEPARATED_BOX")
    require("PROFILE_NAV_BLOCKER_JS")
    require("R45AV_PROFILE_NAV_BLOCKER")
    require("profile_or_profile_comment_anchor_under_click_point")
    require("R45AV_UNSAFE_CLICK_POINT_SKIPPED")
    require("skipKeys")
    require("unsafe_skip_keys")
    require("PASS_FULL_TOPDOWN_VISUAL_AUDIT_ZERO_VISIBLE_CONTROLS")
    require("VISUAL_CLEAN_CSS")
    require("JS_MARK_AND_CLEAN_PRESERVED_COMMENTS")
    require("data-r45j-preserved-comments-root")
    require("r45l_comment_column_crop_used")
    require("facebook_preserved_visual_comments_column.png")
    require("capture_separated_comments_box")
    bad_exemption = "! /permalink\.php|story_fbid|comment_id=|reply_comment_id=/"
    assert bad_exemption not in SRC.replace(" ", ""), "profile comment_id/reply_comment_id exemption reintroduced"
    assert "comment_id" in SRC and "isProfileOrProfileCommentHref" in SRC

if __name__ == "__main__":
    test_contract_static_assets()
    print("profile_media_facebook_safe_visual_topdown_r45av_test: PASS")
