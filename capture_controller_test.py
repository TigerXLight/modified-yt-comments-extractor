from capture_controller import (
    _action_log_jsonl,
    build_operational_capture_plan,
    format_operational_capture_plan_message,
)
from capture_contracts import ARTIFACT_TYPE_ACTION_LOG
from capture_contracts import (
    ARTIFACT_TYPE_ACCESSIBILITY_TREE,
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_DOM_SNAPSHOT,
    ARTIFACT_TYPE_FINAL_DOM,
    ARTIFACT_TYPE_MHTML,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_SCREENSHOT,
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
    assert result.action_events[1].previous_event_hash == result.action_events[0].event_hash
    assert result.action_events[2].previous_event_hash == result.action_events[1].event_hash
    assert result.action_events[2].artifact_ids == (result.action_log_artifact.artifact_id,)
    assert [artifact.artifact_type for artifact in result.declared_artifacts] == [
        ARTIFACT_TYPE_RAW_HTML,
        ARTIFACT_TYPE_FINAL_DOM,
        ARTIFACT_TYPE_MHTML,
        ARTIFACT_TYPE_DOM_SNAPSHOT,
        ARTIFACT_TYPE_ACCESSIBILITY_TREE,
        ARTIFACT_TYPE_ARTICLE_TEXT,
        ARTIFACT_TYPE_PAGE_OUTLINE,
        ARTIFACT_TYPE_SCREENSHOT,
        ARTIFACT_TYPE_SCREENSHOT,
    ]
    assert result.declared_artifacts[-1].metadata["screenshot_intent"] == "comments"
    assert result.action_log_artifact.artifact_type == ARTIFACT_TYPE_ACTION_LOG
    assert result.action_log_artifact.metadata["network_actions_performed"] == "none"
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
    assert "Action log artifact: capture/" in message
    assert "Network actions performed: none" in message
    assert "Screenshots performed: none" in message
    assert "Downloads performed: none" in message
    assert "Archives performed: none" in message


def test_operational_capture_plan_action_log_artifact_is_deterministic_and_sanitized() -> None:
    row = build_source_resource_row(MSN_URL)
    discussion = build_discussion_capture_options(
        (row,),
        selected_row_id=row.row_id,
        webpage_selected=True,
        comments_selected=True,
        comments_screenshot_requested=True,
        livechat_selected=False,
        livechat_screenshot_requested=False,
    )

    first = build_operational_capture_plan(row=row, discussion=discussion)
    second = build_operational_capture_plan(row=row, discussion=discussion)

    assert first.action_log_artifact.sha256 == second.action_log_artifact.sha256
    assert first.action_log_artifact.relative_path == f"capture/{row.row_id}/action_log.jsonl"
    rendered = _action_log_jsonl(first.action_events)
    assert "api_key" not in rendered
    assert "authorization" not in rendered.lower()
    assert "write_performed\":false" in rendered
    assert "operational_capture_artifacts_declared" in rendered
    assert "playwright.chromium.launch" not in rendered
    assert "requests.get" not in rendered


def run_self_test() -> None:
    test_operational_capture_plan_records_modes_without_execution()
    test_operational_capture_plan_message_is_user_facing_and_local_only()
    test_operational_capture_plan_action_log_artifact_is_deterministic_and_sanitized()


if __name__ == "__main__":
    run_self_test()
    print("Capture controller self-test passed.")
