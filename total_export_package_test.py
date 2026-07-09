import json
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_package import create_total_export_package, ensure_folder


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        nested_folder = Path(temp_dir) / "manual" / "nested"
        assert ensure_folder(str(nested_folder)) == str(nested_folder)
        assert nested_folder.is_dir()

        unsafe_result = create_total_export_package(
            base_folder=temp_dir,
            source_label="YouTube",
            package_id=" My Package: Clip #1! ",
            selected_capture_options=("comments", "archive_check"),
            create_asset_folders=True,
        )
        assert unsafe_result.package_id == "My_Package_Clip_1"
        assert Path(unsafe_result.package_folder).is_dir()
        assert Path(unsafe_result.manifest_path).is_file()

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

        for subfolder in ["metadata", "page_capture", "media"]:
            assert not (Path(default_result.package_folder) / subfolder).exists()

        default_manifest = json.loads(
            Path(default_result.manifest_path).read_text(encoding="utf-8")
        )
        assert default_manifest["package_id"] == default_result.package_id
        assert default_manifest["capture_options"] == ["comments"]


if __name__ == "__main__":
    run_self_test()
    print("Total Export package self-test passed.")
