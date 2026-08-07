from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_release_index_cli import main


def _approved_release_package():
    return {
        "schema_version": "source_approved_release_v1",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "release_status": "READY_FOR_RELEASE_INDEX",
        "approved_by_review_decision": True,
        "content_summary": {"title": "Fixture Story"},
        "comment_summary": {"comment_count": 2},
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_approved_release"},
        ],
        "release_fingerprint": "f" * 16,
    }


def _approved_release_manifest():
    return {
        "schema_version": "source_approved_release_manifest_v1",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "manifest_status": "READY_FOR_RELEASE_INDEX",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "artifact_count": 1,
        "artifact_roles": ["article_html_or_text"],
        "release_fingerprint": "f" * 16,
    }


def _release_index_handoff():
    return {
        "schema_version": "source_approved_release_index_handoff_v1",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "handoff_status": "READY_FOR_RELEASE_INDEX",
        "required_next_stage": "source_release_index",
        "release_index_inputs": [],
    }


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def test_source_release_index_cli_writes_outputs() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        package_json = root / "approved_release_package.json"
        manifest_json = root / "approved_release_manifest.json"
        handoff_json = root / "release_index_handoff.json"
        out = root / "out"
        _write(package_json, _approved_release_package())
        _write(manifest_json, _approved_release_manifest())
        _write(handoff_json, _release_index_handoff())
        rc = main([
            "--approved-release-package-json", str(package_json),
            "--approved-release-manifest-json", str(manifest_json),
            "--release-index-handoff-json", str(handoff_json),
            "--indexer-id", "release_index_operator",
            "--release-note", "Ready for shared export bundle.",
            "--output-dir", str(out),
        ])
        assert rc == 0
        assert len(list(out.glob("*.json"))) == 4


if __name__ == "__main__":
    test_source_release_index_cli_writes_outputs()
    print("Source Release Index CLI self-test passed.")
