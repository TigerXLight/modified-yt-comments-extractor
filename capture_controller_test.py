from capture_controller import (
    build_operational_capture_plan,
    format_operational_capture_plan_message,
)
from source_resource_state import build_discussion_capture_options, build_source_resource_row


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"


def test_operational_capture_plan_records_modes_without_execution() -> None:
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

    assert result.selected_modes == ("webpage", "comments")
    assert result.screenshot_intents == ("webpage", "comments")
    assert any("Livechat mode is selected" in warning for warning in result.warnings)
    assert result.action_events[0].result == "MODEL_ONLY"
    assert "no fetch" in result.scope
    assert "api_key" not in repr(result.to_dict())


def test_operational_capture_plan_message_is_user_facing_and_local_only() -> None:
    row = build_source_resource_row(MSN_URL)
    discussion = build_discussion_capture_options(
        (row,),
        selected_row_id=row.row_id,
        webpage_selected=True,
        comments_selected=False,
        livechat_selected=False,
        webpage_screenshot_requested=False,
        comments_screenshot_requested=False,
        livechat_screenshot_requested=False,
    )

    result = build_operational_capture_plan(row=row, discussion=discussion)
    message = format_operational_capture_plan_message(result)

    assert "Operational site-capture plan" in message
    assert "Selected modes: webpage" in message
    assert "Network actions performed: none" in message
    assert "Screenshots performed: none" in message
    assert "Downloads performed: none" in message
    assert "Archives performed: none" in message


def run_self_test() -> None:
    test_operational_capture_plan_records_modes_without_execution()
    test_operational_capture_plan_message_is_user_facing_and_local_only()


if __name__ == "__main__":
    run_self_test()
    print("Capture controller self-test passed.")
