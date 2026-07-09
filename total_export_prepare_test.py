from pathlib import Path
from tempfile import TemporaryDirectory

from capture_options import CAPTURE_ARCHIVE_CHECK, CAPTURE_COMMENTS
from source_capture_plan import PLAN_STATUS_READY, PLAN_STATUS_UNSUPPORTED_SOURCE
from total_export_manifest import read_manifest_json
from total_export_prepare import prepare_total_export_with_summary
from total_export_inventory_report import write_total_export_inventory_report_file
from total_export_readme import write_total_export_readme_file
from total_export_summary import write_workflow_summary_file


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        prepared = prepare_total_export_with_summary(
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
            package_id="prepared package",
            create_asset_folders=False,
        )
        workflow = prepared.workflow_result
        assert workflow.plan.status == PLAN_STATUS_READY
        assert workflow.plan.normalized_url == CANONICAL_URL
        assert Path(workflow.package_result.package_result.package_folder).is_dir()
        assert Path(workflow.package_result.manifest_path).is_file()
        assert Path(prepared.summary_file_result.summary_path).is_file()
        assert prepared.summary_file_result.registered
        assert prepared.readme_file_result is None
        assert prepared.inventory_report_file_result is None
        assert prepared.final_validation_result is not None
        assert prepared.final_validation_result.issues == ()
        assert prepared.warnings == (
            "Unknown capture options ignored: unknown_option",
            "Duplicate capture options ignored: comments",
        )

        summary_text = Path(prepared.summary_file_result.summary_path).read_text(encoding="utf-8")
        assert "Plan status: ready" in summary_text
        assert f"Manifest path: {workflow.package_result.manifest_path}" in summary_text

        manifest = read_manifest_json(workflow.package_result.manifest_path)
        assert manifest.source_urls == [CANONICAL_URL]
        assert manifest.capture_options == [CAPTURE_COMMENTS, CAPTURE_ARCHIVE_CHECK]
        assert len(manifest.assets) == 1
        assert manifest.assets[0].path == prepared.summary_file_result.asset_path

        repeated_summary = write_workflow_summary_file(workflow_result=workflow)
        assert repeated_summary.registered
        repeated_manifest = read_manifest_json(workflow.package_result.manifest_path)
        assert len(repeated_manifest.assets) == 1

        with_readme = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="prepared readme",
            create_asset_folders=False,
            write_readme=True,
        )
        assert with_readme.readme_file_result is not None
        assert Path(with_readme.readme_file_result.readme_path).is_file()
        assert with_readme.readme_file_result.registered
        assert with_readme.final_validation_result is not None
        assert with_readme.final_validation_result.issues == ()
        readme_manifest = read_manifest_json(with_readme.workflow_result.package_result.manifest_path)
        assert len(readme_manifest.assets) == 2

        with_inventory_report = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="prepared inventory report",
            create_asset_folders=False,
            write_inventory_report=True,
        )
        assert with_inventory_report.inventory_report_file_result is not None
        assert Path(with_inventory_report.inventory_report_file_result.report_path).is_file()
        assert with_inventory_report.inventory_report_file_result.registered
        assert with_inventory_report.final_validation_result is not None
        assert with_inventory_report.final_validation_result.issues == ()
        inventory_report_manifest = read_manifest_json(
            with_inventory_report.workflow_result.package_result.manifest_path
        )
        assert len(inventory_report_manifest.assets) == 2

        repeated_inventory_report = write_total_export_inventory_report_file(
            package_folder=(
                with_inventory_report.workflow_result.package_result.package_result.package_folder
            ),
            manifest_path=with_inventory_report.workflow_result.package_result.manifest_path,
            filename="TOTAL_EXPORT_INVENTORY.txt",
            register_in_manifest=True,
        )
        assert repeated_inventory_report.registered
        inventory_report_repeat_manifest = read_manifest_json(
            with_inventory_report.workflow_result.package_result.manifest_path
        )
        assert len(inventory_report_repeat_manifest.assets) == 2

        repeated_readme = write_total_export_readme_file(
            workflow_result=with_readme.workflow_result,
            filename="README_TOTAL_EXPORT.txt",
            register_in_manifest=True,
        )
        assert repeated_readme.registered
        readme_repeat_manifest = read_manifest_json(with_readme.workflow_result.package_result.manifest_path)
        assert len(readme_repeat_manifest.assets) == 2

        readme_unregistered = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="prepared readme unregistered",
            create_asset_folders=False,
            write_readme=True,
            register_readme_in_manifest=False,
        )
        assert readme_unregistered.readme_file_result is not None
        assert Path(readme_unregistered.readme_file_result.readme_path).is_file()
        assert not readme_unregistered.readme_file_result.registered
        readme_unregistered_manifest = read_manifest_json(
            readme_unregistered.workflow_result.package_result.manifest_path
        )
        assert len(readme_unregistered_manifest.assets) == 1

        inventory_report_unregistered = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="prepared inventory report unregistered",
            create_asset_folders=False,
            write_inventory_report=True,
            register_inventory_report_in_manifest=False,
        )
        assert inventory_report_unregistered.inventory_report_file_result is not None
        assert Path(inventory_report_unregistered.inventory_report_file_result.report_path).is_file()
        assert not inventory_report_unregistered.inventory_report_file_result.registered
        inventory_report_unregistered_manifest = read_manifest_json(
            inventory_report_unregistered.workflow_result.package_result.manifest_path
        )
        assert len(inventory_report_unregistered_manifest.assets) == 1

        skipped_validation = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="prepared skipped validation",
            create_asset_folders=False,
            validate_final_manifest=False,
        )
        assert skipped_validation.final_validation_result is None

        unregistered = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url=f"https://www.youtube.com/watch?v={VALID_ID}",
            selected_capture_options=["comments"],
            package_id="prepared unregistered",
            create_asset_folders=False,
            register_summary_in_manifest=False,
        )
        assert Path(unregistered.summary_file_result.summary_path).is_file()
        assert not unregistered.summary_file_result.registered
        unregistered_manifest = read_manifest_json(unregistered.workflow_result.package_result.manifest_path)
        assert unregistered_manifest.assets == []

        unsupported = prepare_total_export_with_summary(
            base_folder=temp_dir,
            source_url="https://example.com/article",
            source_label="Example article",
            selected_capture_options=["comments"],
            package_id="prepared unsupported",
            create_asset_folders=False,
            write_readme=True,
            write_inventory_report=True,
        )
        assert unsupported.workflow_result.plan.status == PLAN_STATUS_UNSUPPORTED_SOURCE
        assert Path(unsupported.workflow_result.package_result.package_result.package_folder).is_dir()
        assert Path(unsupported.summary_file_result.summary_path).is_file()
        assert unsupported.readme_file_result is not None
        assert unsupported.inventory_report_file_result is not None
        assert unsupported.final_validation_result is not None
        assert unsupported.final_validation_result.issues == ()
        unsupported_text = Path(unsupported.summary_file_result.summary_path).read_text(encoding="utf-8")
        assert "Plan status: unsupported_source" in unsupported_text
        unsupported_readme = Path(unsupported.readme_file_result.readme_path).read_text(encoding="utf-8")
        assert "Plan status: unsupported_source" in unsupported_readme
        unsupported_inventory_report = Path(
            unsupported.inventory_report_file_result.report_path
        ).read_text(encoding="utf-8")
        assert "Total Export Package Inventory" in unsupported_inventory_report
        assert unsupported.warnings == (
            "No source adapter supports the URL: https://example.com/article",
        )


if __name__ == "__main__":
    run_self_test()
    print("Total Export prepare self-test passed.")
