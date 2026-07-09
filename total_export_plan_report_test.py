from pathlib import Path
from tempfile import TemporaryDirectory

from source_capture_plan import PLAN_STATUS_UNSUPPORTED_SOURCE
from total_export_manifest import read_manifest_json
from total_export_plan_report import (
    DEFAULT_PLAN_REPORT_FILENAME,
    build_total_export_plan_report_text,
    write_total_export_plan_report_file,
)
from total_export_workflow import prepare_total_export_from_source


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def _posix_path(value: str) -> str:
    return (value or "").replace("\\", "/")


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        workflow = prepare_total_export_from_source(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
            source_label="YouTube clip",
            title="Clip Title",
            selected_capture_options=[
                "comments",
                "comments",
                "unknown_option",
            ],
            user_terms=["Caltheris"],
            package_id="plan report package",
            create_asset_folders=False,
        )
        text = build_total_export_plan_report_text(workflow)
        assert "Total Export Source Capture Plan" in text
        assert f"Source URL: https://www.youtube.com/watch?v={VALID_ID}&t=30s" in text
        assert f"Normalized URL: {CANONICAL_URL}" in text
        assert f"Source ID: {VALID_ID}" in text
        assert "Source label: YouTube clip" in text
        assert "Title: Clip Title" in text
        assert "Adapter name: youtube" in text
        assert "Adapter display name: YouTube" in text
        assert "Plan status: ready" in text
        assert "Selected capture options: comments" in text
        assert "Unknown capture options: unknown_option" in text
        assert "Duplicate capture options: comments" in text
        assert "Unknown capture options ignored: unknown_option" in text
        assert "- Caltheris" in text
        assert "does not prove content was fetched, captured, archived, downloaded, or transcribed" in text

        result = write_total_export_plan_report_file(workflow_result=workflow)
        assert result.registered
        assert result.manifest_path == workflow.package_result.manifest_path
        assert _posix_path(result.asset_path) == f"metadata/{DEFAULT_PLAN_REPORT_FILENAME}"
        assert Path(result.report_path).is_file()
        assert Path(result.report_path).name == DEFAULT_PLAN_REPORT_FILENAME
        assert Path(result.report_path).parent.name == "metadata"

        manifest = read_manifest_json(workflow.package_result.manifest_path)
        report_assets = [
            asset for asset in manifest.assets if _posix_path(asset.path) == _posix_path(result.asset_path)
        ]
        assert len(report_assets) == 1
        assert report_assets[0].sha256
        assert report_assets[0].size_bytes == Path(result.report_path).stat().st_size

        repeated = write_total_export_plan_report_file(workflow_result=workflow)
        assert repeated.registered
        repeated_manifest = read_manifest_json(workflow.package_result.manifest_path)
        repeated_report_assets = [
            asset for asset in repeated_manifest.assets if _posix_path(asset.path) == _posix_path(result.asset_path)
        ]
        assert len(repeated_report_assets) == 1

        unregistered_workflow = prepare_total_export_from_source(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="plan report unregistered",
            create_asset_folders=False,
        )
        unregistered = write_total_export_plan_report_file(
            workflow_result=unregistered_workflow,
            register_in_manifest=False,
        )
        assert not unregistered.registered
        assert Path(unregistered.report_path).is_file()
        unregistered_manifest = read_manifest_json(unregistered_workflow.package_result.manifest_path)
        assert unregistered_manifest.assets == []

        custom = write_total_export_plan_report_file(
            workflow_result=unregistered_workflow,
            filename=" Custom Plan: Review?.txt ",
            register_in_manifest=False,
        )
        assert Path(custom.report_path).name == "Custom_Plan_Review_.txt"

        unsupported = prepare_total_export_from_source(
            base_folder=temp_dir,
            source_url="https://example.com/article",
            source_label="Example article",
            selected_capture_options=["comments"],
            package_id="plan report unsupported",
            create_asset_folders=False,
        )
        assert unsupported.plan.status == PLAN_STATUS_UNSUPPORTED_SOURCE
        unsupported_result = write_total_export_plan_report_file(workflow_result=unsupported)
        unsupported_text = Path(unsupported_result.report_path).read_text(encoding="utf-8")
        assert "Plan status: unsupported_source" in unsupported_text
        assert "No source adapter supports the URL: https://example.com/article" in unsupported_text


if __name__ == "__main__":
    run_self_test()
    print("Total Export plan report self-test passed.")
