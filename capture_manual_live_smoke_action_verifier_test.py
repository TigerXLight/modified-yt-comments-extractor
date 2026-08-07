from __future__ import annotations

from capture_manual_live_smoke_action_implementation import (
    build_manual_live_smoke_action_plan,
    execute_manual_live_smoke_action_plan,
    manual_live_smoke_action_plan_to_dict,
    manual_live_smoke_action_run_to_dict,
)
from capture_manual_live_smoke_action_verifier import (
    MANUAL_LIVE_SMOKE_ACTION_VERIFIER_NEEDS_REVIEW,
    MANUAL_LIVE_SMOKE_ACTION_VERIFIER_READY,
    verify_manual_live_smoke_action_payload,
)


def test_verifier_accepts_action_payload() -> None:
    plan = build_manual_live_smoke_action_plan(
        site_id="msn",
        action_id="msn_article_capture",
        source_url="https://www.msn.com/en-gb/news/example",
        operator_intent="Prepare action.",
    )
    run = execute_manual_live_smoke_action_plan(plan)
    report = verify_manual_live_smoke_action_payload({"plan": manual_live_smoke_action_plan_to_dict(plan), "run": manual_live_smoke_action_run_to_dict(run)})
    assert report.verdict == MANUAL_LIVE_SMOKE_ACTION_VERIFIER_READY
    assert report.issue_count == 0


def test_verifier_rejects_completion_claim() -> None:
    report = verify_manual_live_smoke_action_payload({"plan": {"safety_flags": []}, "run": {}, "note": "verified capture completed"})
    assert report.verdict == MANUAL_LIVE_SMOKE_ACTION_VERIFIER_NEEDS_REVIEW
    assert any(issue.code == "forbidden_completion_claim" for issue in report.issues)


if __name__ == "__main__":
    test_verifier_accepts_action_payload()
    test_verifier_rejects_completion_claim()
    print("Manual live smoke action verifier self-test passed.")
