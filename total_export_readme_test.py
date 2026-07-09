from pathlib import Path
from tempfile import TemporaryDirectory

from capture_options import CAPTURE_ARCHIVE_CHECK, CAPTURE_COMMENTS
from source_capture_plan import PLAN_STATUS_UNSUPPORTED_SOURCE
from total_export_manifest import read_manifest_json
from total_export_readme import (
    build_total_export_readme_text,
    write_total_export_readme_file,
)
from total_export_workflow import prepare_total_export_from_source


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        workflow = prepare_total_export_from_source(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
            selected_capture_options=[
                "comments",
                "archive_check",
                "comments",
                "unknown_option",
            ],
            package_id="readme package",
            create_asset_folders=False,
        )
        readme_text = build_total_export_readme_text(workflow)
        assert "Total Export Package" in readme_text
        assert "Package ID: readme_package" in readme_text
        assert f"Source URL: https://www.youtube.com/watch?v={VALID_ID}&t=30s" in readme_text
        assert f"Normalized URL: {CANONICAL_URL}" in readme_text
        assert "Plan status: ready" in readme_text
        assert f"Selected capture options: {CAPTURE_COMMENTS}, {CAPTURE_ARCHIVE_CHECK}" in readme_text
        assert "local preparation shell" in readme_text
        assert "did not fetch comments, live chat, media, screenshots, archive captures" in readme_text
        assert "Unknown capture options ignored: unknown_option" in readme_text

        result = write_total_export_readme_file(
            workflow_result=workflow,
            filename=" Unsafe Readme: Clip #1?.txt ",
            register_in_manifest=True,
        )
        assert result.registered
        assert result.manifest_path == workflow.package_result.manifest_path
        assert result.asset_path == "Unsafe_Readme_Clip_1_.txt"
        assert Path(result.readme_path).parent == Path(workflow.package_result.package_result.package_folder)
        assert Path(result.readme_path).is_file()
        assert "Plan status: ready" in Path(result.readme_path).read_text(encoding="utf-8")

        manifest = read_manifest_json(workflow.package_result.manifest_path)
        assert len(manifest.assets) == 1
        assert manifest.assets[0].path == result.asset_path
        assert manifest.assets[0].sha256
        assert manifest.assets[0].size_bytes == Path(result.readme_path).stat().st_size

        repeated = write_total_export_readme_file(
            workflow_result=workflow,
            filename=" Unsafe Readme: Clip #1?.txt ",
            register_in_manifest=True,
        )
        assert repeated.registered
        repeated_manifest = read_manifest_json(workflow.package_result.manifest_path)
        assert len(repeated_manifest.assets) == 1
        assert repeated_manifest.assets[0].path == result.asset_path

        unregistered_workflow = prepare_total_export_from_source(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="readme unregistered",
            create_asset_folders=False,
        )
        unregistered = write_total_export_readme_file(
            workflow_result=unregistered_workflow,
            register_in_manifest=False,
        )
        assert not unregistered.registered
        assert Path(unregistered.readme_path).is_file()
        unregistered_manifest = read_manifest_json(unregistered_workflow.package_result.manifest_path)
        assert unregistered_manifest.assets == []

        unsupported = prepare_total_export_from_source(
            base_folder=temp_dir,
            source_url="https://example.com/article",
            selected_capture_options=["comments"],
            package_id="readme unsupported",
            create_asset_folders=False,
        )
        assert unsupported.plan.status == PLAN_STATUS_UNSUPPORTED_SOURCE
        unsupported_result = write_total_export_readme_file(workflow_result=unsupported)
        unsupported_text = Path(unsupported_result.readme_path).read_text(encoding="utf-8")
        assert "Plan status: unsupported_source" in unsupported_text
        assert "No source adapter supports the URL: https://example.com/article" in unsupported_text


if __name__ == "__main__":
    run_self_test()
    print("Total Export README self-test passed.")
