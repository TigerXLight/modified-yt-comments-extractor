import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from evidence_schema import (
    AccessMode,
    CaptureMethod,
    ClaimEvidenceNote,
    EvidenceProvenance,
    MediaSourceChainNote,
    SourceRole,
)
from total_export_manifest import ExportAsset, TotalExportManifest, sha256_for_file


def _assert_utc_timestamp(value: str) -> None:
    assert value.endswith("Z"), value
    assert "T" in value, value


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        asset_path = Path(temp_dir) / "sample.txt"
        sample_bytes = b"sample evidence\n"
        asset_path.write_bytes(sample_bytes)
        expected_hash = hashlib.sha256(sample_bytes).hexdigest()

        assert sha256_for_file(str(asset_path)) == expected_hash
        assert sha256_for_file(str(asset_path.with_name("missing.txt"))) == ""

        asset = ExportAsset(
            asset_type="text",
            path=str(asset_path),
            description="Sample extracted text",
            sha256=sha256_for_file(str(asset_path)),
            mime_type="text/plain",
            size_bytes=asset_path.stat().st_size,
        )
        _assert_utc_timestamp(asset.created_at_utc)
        assert asset.to_dict()["sha256"] == expected_hash

        provenance = EvidenceProvenance(
            source_url="https://www.youtube.com/watch?v=aB3_dE-9xYz",
            access_mode=AccessMode.PUBLIC_ACCESS,
            capture_method=CaptureMethod.API,
            source_role=SourceRole.PRIMARY_ORIGINAL_AUTHORED,
        )
        claim_note = ClaimEvidenceNote(claim_text="The source directly states a claim.")
        media_note = MediaSourceChainNote(media_observed_on_url=provenance.source_url)

        manifest = TotalExportManifest(
            package_id="test-package",
            source_urls=[provenance.source_url],
            output_folder=temp_dir,
            capture_options=["Comments", "Archive check"],
            assets=[asset],
            provenance_records=[provenance],
            claim_notes=[claim_note],
            media_source_chain_notes=[media_note],
            archive_results=[
                {
                    "archive_service": "wayback",
                    "archive_status": "not_checked",
                }
            ],
            notes="Self-test manifest only.",
        )
        manifest_dict = manifest.to_dict()
        _assert_utc_timestamp(manifest_dict["created_at_utc"])
        assert manifest_dict["assets"][0]["sha256"] == expected_hash
        assert manifest_dict["provenance_records"][0]["access_mode"] == "PUBLIC_ACCESS"
        assert manifest_dict["provenance_records"][0]["capture_method"] == "API"
        assert manifest_dict["claim_notes"][0]["claim_text"]
        assert manifest_dict["media_source_chain_notes"][0]["media_observed_on_url"]
        assert manifest_dict["archive_results"][0]["archive_service"] == "wayback"


if __name__ == "__main__":
    run_self_test()
    print("Total Export manifest self-test passed.")
