from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_release_audit_cli import main


def _release_index_record():
    return {
        "schema_version": "source_release_index_v1",
        "release_index_id": "fixture_adapter.release_index.1234",
        "release_index_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_release_index"},
        ],
        "release_fingerprint": "f" * 16,
        "index_fingerprint": "i" * 16,
    }


def _release_inventory():
    return {
        "schema_version": "source_release_inventory_v1",
        "release_index_id": "fixture_adapter.release_index.1234",
        "inventory_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "release_count": 1,
        "release_entries": [{"approved_release_id": "fixture_adapter.approved_release.1234"}],
    }


def _export_bundle_handoff():
    return {
        "schema_version": "source_release_export_bundle_handoff_v1",
        "release_index_id": "fixture_adapter.release_index.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "handoff_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "required_next_stage": "source_release_export_bundle",
        "release_export_inputs": [],
    }


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def test_source_release_audit_cli_writes_outputs() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        record_json = root / "release_index_record.json"
        inventory_json = root / "release_inventory.json"
        handoff_json = root / "export_bundle_handoff.json"
        out = root / "out"
        _write(record_json, _release_index_record())
        _write(inventory_json, _release_inventory())
        _write(handoff_json, _export_bundle_handoff())
        rc = main([
            "--release-index-record-json", str(record_json),
            "--release-inventory-json", str(inventory_json),
            "--export-bundle-handoff-json", str(handoff_json),
            "--auditor-id", "release_audit_operator",
            "--audit-note", "Ready for archive handoff.",
            "--output-dir", str(out),
        ])
        assert rc == 0
        assert len(list(out.glob("*.json"))) == 4


if __name__ == "__main__":
    test_source_release_audit_cli_writes_outputs()
    print("Source Release Audit CLI self-test passed.")
