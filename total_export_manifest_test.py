import hashlib
import json
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
from total_export_manifest import (
    ASSET_ARCHIVE_RESULT,
    ASSET_CSV_EXPORT,
    ASSET_EXCEL_EXPORT,
    ASSET_EXTRACTED_TEXT,
    ASSET_HTML_SNAPSHOT,
    ASSET_JSON_EXPORT,
    ASSET_MANIFEST,
    ASSET_MEDIA,
    ASSET_RAW_SIDECAR,
    ASSET_SCREENSHOT,
    ASSET_TEXT_EXPORT,
    ExportAsset,
    TotalExportManifest,
    asset_subfolder,
    default_package_folder,
    default_package_id,
    manifest_filename,
    read_manifest_json,
    safe_package_id,
    sha256_for_file,
    write_manifest_json,
)


def _assert_utc_timestamp(value: str) -> None:
    assert value.endswith("Z"), value
    assert "T" in value, value


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        assert safe_package_id(" YouTube Export: Clip #1 ") == "YouTube_Export_Clip_1"
        assert safe_package_id("a__b!!c") == "a_b_c"
        assert safe_package_id("") == "total_export"

        package_id = default_package_id("youtube")
        assert package_id.startswith("total_export_youtube_")
        assert package_id.endswith("Z")
        assert default_package_id().startswith("total_export_")

        package_folder = default_package_folder(temp_dir, "My Package!")
        assert package_folder == str(Path(temp_dir) / "My_Package")
        assert not Path(package_folder).exists()

        for asset_type in [
            ASSET_TEXT_EXPORT,
            ASSET_CSV_EXPORT,
            ASSET_EXCEL_EXPORT,
            ASSET_JSON_EXPORT,
            ASSET_MANIFEST,
            ASSET_ARCHIVE_RESULT,
            ASSET_RAW_SIDECAR,
        ]:
            assert asset_subfolder(asset_type) == "metadata"
        for asset_type in [ASSET_SCREENSHOT, ASSET_HTML_SNAPSHOT, ASSET_EXTRACTED_TEXT]:
            assert asset_subfolder(asset_type) == "page_capture"
        assert asset_subfolder(ASSET_MEDIA) == "media"
        assert asset_subfolder("unknown") == "assets"

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

        manifest_path = Path(temp_dir) / manifest_filename(manifest.package_id)
        written_path = write_manifest_json(manifest, str(manifest_path))
        assert written_path == str(manifest_path)
        assert manifest_path.is_file()

        loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert loaded_manifest["package_id"] == "test-package"
        assert loaded_manifest["assets"][0]["sha256"] == expected_hash
        assert loaded_manifest["provenance_records"][0]["source_url"] == provenance.source_url
        assert loaded_manifest["claim_notes"][0]["claim_text"] == claim_note.claim_text
        assert loaded_manifest["media_source_chain_notes"][0]["media_observed_on_url"]

        loaded_manifest["unknown_extra_key"] = "ignored"
        loaded_manifest["assets"][0]["unknown_asset_key"] = "ignored"
        manifest_path.write_text(
            json.dumps(loaded_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        round_trip_manifest = read_manifest_json(str(manifest_path))
        assert round_trip_manifest.package_id == "test-package"
        assert round_trip_manifest.source_urls == [provenance.source_url]
        assert round_trip_manifest.output_folder == temp_dir
        assert round_trip_manifest.capture_options == ["Comments", "Archive check"]
        assert round_trip_manifest.notes == "Self-test manifest only."
        assert len(round_trip_manifest.assets) == 1
        assert isinstance(round_trip_manifest.assets[0], ExportAsset)
        assert round_trip_manifest.assets[0].asset_type == "text"
        assert round_trip_manifest.assets[0].sha256 == expected_hash
        assert round_trip_manifest.assets[0].size_bytes == len(sample_bytes)
        assert round_trip_manifest.provenance_records[0].source_url == provenance.source_url
        assert round_trip_manifest.claim_notes[0].claim_text == claim_note.claim_text
        assert round_trip_manifest.media_source_chain_notes[0].media_observed_on_url


if __name__ == "__main__":
    run_self_test()
    print("Total Export manifest self-test passed.")
