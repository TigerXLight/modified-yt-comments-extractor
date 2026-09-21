#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

SRC = Path(__file__).with_name("profile_media_facebook_safe_visual_topdown_r45at.py").read_text(encoding="utf-8")


def require(needle: str) -> None:
    assert needle in SRC, f"missing {needle!r}"


def test_contract_static_assets() -> None:
    require("YTCE_R45AT_SAFE_VISUAL_TOPDOWN_EXHAUST")
    require("PROFILE_NAV_BLOCKER_JS")
    require("R45AT_PROFILE_NAV_BLOCKER")
    require("profile_or_profile_comment_anchor_under_click_point")
    require("R45AT_UNSAFE_CLICK_POINT_BLOCKED")
    require("PASS_FULL_TOPDOWN_VISUAL_AUDIT_ZERO_VISIBLE_CONTROLS")
    # Regression guard: profile comment permalinks must not be exempted as safe expansion targets.
    bad_exemption = "! /permalink\\.php|story_fbid|comment_id=|reply_comment_id=/"
    assert bad_exemption not in SRC.replace(" ", ""), "profile comment_id/reply_comment_id exemption reintroduced"
    assert "comment_id" in SRC and "isProfileOrProfileCommentHref" in SRC


if __name__ == "__main__":
    test_contract_static_assets()
    print("profile_media_facebook_safe_visual_topdown_r45at_test: PASS")
