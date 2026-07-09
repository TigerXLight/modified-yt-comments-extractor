from pathlib import Path
from tempfile import TemporaryDirectory

from capture_options import CAPTURE_ARCHIVE_CHECK, CAPTURE_COMMENTS
from source_capture_plan import PLAN_STATUS_READY, PLAN_STATUS_UNSUPPORTED_SOURCE
from total_export_manifest import read_manifest_json
from total_export_workflow import prepare_total_export_from_source


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        result = prepare_total_export_from_source(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
            source_label="YouTube clip",
            title="Clip Title",
            selected_capture_options=[
                "comments",
                "archive_check",
                "comments",
                "unknown_option",
            ],
            user_terms=["Caltheris"],
            package_id="workflow package",
            create_asset_folders=False,
        )

        assert result.plan.status == PLAN_STATUS_READY
        assert result.plan.normalized_url == CANONICAL_URL
        assert Path(result.package_result.package_result.package_folder).is_dir()
        assert Path(result.package_result.manifest_path).is_file()
        assert not result.validation_result.has_errors
        assert result.warnings == (
            "Unknown capture options ignored: unknown_option",
            "Duplicate capture options ignored: comments",
        )

        manifest = read_manifest_json(result.package_result.manifest_path)
        assert manifest.source_urls == [CANONICAL_URL]
        assert manifest.capture_options == [CAPTURE_COMMENTS, CAPTURE_ARCHIVE_CHECK]
        assert len(manifest.provenance_records) == 1
        assert manifest.provenance_records[0].source_url == CANONICAL_URL

        unsupported = prepare_total_export_from_source(
            base_folder=temp_dir,
            source_url="https://example.com/article",
            source_label="Example article",
            selected_capture_options=["comments"],
            package_id="unsupported workflow",
            create_asset_folders=False,
        )
        assert unsupported.plan.status == PLAN_STATUS_UNSUPPORTED_SOURCE
        assert Path(unsupported.package_result.package_result.package_folder).is_dir()
        assert Path(unsupported.package_result.manifest_path).is_file()
        assert not unsupported.validation_result.has_errors
        assert unsupported.warnings == (
            "No source adapter supports the URL: https://example.com/article",
        )

        unsupported_manifest = read_manifest_json(unsupported.package_result.manifest_path)
        assert unsupported_manifest.source_urls == ["https://example.com/article"]
        assert unsupported_manifest.capture_options == [CAPTURE_COMMENTS]
        assert len(unsupported_manifest.provenance_records) == 1
        assert unsupported_manifest.provenance_records[0].source_url == "https://example.com/article"


if __name__ == "__main__":
    run_self_test()
    print("Total Export workflow self-test passed.")
