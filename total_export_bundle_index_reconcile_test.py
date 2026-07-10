import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_bundle_index import (
    BUNDLE_INDEX_STATUS_MISSING_SHA256_SIDECAR,
    BUNDLE_INDEX_STATUS_SHA256_MISMATCH,
    build_bundle_index,
)
from total_export_bundle_index_reconcile import (
    BUNDLE_RECONCILE_STATUS_MISSING_EXPECTED_ZIP,
    BUNDLE_RECONCILE_STATUS_PRESENT,
    BUNDLE_RECONCILE_STATUS_PRESENT_NEEDS_REVIEW,
    BUNDLE_RECONCILE_STATUS_UNEXPECTED_ZIP,
    ExpectedBundleEntry,
    build_bundle_index_reconciliation_markdown,
    build_bundle_index_reconciliation_text,
    build_expected_bundle_entries,
    bundle_index_reconciliation_item_to_dict,
    bundle_index_reconciliation_to_dict,
    reconcile_bundle_index,
)
from total_export_zip_sidecar import (
    build_zip_sha256_sidecar_text,
    default_zip_json_sidecar_path,
    default_zip_sha256_sidecar_path,
)


def _write_bundle(root: Path, name: str, *, sidecar_hash: str | None = None) -> Path:
    zip_path = root / name
    data = f"fake local bundle: {name}\n".encode("utf-8")
    zip_path.write_bytes(data)
    actual_hash = hashlib.sha256(data).hexdigest()
    selected_hash = actual_hash if sidecar_hash is None else sidecar_hash
    Path(default_zip_sha256_sidecar_path(str(zip_path))).write_text(
        build_zip_sha256_sidecar_text(str(zip_path), selected_hash),
        encoding="utf-8",
    )
    Path(default_zip_json_sidecar_path(str(zip_path))).write_text(
        json.dumps(
            {
                "zip_inspection": {
                    "entry_count": 1,
                    "file_entry_count": 1,
                    "status": "ok",
                    "zip_sha256": actual_hash,
                    "zip_size_bytes": zip_path.stat().st_size,
                }
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return zip_path


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        complete_zip = _write_bundle(root, "complete.zip")
        missing_sha_zip = _write_bundle(root, "missing_sha.zip")
        Path(default_zip_sha256_sidecar_path(str(missing_sha_zip))).unlink()
        mismatch_zip = _write_bundle(root, "mismatch.zip", sidecar_hash="0" * 64)
        unexpected_zip = _write_bundle(root, "unexpected.zip")
        missing_zip = root / "missing.zip"

        expected = build_expected_bundle_entries(
            [
                ExpectedBundleEntry(
                    expected_zip_path=str(complete_zip),
                    package_id="complete-package",
                    source_url="https://example.invalid/complete",
                    notes="Expected complete bundle.",
                ),
                str(missing_zip),
                str(missing_sha_zip),
                str(mismatch_zip),
            ]
        )
        assert len(expected) == 4
        assert expected[0].package_id == "complete-package"
        assert expected[1].expected_zip_path == str(missing_zip)

        index = build_bundle_index(str(root))
        result = reconcile_bundle_index(expected, index)

        assert result.expected_count == 4
        assert result.present_expected_count == 3
        assert result.missing_expected_count == 1
        assert result.unexpected_zip_count == 1
        assert result.needs_follow_up_count == 4

        by_name = {item.zip_filename: item for item in result.items}
        complete = by_name["complete.zip"]
        assert complete.status == BUNDLE_RECONCILE_STATUS_PRESENT
        assert complete.expected_present is True
        assert complete.sidecar_ok is True
        assert complete.needs_follow_up is False
        assert complete.package_id == "complete-package"

        missing = by_name["missing.zip"]
        assert missing.status == BUNDLE_RECONCILE_STATUS_MISSING_EXPECTED_ZIP
        assert missing.expected_present is False
        assert missing.needs_follow_up is True
        assert any("not present" in warning for warning in missing.warnings)

        missing_sha = by_name["missing_sha.zip"]
        assert missing_sha.status == BUNDLE_RECONCILE_STATUS_PRESENT_NEEDS_REVIEW
        assert missing_sha.index_status == BUNDLE_INDEX_STATUS_MISSING_SHA256_SIDECAR
        assert missing_sha.sidecar_ok is False
        assert any("SHA256 sidecar missing" in warning for warning in missing_sha.warnings)

        mismatch = by_name["mismatch.zip"]
        assert mismatch.status == BUNDLE_RECONCILE_STATUS_PRESENT_NEEDS_REVIEW
        assert mismatch.index_status == BUNDLE_INDEX_STATUS_SHA256_MISMATCH
        assert any("does not match" in warning for warning in mismatch.warnings)

        unexpected = result.unexpected_items[0]
        assert unexpected.zip_filename == unexpected_zip.name
        assert unexpected.status == BUNDLE_RECONCILE_STATUS_UNEXPECTED_ZIP
        assert unexpected.needs_follow_up is True
        assert any("not in the expected" in warning for warning in unexpected.warnings)

        item_dict = bundle_index_reconciliation_item_to_dict(complete)
        assert list(item_dict) == [
            "expected_present",
            "expected_zip_path",
            "index_status",
            "matched_zip_path",
            "needs_follow_up",
            "notes",
            "package_id",
            "recommended_actions",
            "sidecar_ok",
            "source_url",
            "status",
            "warnings",
            "zip_filename",
        ]
        result_dict = bundle_index_reconciliation_to_dict(result)
        assert list(result_dict) == [
            "errors",
            "expected_count",
            "index_root_path",
            "items",
            "missing_expected_count",
            "needs_follow_up_count",
            "present_expected_count",
            "unexpected_items",
            "unexpected_zip_count",
            "warnings",
        ]
        assert result_dict == bundle_index_reconciliation_to_dict(
            reconcile_bundle_index(expected, index)
        )

        text = build_bundle_index_reconciliation_text(result)
        assert "Total Export bundle index reconciliation" in text
        assert "Expected count: 4" in text
        assert "Missing expected count: 1" in text
        assert "Unexpected ZIP count: 1" in text
        assert "missing_sha256_sidecar" in text
        assert "no ZIP extraction, network, archive checks, downloads" in text
        assert "not proof of deletion" in text

        markdown = build_bundle_index_reconciliation_markdown(result)
        assert "# Total Export Bundle Index Reconciliation" in markdown
        assert "| ZIP path | Status | Index status | Sidecars OK | Follow-up | Warnings | Recommended actions |" in markdown
        assert "sha256_mismatch" in markdown
        assert "No ZIP extraction is performed" in markdown


if __name__ == "__main__":
    run_self_test()
    print("Total Export bundle index reconciliation self-test passed.")
