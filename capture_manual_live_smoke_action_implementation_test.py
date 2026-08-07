from __future__ import annotations

import json

from capture_manual_live_smoke_action_implementation import (
    MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN,
    MANUAL_LIVE_SMOKE_ACTION_VERDICT_BLOCKED,
    MANUAL_LIVE_SMOKE_ACTION_VERDICT_DRY_RUN,
    MANUAL_LIVE_SMOKE_ACTION_VERDICT_READY,
    ManualLiveSmokeActionAdapter,
    build_manual_live_smoke_action_plan,
    execute_manual_live_smoke_action_plan,
    list_manual_live_smoke_actions,
    manual_live_smoke_action_plan_to_json,
    manual_live_smoke_action_run_to_json,
)


class FakeAdapter(ManualLiveSmokeActionAdapter):
    def __init__(self) -> None:
        self.opened: list[str] = []

    def open_browser(self, url: str) -> str:
        self.opened.append(url)
        return "fake_browser_opened"


def test_registry_contains_concrete_actions() -> None:
    actions = list_manual_live_smoke_actions()
    keys = {action["key"] for action in actions}
    assert "msn:msn_article_capture" in keys
    assert "msn:msn_comments_shadow_root_capture" in keys
    assert "generic_web:archive_submission_prepare" in keys
    assert any("comments_text" in action["required_artifact_roles"] for action in actions)


def test_dry_run_plan_has_steps_and_no_execution() -> None:
    plan = build_manual_live_smoke_action_plan(
        site_id="msn",
        action_id="msn_comments_shadow_root_capture",
        source_url="https://www.msn.com/en-gb/news/example",
        operator_intent="Capture named article comments after explicit operator review.",
        dry_run=True,
    )
    assert plan.verdict == MANUAL_LIVE_SMOKE_ACTION_VERDICT_DRY_RUN
    assert plan.execution_allowed is False
    assert any(step.kind == "browser_open" for step in plan.steps)
    assert any(artifact.role == "comments_text" and artifact.required for artifact in plan.artifact_contracts)
    payload = json.loads(manual_live_smoke_action_plan_to_json(plan))
    assert payload["source_url"] == "https://www.msn.com/en-gb/news/example"
    assert "no_completed_capture_claim" in payload["safety_flags"]

    fake = FakeAdapter()
    run = execute_manual_live_smoke_action_plan(plan, adapter=fake)
    assert fake.opened == []
    assert any(result.status == "DRY_RUN_SKIPPED" for result in run.step_results)
    assert "verified capture" not in manual_live_smoke_action_run_to_json(run).lower()


def test_non_dry_run_requires_approval() -> None:
    plan = build_manual_live_smoke_action_plan(
        site_id="generic_web",
        action_id="archive_submission_prepare",
        source_url="https://example.com/article",
        operator_intent="Prepare archive metadata.",
        dry_run=False,
    )
    assert plan.verdict == MANUAL_LIVE_SMOKE_ACTION_VERDICT_BLOCKED
    fake = FakeAdapter()
    run = execute_manual_live_smoke_action_plan(plan, adapter=fake)
    assert fake.opened == []
    assert any(result.status == "BLOCKED_PENDING_APPROVAL" for result in run.step_results)


def test_approved_non_dry_run_uses_adapter() -> None:
    plan = build_manual_live_smoke_action_plan(
        site_id="msn",
        action_id="msn_article_capture",
        source_url="https://www.msn.com/en-gb/news/example",
        operator_intent="Open target and collect article artifacts.",
        approval_token=MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN,
        dry_run=False,
    )
    assert plan.execution_allowed is True
    fake = FakeAdapter()
    run = execute_manual_live_smoke_action_plan(plan, adapter=fake)
    assert fake.opened == ["https://www.msn.com/en-gb/news/example"]
    assert run.verdict == MANUAL_LIVE_SMOKE_ACTION_VERDICT_READY
    assert any(result.status == "EXECUTED_OPERATOR_BROWSER_OPEN" for result in run.step_results)


def test_rejects_secret_like_values_and_full_paths() -> None:
    for bad in ("token=abc", "C:/Users/fahad/Desktop/source.html"):
        try:
            build_manual_live_smoke_action_plan(
                site_id="msn",
                action_id="msn_article_capture",
                source_url="https://example.com/article",
                operator_intent=bad,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe value should have been rejected: {bad}")


if __name__ == "__main__":
    test_registry_contains_concrete_actions()
    test_dry_run_plan_has_steps_and_no_execution()
    test_non_dry_run_requires_approval()
    test_approved_non_dry_run_uses_adapter()
    test_rejects_secret_like_values_and_full_paths()
    print("Manual live smoke action implementation self-test passed.")
