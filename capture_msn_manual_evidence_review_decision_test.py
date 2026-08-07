from __future__ import annotations

import json

from capture_msn_manual_evidence_review_decision import (
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED,
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_READY,
    build_msn_manual_evidence_review_decision,
    msn_manual_evidence_review_decision_to_json,
)


def _package() -> dict:
    actions = [
        "review_source_url_and_site",
        "review_article_extraction",
        "review_comments_extraction",
        "review_total_export_manifest",
        "review_asset_hashes",
        "approve_or_reject_queue_item",
    ]
    return {
        "schema_version": "msn_manual_evidence_review_package_v1",
        "queue_item_id": "msn_queue_001",
        "source_url": "https://www.msn.com/en-gb/news/example",
        "named_site": "msn",
        "named_action": "msn_manual_capture",
        "article_title": "Example title",
        "review_status": "REVIEW_PENDING",
        "source_issue_count": 0,
        "assets": [
            {"role": "article_text", "filename": "article.txt", "sha256": "a" * 64, "byte_count": 10},
            {"role": "comments_json", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 20},
            {"role": "manifest_json", "filename": "manifest.json", "sha256": "c" * 64, "byte_count": 30},
        ],
        "review_actions": [{"action_id": action, "label": action, "required": True, "completed": False} for action in actions],
        "safety_flags": {
            "metadata_only_review_package": True,
            "explicit_operator_artifacts_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_full_local_paths": True,
        },
    }


def test_approved_decision_requires_completed_actions() -> None:
    report = build_msn_manual_evidence_review_decision(
        _package(),
        review_decision=MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED,
        reviewer_id="reviewer-a",
    )
    assert report.approved_for_total_export is False
    assert report.issue_count == 1
    assert report.decision_status != MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_READY


def test_approved_decision_ready_when_actions_completed() -> None:
    package = _package()
    completed = [action["action_id"] for action in package["review_actions"]]
    report = build_msn_manual_evidence_review_decision(
        package,
        review_decision=MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED,
        reviewer_id="reviewer-a",
        completed_action_ids=completed,
        comments=["Reviewed explicit operator artifacts."],
    )
    assert report.approved_for_total_export is True
    assert report.issue_count == 0
    assert report.decision_status == MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_READY
    assert report.total_export_handoff["handoff_status"] == "READY_FOR_TOTAL_EXPORT"
    payload = json.loads(msn_manual_evidence_review_decision_to_json(report))
    assert payload["decision_id"].startswith("msn_queue_001.approved.")
    assert "reviewer-a" in payload["reviewer_id"]


if __name__ == "__main__":
    test_approved_decision_requires_completed_actions()
    test_approved_decision_ready_when_actions_completed()
    print("MSN manual Evidence Review decision self-test passed.")
