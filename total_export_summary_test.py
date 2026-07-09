from pathlib import Path
from tempfile import TemporaryDirectory

from capture_options import CAPTURE_ARCHIVE_CHECK, CAPTURE_COMMENTS
from evidence_schema import EvidenceProvenance
from source_capture_plan import build_source_capture_plan
from total_export_manifest import ExportAsset, TotalExportManifest
from total_export_summary import (
    summarize_manifest_validation,
    summarize_source_capture_plan,
    summarize_total_export_manifest,
    summarize_total_export_workflow,
    write_text_summary,
)
from total_export_validation import (
    ManifestValidationIssue,
    ManifestValidationResult,
    VALIDATION_LEVEL_ERROR,
    VALIDATION_LEVEL_INFO,
    VALIDATION_LEVEL_WARNING,
)
from total_export_workflow import prepare_total_export_from_source


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    plan = build_source_capture_plan(
        source_url=f"https://youtu.be/{VALID_ID}?t=30s",
        source_label="Clip",
        title="Clip Title",
        selected_capture_options=["comments", "archive_check"],
        user_terms=["Caltheris"],
    )
    plan_summary = summarize_source_capture_plan(plan)
    assert "Status: ready" in plan_summary
    assert f"Normalized URL: {CANONICAL_URL}" in plan_summary
    assert "Adapter: youtube" in plan_summary
    assert "Selected capture options: comments, archive_check" in plan_summary
    assert "- Caltheris" in plan_summary

    unsupported_plan = build_source_capture_plan(source_url="https://example.com/article")
    unsupported_summary = summarize_source_capture_plan(unsupported_plan)
    assert "Status: unsupported_source" in unsupported_summary
    assert "No source adapter supports the URL: https://example.com/article" in unsupported_summary

    validation = ManifestValidationResult(
        manifest_path="manifest.json",
        package_folder="package",
        issues=(
            ManifestValidationIssue(
                VALIDATION_LEVEL_ERROR,
                "MISSING_PACKAGE_ID",
                "Manifest package_id is empty.",
                "package_id",
            ),
            ManifestValidationIssue(
                VALIDATION_LEVEL_WARNING,
                "ASSET_PATH_UNRESOLVED",
                "Asset path is unresolved.",
                "assets[0]",
            ),
            ManifestValidationIssue(
                VALIDATION_LEVEL_INFO,
                "NO_SOURCE_URLS",
                "Manifest has no source URLs recorded.",
                "source_urls",
            ),
        ),
    )
    validation_summary = summarize_manifest_validation(validation)
    assert "Issue count: 3" in validation_summary
    assert "Errors: 1" in validation_summary
    assert "Warnings: 1" in validation_summary
    assert "INFO NO_SOURCE_URLS" in validation_summary

    manifest = TotalExportManifest(
        package_id="summary-package",
        output_folder="package",
        source_urls=[CANONICAL_URL],
        capture_options=[CAPTURE_COMMENTS],
        assets=[ExportAsset(path="metadata/report.txt")],
        provenance_records=[EvidenceProvenance(source_url=CANONICAL_URL)],
        notes="Review note.",
    )
    manifest_summary = summarize_total_export_manifest(manifest)
    assert "Package ID: summary-package" in manifest_summary
    assert f"- {CANONICAL_URL}" in manifest_summary
    assert "- comments" in manifest_summary
    assert "Asset count: 1" in manifest_summary
    assert "Provenance count: 1" in manifest_summary

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
            package_id="summary workflow",
            create_asset_folders=False,
        )
        workflow_summary = summarize_total_export_workflow(workflow)
        assert "Total Export Workflow" in workflow_summary
        assert f"Manifest path: {workflow.package_result.manifest_path}" in workflow_summary
        assert "Plan status: ready" in workflow_summary
        assert "Unknown capture options ignored: unknown_option" in workflow_summary
        assert "Duplicate capture options ignored: comments" in workflow_summary

        summary_path = Path(temp_dir) / "summary.txt"
        written_path = write_text_summary("Summary text with Caltheris.", str(summary_path))
        assert written_path == str(summary_path)
        assert summary_path.read_text(encoding="utf-8") == "Summary text with Caltheris."


if __name__ == "__main__":
    run_self_test()
    print("Total Export summary self-test passed.")
