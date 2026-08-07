from __future__ import annotations

import json

from capture_msn_manual_approved_export_handoff import (
    MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STATUS_READY,
    build_msn_manual_approved_export_handoff,
    msn_manual_approved_export_handoff_to_json,
)


def _decision() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_evidence_review_decision_v1",
        "decision_id": "msn.queue.approved.1234",
        "queue_item_id": "msn.queue",
        "source_url": "https://www.msn.com/en-gb/news/example",
        "named_site": "msn",
        "named_action": "msn_manual_capture",
        "article_title": "Example MSN article",
        "reviewer_id": "operator",
        "review_decision": "APPROVED",
        "decision_status": "DECISION_READY",
        "approved_for_total_export": True,
        "issue_count": 0,
        "assets": [
            {"role": "article_text", "filename": "article.txt", "sha256": "a" * 64, "byte_count": 40},
            {"role": "comments_json", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 80},
        ],
        "evidence_queue_update": {"queue_item_id": "msn.queue", "queue_status": "REVIEW_APPROVED"},
        "total_export_handoff": {"queue_item_id": "msn.queue", "handoff_status": "READY_FOR_TOTAL_EXPORT"},
        "safety_flags": {
            "metadata_only_decision": True,
            "explicit_review_package_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_full_local_paths": True,
        },
    }


def main() -> None:
    store_report = {
        "stored_files": [
            {"role": "manifest", "filename": "manifest.json", "sha256": "c" * 64, "byte_count": 120},
        ]
    }
    handoff = build_msn_manual_approved_export_handoff(_decision(), package_store_report=store_report, operator_run_id="review_run_1")
    assert handoff.handoff_status == MSN_MANUAL_APPROVED_EXPORT_HANDOFF_STATUS_READY
    assert handoff.ready_for_total_export_release is True
    assert handoff.issue_count == 0
    assert len(handoff.assets) == 3
    assert handoff.evidence_queue_update["queue_status"] == "READY_FOR_TOTAL_EXPORT_RELEASE"
    payload = json.loads(msn_manual_approved_export_handoff_to_json(handoff))
    assert payload["handoff_hash"] == handoff.handoff_hash

    rejected = dict(_decision())
    rejected["review_decision"] = "REJECTED"
    blocked = build_msn_manual_approved_export_handoff(rejected)
    assert blocked.ready_for_total_export_release is False
    assert blocked.issue_count > 0
    print("MSN manual approved export handoff self-test passed.")


if __name__ == "__main__":
    main()
