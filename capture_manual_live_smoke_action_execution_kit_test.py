from __future__ import annotations

import json

from capture_manual_live_smoke_action_execution_kit import (
    build_manual_live_smoke_action_execution_kit,
    manual_live_smoke_action_execution_kit_to_json,
)


def test_execution_kit_contains_runnable_commands_and_msn_snippet() -> None:
    kit = build_manual_live_smoke_action_execution_kit(
        site_id="msn",
        action_id="msn_comments_shadow_root_capture",
        source_url="https://www.msn.com/en-gb/news/example",
        operator_intent="Run approved MSN comments smoke action.",
        file_prefix="msn_comments",
    )
    names = {file.file_name for file in kit.files}
    assert "msn_comments_run_approved_action.cmd" in names
    assert "msn_comments_collect_artifacts_template.cmd" in names
    assert "msn_comments_msn_comments_shadow_root_snippet.js" in names
    rendered = manual_live_smoke_action_execution_kit_to_json(kit)
    assert "%LOCALAPPDATA%" in rendered
    assert "APPROVE_MANUAL_LIVE_SMOKE_ACTIONS" in rendered
    assert "<role>=<artifact_file>" in rendered
    assert json.loads(rendered)["implementation_bundle"] is True
    assert "C:\\Users" not in rendered


def test_archive_action_gets_archive_template() -> None:
    kit = build_manual_live_smoke_action_execution_kit(
        site_id="generic_web",
        action_id="archive_submission_prepare",
        source_url="https://example.com/article",
        operator_intent="Prepare operator archive submission.",
        file_prefix="archive_action",
    )
    assert any(file.file_name == "archive_action_archive_result_template.json" for file in kit.files)


if __name__ == "__main__":
    test_execution_kit_contains_runnable_commands_and_msn_snippet()
    test_archive_action_gets_archive_template()
    print("Manual live smoke action execution kit self-test passed.")
