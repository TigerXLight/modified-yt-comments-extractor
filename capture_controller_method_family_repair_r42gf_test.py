from __future__ import annotations

from capture_controller import build_operational_capture_plan
from source_adapters import default_source_method_profile_for_adapter
from source_resource_state import build_discussion_capture_options, build_source_resource_row


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"


def test_msn_default_method_family_matches_operational_controller_contract() -> None:
    profile = default_source_method_profile_for_adapter("msn")

    assert profile.profile_id == "msn_article_comments_shadow_manual_import"
    assert profile.method_family == "article_comments_manual_observation"


def test_msn_operational_capture_plan_preserves_legacy_method_family_contract() -> None:
    row = build_source_resource_row(MSN_URL)
    discussion = build_discussion_capture_options(
        (row,),
        selected_row_id=row.row_id,
        webpage_selected=True,
        webpage_screenshot_requested=True,
        comments_selected=True,
        comments_screenshot_requested=True,
        livechat_selected=True,
        livechat_screenshot_requested=True,
    )

    result = build_operational_capture_plan(row=row, discussion=discussion)

    assert result.method_profile_id == "msn_article_comments_shadow_manual_import"
    assert result.method_profile_family == "article_comments_manual_observation"
    assert result.grabbed_source_record is not None
    assert result.grabbed_source_record.review_state == "USER_REVIEW_REQUIRED"
    assert result.grabbed_source_record.metadata_only is True
    assert result.grabbed_source_record.live_capture_performed is False
    assert "Livechat mode is selected" in " ".join(result.warnings)


def test_twitter_x_default_profile_remains_specialist_not_generic_article() -> None:
    profile = default_source_method_profile_for_adapter("twitter_x")

    assert profile.adapter_id == "twitter_x"
    assert profile.profile_id.startswith("twitter_x_")
    assert profile.method_family != "generic_article_html_manual_metadata"
    assert profile.method_family != "generic_article_comments_manual_metadata"


def run_self_test() -> None:
    test_msn_default_method_family_matches_operational_controller_contract()
    test_msn_operational_capture_plan_preserves_legacy_method_family_contract()
    test_twitter_x_default_profile_remains_specialist_not_generic_article()


if __name__ == "__main__":
    run_self_test()
    print("capture_controller_method_family_repair_r42gf_test OK")
