import json
from pathlib import Path
from tempfile import TemporaryDirectory

from capture_options import CAPTURE_ARCHIVE_CHECK, CAPTURE_COMMENTS
from source_capture_plan import (
    PLAN_STATUS_READY,
    PLAN_STATUS_UNSUPPORTED_SOURCE,
    build_source_capture_plan,
)
from total_export_package import create_total_export_package, ensure_folder
from total_export_package import create_total_export_package_from_plan
from total_export_manifest import read_manifest_json


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        nested_folder = Path(temp_dir) / "manual" / "nested"
        assert ensure_folder(str(nested_folder)) == str(nested_folder)
        assert nested_folder.is_dir()

        unsafe_result = create_total_export_package(
            base_folder=temp_dir,
            source_label="YouTube",
            package_id=" My Package: Clip #1! ",
            selected_capture_options=(
                " comments ",
                "archive_check",
                "comments",
                "unknown_option",
            ),
            create_asset_folders=True,
        )
        assert unsafe_result.package_id == "My_Package_Clip_1"
        assert Path(unsafe_result.package_folder).is_dir()
        assert Path(unsafe_result.manifest_path).is_file()
        assert unsafe_result.warnings == (
            "Unknown capture options ignored: unknown_option",
            "Duplicate capture options ignored: comments",
        )

        for subfolder in ["metadata", "page_capture", "media"]:
            assert (Path(unsafe_result.package_folder) / subfolder).is_dir()

        loaded_manifest = json.loads(
            Path(unsafe_result.manifest_path).read_text(encoding="utf-8")
        )
        assert loaded_manifest["package_id"] == "My_Package_Clip_1"
        assert loaded_manifest["output_folder"] == unsafe_result.package_folder
        assert loaded_manifest["capture_options"] == ["comments", "archive_check"]
        assert loaded_manifest["notes"] == "Source label: YouTube"

        default_result = create_total_export_package(
            base_folder=temp_dir,
            source_label="YouTube",
            selected_capture_options=("comments",),
            create_asset_folders=False,
        )
        assert default_result.package_id.startswith("total_export_YouTube_")
        assert default_result.package_id.endswith("Z")
        assert Path(default_result.package_folder).is_dir()
        assert Path(default_result.manifest_path).is_file()
        assert default_result.created_folders == (default_result.package_folder,)
        assert default_result.warnings == ()

        for subfolder in ["metadata", "page_capture", "media"]:
            assert not (Path(default_result.package_folder) / subfolder).exists()

        default_manifest = json.loads(
            Path(default_result.manifest_path).read_text(encoding="utf-8")
        )
        assert default_manifest["package_id"] == default_result.package_id
        assert default_manifest["capture_options"] == ["comments"]

        plan = build_source_capture_plan(
            source_url=f"https://youtu.be/{VALID_ID}?t=30s",
            source_label="Clip",
            title="Clip Title",
            selected_capture_options=[
                "comments",
                "archive_check",
                "comments",
                "unknown_option",
            ],
            user_terms=["Caltheris"],
        )
        plan_result = create_total_export_package_from_plan(
            base_folder=temp_dir,
            plan=plan,
            package_id="plan package",
            create_asset_folders=False,
        )
        assert plan.status == PLAN_STATUS_READY
        assert Path(plan_result.package_result.package_folder).is_dir()
        assert Path(plan_result.manifest_path).is_file()
        assert plan_result.plan_status == PLAN_STATUS_READY
        assert plan_result.warnings == (
            "Unknown capture options ignored: unknown_option",
            "Duplicate capture options ignored: comments",
        )

        plan_manifest = read_manifest_json(plan_result.manifest_path)
        assert plan_manifest.source_urls == [CANONICAL_URL]
        assert plan_manifest.capture_options == [CAPTURE_COMMENTS, CAPTURE_ARCHIVE_CHECK]
        assert len(plan_manifest.provenance_records) == 1
        assert plan_manifest.provenance_records[0].source_url == CANONICAL_URL
        assert plan_manifest.provenance_records[0].adapter_name == "youtube"
        assert plan_manifest.provenance_records[0].item_id == VALID_ID
        assert "Source Capture Plan status: ready" in plan_manifest.notes
        assert "adapter=YouTube" in plan_manifest.notes
        assert f"source_id={VALID_ID}" in plan_manifest.notes

        unsupported_plan = build_source_capture_plan(
            source_url="https://example.com/article",
            source_label="Example article",
            selected_capture_options=["comments"],
        )
        unsupported_result = create_total_export_package_from_plan(
            base_folder=temp_dir,
            plan=unsupported_plan,
            package_id="unsupported plan",
            create_asset_folders=False,
        )
        assert unsupported_plan.status == PLAN_STATUS_UNSUPPORTED_SOURCE
        assert unsupported_result.plan_status == PLAN_STATUS_UNSUPPORTED_SOURCE
        unsupported_manifest = read_manifest_json(unsupported_result.manifest_path)
        assert unsupported_manifest.source_urls == ["https://example.com/article"]
        assert unsupported_manifest.capture_options == [CAPTURE_COMMENTS]
        assert len(unsupported_manifest.provenance_records) == 1
        assert unsupported_manifest.provenance_records[0].source_url == "https://example.com/article"
        assert "Source Capture Plan status: unsupported_source" in unsupported_manifest.notes


if __name__ == "__main__":
    run_self_test()
    print("Total Export package self-test passed.")
