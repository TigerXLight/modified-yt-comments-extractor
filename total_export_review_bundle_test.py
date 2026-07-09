from pathlib import Path
from tempfile import TemporaryDirectory
import json

from total_export_review_bundle import (
    build_total_export_review_bundle,
    build_total_export_review_bundle_text,
    review_bundle_result_to_dict,
)


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        result = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
            source_label="YouTube clip",
            title="Clip Title",
            package_id="review bundle package",
            selected_capture_options=["comments"],
            user_terms=["Caltheris"],
            create_asset_folders=False,
        )
        assert Path(result.package_folder).is_dir()
        assert Path(result.manifest_path).is_file()
        assert Path(result.summary_path).is_file()
        assert Path(result.readme_path).is_file()
        assert Path(result.plan_report_path).is_file()
        assert Path(result.inventory_report_path).is_file()
        assert result.normalized_url == CANONICAL_URL
        assert result.package_inspection_status == "ok"
        assert result.package_manifest_valid is True
        assert Path(result.zip_path).is_file()
        assert result.zip_created is True
        assert result.zip_sha256
        assert result.zip_size_bytes == Path(result.zip_path).stat().st_size
        assert result.zip_inspection_status == "ok"
        assert result.zip_sidecar_sha256_written is True
        assert result.zip_sidecar_json_written is True
        assert Path(result.zip_sidecar_sha256_path).is_file()
        assert Path(result.zip_sidecar_json_path).is_file()
        assert result.final_validation_issue_count == 0
        assert result.errors == ()

        sidecar_json = json.loads(Path(result.zip_sidecar_json_path).read_text(encoding="utf-8"))
        assert sidecar_json["zip_inspection"]["status"] == "ok"

        repeated = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="review bundle package",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        assert repeated.zip_created is False
        assert repeated.errors
        assert any("already exists" in error for error in repeated.errors)

        overwritten = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="review bundle package",
            selected_capture_options=["comments"],
            create_asset_folders=False,
            overwrite_zip=True,
            overwrite_sidecars=True,
        )
        assert overwritten.zip_created is True
        assert overwritten.zip_sidecar_sha256_written is True
        assert overwritten.zip_sidecar_json_written is True
        assert overwritten.errors == ()

        no_sidecars = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="review bundle no sidecars",
            selected_capture_options=["comments"],
            create_asset_folders=False,
            write_sidecars=False,
        )
        assert no_sidecars.zip_created is True
        assert no_sidecars.zip_sidecar_sha256_path == ""
        assert no_sidecars.zip_sidecar_json_path == ""
        assert no_sidecars.zip_sidecar_sha256_written is False
        assert no_sidecars.zip_sidecar_json_written is False

        custom_zip_path = str(Path(temp_dir) / "custom" / "review_bundle.zip")
        custom = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="review bundle custom zip",
            selected_capture_options=["comments"],
            create_asset_folders=False,
            zip_path=custom_zip_path,
        )
        assert custom.zip_created is True
        assert custom.zip_path == custom_zip_path
        assert Path(custom_zip_path).is_file()

        entries_json_path = str(Path(temp_dir) / "entries" / "review_bundle.inspection.json")
        entries = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            package_id="review bundle entries",
            selected_capture_options=["comments"],
            create_asset_folders=False,
            zip_path=str(Path(temp_dir) / "entries" / "review_bundle.zip"),
            include_zip_entries=True,
            hash_zip_entries=True,
        )
        assert entries.zip_created is True
        assert entries.zip_sidecar_json_written is True
        assert entries.zip_sidecar_json_path.endswith(".inspection.json")
        entries_json_path = entries.zip_sidecar_json_path or entries_json_path
        entries_json = json.loads(Path(entries_json_path).read_text(encoding="utf-8"))
        assert any(
            entry["sha256"]
            for entry in entries_json["zip_inspection"]["entries"]
            if not entry["is_dir"]
        )

        unsupported = build_total_export_review_bundle(
            base_folder=temp_dir,
            source_url="https://example.com/article",
            source_label="Example article",
            package_id="review bundle unsupported",
            selected_capture_options=["comments"],
            create_asset_folders=False,
        )
        assert Path(unsupported.package_folder).is_dir()
        assert Path(unsupported.manifest_path).is_file()
        assert Path(unsupported.zip_path).is_file()
        assert unsupported.zip_created is True
        assert unsupported.package_inspection_status == "ok"
        assert unsupported.zip_inspection_status == "ok"
        assert "No source adapter supports the URL: https://example.com/article" in unsupported.warnings

        as_dict = review_bundle_result_to_dict(result)
        assert set(as_dict) == {
            "errors",
            "final_validation_issue_count",
            "inventory_report_path",
            "manifest_path",
            "normalized_url",
            "package_folder",
            "package_inspection_status",
            "package_manifest_valid",
            "plan_report_path",
            "readme_path",
            "source_url",
            "summary_path",
            "warnings",
            "zip_created",
            "zip_inspection_status",
            "zip_path",
            "zip_sha256",
            "zip_sidecar_json_path",
            "zip_sidecar_json_written",
            "zip_sidecar_sha256_path",
            "zip_sidecar_sha256_written",
            "zip_size_bytes",
        }
        assert as_dict["zip_created"] is True
        assert as_dict["zip_sha256"] == result.zip_sha256

        text = build_total_export_review_bundle_text(result)
        assert "Total Export review bundle" in text
        assert "Package inspection status: ok" in text
        assert "ZIP created: yes" in text
        assert "ZIP inspection status: ok" in text
        assert "ZIP SHA256 sidecar written: yes" in text


if __name__ == "__main__":
    run_self_test()
    print("Total Export review bundle self-test passed.")
