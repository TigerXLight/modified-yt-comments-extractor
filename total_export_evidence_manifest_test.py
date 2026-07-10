from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_bundle_index_reconcile import (
    BUNDLE_RECONCILE_STATUS_MISSING_EXPECTED_ZIP,
    BUNDLE_RECONCILE_STATUS_PRESENT,
    BUNDLE_RECONCILE_STATUS_UNEXPECTED_ZIP,
    BundleIndexReconciliationItem,
    BundleIndexReconciliationResult,
)
from total_export_evidence_manifest import (
    build_evidence_manifest,
    build_evidence_manifest_markdown,
    build_evidence_manifest_text,
    evidence_manifest_entry_to_dict,
    evidence_manifest_to_dict,
)
from total_export_local_media import build_local_media_record
from total_export_local_media_verify import (
    LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE,
    LOCAL_MEDIA_VERIFY_STATUS_VERIFIED,
    LocalMediaVerificationItem,
    LocalMediaVerificationResult,
)
from total_export_manual_archive import build_manual_archive_record
from total_export_preservation_plan import build_preservation_plan


VIDEO_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


def run_self_test() -> None:
    source_only = build_evidence_manifest(
        source_urls=(CANONICAL_URL, "https://example.com/source-only"),
    )
    assert source_only.entry_count == 2
    assert source_only.archive_record_count == 0
    assert source_only.local_media_record_count == 0
    assert source_only.sources_needing_follow_up_count == 2
    assert all(entry.needs_follow_up for entry in source_only.entries)

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        fake_media_path = root / "not-created.mp4"
        archive_record = build_manual_archive_record(
            source_url=f"https://youtu.be/{VIDEO_ID}?t=30",
            archive_url="https://web.archive.org/web/example",
            archive_status="manually_supplied",
        )
        media_record = build_local_media_record(
            source_url=CANONICAL_URL,
            package_id="example-package",
            local_media_path=str(fake_media_path),
            local_file_size_bytes=123,
            local_file_sha256="0" * 64,
            status="registered",
            inspect_local_file=False,
            compute_hash=False,
        )
        plan = build_preservation_plan(
            source_urls=(CANONICAL_URL,),
            manual_archive_records=(archive_record,),
            local_media_records=(media_record,),
        )
        assert plan.items[0].needs_archive_follow_up is False
        assert plan.items[0].needs_local_media_follow_up is False

        verification = LocalMediaVerificationResult(
            record_count=2,
            checked_count=2,
            missing_count=1,
            items=(
                LocalMediaVerificationItem(
                    source_url=CANONICAL_URL,
                    package_id="example-package",
                    local_media_path=str(fake_media_path),
                    status=LOCAL_MEDIA_VERIFY_STATUS_VERIFIED,
                ),
                LocalMediaVerificationItem(
                    package_id="example-package",
                    local_media_path=str(root / "missing.mp4"),
                    status=LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE,
                    warnings=("Registered local media path is missing.",),
                    recommended_actions=("Locate or re-register the local media file.",),
                ),
            ),
        )

        reconciliation = BundleIndexReconciliationResult(
            index_root_path=str(root),
            expected_count=2,
            present_expected_count=1,
            missing_expected_count=1,
            unexpected_zip_count=1,
            needs_follow_up_count=2,
            items=(
                BundleIndexReconciliationItem(
                    expected_zip_path=str(root / "present.zip"),
                    matched_zip_path=str(root / "present.zip"),
                    zip_filename="present.zip",
                    package_id="example-package",
                    source_url=CANONICAL_URL,
                    expected_present=True,
                    index_status="complete",
                    sidecar_ok=True,
                    needs_follow_up=False,
                    status=BUNDLE_RECONCILE_STATUS_PRESENT,
                ),
                BundleIndexReconciliationItem(
                    expected_zip_path=str(root / "missing.zip"),
                    zip_filename="missing.zip",
                    package_id="example-package",
                    source_url=CANONICAL_URL,
                    needs_follow_up=True,
                    status=BUNDLE_RECONCILE_STATUS_MISSING_EXPECTED_ZIP,
                    warnings=("Expected ZIP is missing locally.",),
                    recommended_actions=("Locate the expected local ZIP.",),
                ),
            ),
            unexpected_items=(
                BundleIndexReconciliationItem(
                    expected_zip_path="",
                    matched_zip_path=str(root / "unexpected.zip"),
                    zip_filename="unexpected.zip",
                    expected_present=False,
                    index_status="complete",
                    sidecar_ok=True,
                    needs_follow_up=True,
                    status=BUNDLE_RECONCILE_STATUS_UNEXPECTED_ZIP,
                    warnings=("Unexpected local ZIP requires review.",),
                ),
            ),
        )

        result = build_evidence_manifest(
            source_urls=(CANONICAL_URL,),
            manual_archive_records=(archive_record,),
            local_media_records=(media_record,),
            local_media_verification_result=verification,
            preservation_plan=plan,
            bundle_reconciliation_result=reconciliation,
        )

        assert result.entry_count == 2
        assert result.archive_record_count == 1
        assert result.local_media_record_count == 1
        assert result.local_media_verification_count == 2
        assert result.bundle_item_count == 3
        assert result.sources_needing_follow_up_count == 2

        source_entry = result.entries[0]
        assert source_entry.normalized_url == CANONICAL_URL
        assert source_entry.package_id == "example-package"
        assert source_entry.archive_record_count == 1
        assert source_entry.archive_statuses == ("manually_supplied",)
        assert source_entry.local_media_record_count == 1
        assert source_entry.local_media_statuses == ("registered",)
        assert source_entry.local_media_verification_statuses == (
            LOCAL_MEDIA_VERIFY_STATUS_VERIFIED,
            LOCAL_MEDIA_VERIFY_STATUS_MISSING_LOCAL_FILE,
        )
        assert source_entry.bundle_statuses == (
            BUNDLE_RECONCILE_STATUS_PRESENT,
            BUNDLE_RECONCILE_STATUS_MISSING_EXPECTED_ZIP,
        )
        assert source_entry.needs_follow_up is True
        assert "Registered local media path is missing." in source_entry.warnings
        assert "Expected ZIP is missing locally." in source_entry.warnings
        assert str(fake_media_path) in source_entry.local_reference_paths
        assert str(root / "present.zip") in source_entry.local_reference_paths

        unexpected_entry = result.entries[1]
        assert unexpected_entry.source_url == ""
        assert unexpected_entry.title == "unexpected.zip"
        assert unexpected_entry.bundle_statuses == (BUNDLE_RECONCILE_STATUS_UNEXPECTED_ZIP,)
        assert unexpected_entry.needs_follow_up is True

        entry_dict = evidence_manifest_entry_to_dict(source_entry)
        assert list(entry_dict) == [
            "archive_record_count",
            "archive_statuses",
            "bundle_statuses",
            "local_media_record_count",
            "local_media_statuses",
            "local_media_verification_statuses",
            "local_reference_paths",
            "needs_follow_up",
            "normalized_url",
            "package_id",
            "recommended_actions",
            "source_url",
            "title",
            "warnings",
        ]
        result_dict = evidence_manifest_to_dict(result)
        assert list(result_dict) == [
            "archive_record_count",
            "bundle_item_count",
            "entries",
            "entry_count",
            "errors",
            "local_media_record_count",
            "local_media_verification_count",
            "sources_needing_follow_up_count",
            "warnings",
        ]
        assert result_dict == evidence_manifest_to_dict(
            build_evidence_manifest(
                source_urls=(CANONICAL_URL,),
                manual_archive_records=(archive_record,),
                local_media_records=(media_record,),
                local_media_verification_result=verification,
                preservation_plan=plan,
                bundle_reconciliation_result=reconciliation,
            )
        )

        text = build_evidence_manifest_text(result)
        assert "Manual local evidence package manifest" in text
        assert "Entry count: 2" in text
        assert "missing_local_file" in text
        assert "missing_expected_zip" in text
        assert "Warnings:" in text
        assert "Recommended actions:" in text
        assert "no file copying, package building, ZIP creation/extraction" in text
        assert "not proof of remote deletion" in text

        markdown = build_evidence_manifest_markdown(result)
        assert "# Manual Local Evidence Package Manifest" in markdown
        assert "| Source/package | Archive records/statuses | Local media records/statuses | Verification statuses | Bundle statuses | Local reference paths | Follow-up | Recommended actions |" in markdown
        assert "## Safety Notes" in markdown
        assert "does not open, copy, package, or extract" in markdown
        assert "No downloads, fetching, network/API/archive checks" in markdown

        assert tuple(root.iterdir()) == ()


if __name__ == "__main__":
    run_self_test()
    print("Local evidence package manifest self-test passed.")
