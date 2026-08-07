from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_approved_release_cli import main


def _review_package():
    return {
        "schema_version": "source_evidence_review_v1",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "review_package_status": "READY_FOR_REVIEW_DECISION",
        "content_summary": {"title": "Fixture Story", "body_character_count": 123},
        "comment_summary": {"comment_count": 2, "reply_count": 1},
        "artifact_count": 2,
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_evidence_review"},
            {"role": "comments_json_or_text", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 52, "source_stage": "source_evidence_review"},
        ],
        "required_review_actions": ["verify_source_identity", "review_content_text", "decide_evidence_status"],
    }


def _review_decision():
    return {
        "schema_version": "source_evidence_review_decision_v1",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "decision": "APPROVED",
        "review_status": "APPROVED_FOR_RELEASE",
        "reviewer_id": "reviewer",
        "approved_for_release": True,
        "revision_required": False,
        "completed_action_ids": ["verify_source_identity", "review_content_text", "decide_evidence_status"],
        "missing_required_action_ids": [],
        "review_notes": ["Approved after artifact review."],
    }


def _release_handoff():
    return {
        "schema_version": "source_evidence_review_release_handoff_v1",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "handoff_status": "READY_FOR_APPROVED_RELEASE",
        "required_next_stage": "source_approved_release",
        "decision": "APPROVED",
        "release_inputs": [
            {"role": "source_evidence_review_package", "id": "fixture_adapter.evidence_review.1234", "filename_hint": "review.json"},
            {"role": "source_evidence_review_decision", "id": "fixture_adapter.evidence_review.1234", "filename_hint": "decision.json"},
        ],
    }



def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def test_source_approved_release_cli_writes_outputs() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_json = root / "review_package.json"
        decision_json = root / "review_decision.json"
        handoff_json = root / "release_handoff.json"
        out = root / "out"
        _write(package_json, _review_package())
        _write(decision_json, _review_decision())
        _write(handoff_json, _release_handoff())
        rc = main([
            "--evidence-review-package-json", str(package_json),
            "--evidence-review-decision-json", str(decision_json),
            "--release-handoff-json", str(handoff_json),
            "--releaser-id", "release_operator",
            "--release-note", "Ready for shared release index.",
            "--output-dir", str(out),
        ])
        assert rc == 0
        assert len(list(out.glob("*.json"))) == 4


if __name__ == "__main__":
    test_source_approved_release_cli_writes_outputs()
    print("Source Approved Release CLI self-test passed.")
