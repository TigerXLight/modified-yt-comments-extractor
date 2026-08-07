from __future__ import annotations

from source_archive_handoff import build_source_archive_handoff
from source_archive_handoff_test import _release_audit_report
from source_archive_handoff_verifier import verify_source_archive_handoff


def test_source_archive_handoff_verifier_accepts_good_outputs() -> None:
    outputs = build_source_archive_handoff(release_audit_report=_release_audit_report())
    verification = verify_source_archive_handoff(
        outputs.archive_handoff_package,
        outputs.provider_tasks,
        outputs.result_templates,
        outputs.result_intake_handoff,
    )
    assert verification["verified"] is True
    assert verification["issue_count"] == 0


def test_source_archive_handoff_verifier_rejects_started_task() -> None:
    outputs = build_source_archive_handoff(release_audit_report=_release_audit_report())
    tasks = dict(outputs.provider_tasks)
    task_items = [dict(item) for item in tasks["archive_tasks"]]
    task_items[0]["archive_submission_started"] = True
    tasks["archive_tasks"] = task_items
    verification = verify_source_archive_handoff(outputs.archive_handoff_package, tasks, outputs.result_templates, outputs.result_intake_handoff)
    assert verification["verified"] is False
    assert any("archive submission started" in issue for issue in verification["issues"])


def test_source_archive_handoff_verifier_rejects_prefilled_archive_url() -> None:
    outputs = build_source_archive_handoff(release_audit_report=_release_audit_report())
    templates = dict(outputs.result_templates)
    template_items = [dict(item) for item in templates["archive_result_templates"]]
    template_items[0]["archive_url"] = "https://archive.example/result"
    templates["archive_result_templates"] = template_items
    verification = verify_source_archive_handoff(outputs.archive_handoff_package, outputs.provider_tasks, templates, outputs.result_intake_handoff)
    assert verification["verified"] is False
    assert any("archive_url must be blank" in issue for issue in verification["issues"])


if __name__ == "__main__":
    test_source_archive_handoff_verifier_accepts_good_outputs()
    test_source_archive_handoff_verifier_rejects_started_task()
    test_source_archive_handoff_verifier_rejects_prefilled_archive_url()
    print("Source Archive Handoff verifier self-test passed.")
