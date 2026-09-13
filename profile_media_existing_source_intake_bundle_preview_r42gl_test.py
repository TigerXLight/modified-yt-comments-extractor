from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_existing_source_intake_bundle_preview_r42gl import (
    DEFAULT_INVENTORY_FILES,
    R42GL_MARKER,
    R42GL_PASS_STATUS,
    build_existing_source_intake_preview_bridge_report,
    enrich_source_package_preview_payload_read_only,
    evidence_bundle_plan_preview_from_existing_source,
    inventory_existing_source_files,
    source_row_input_from_existing_shape,
    validate_existing_source_intake_preview_bridge_report,
    write_report,
)
from profile_media_source_package_preview import build_profile_media_source_package_preview
from source_resource_state import build_source_resource_row, parse_source_url_intake


def _preview_by_bundle(report, bundle_id: str) -> dict:
    for preview in report.sample_preview_plans:
        if preview["evidence_bundle_id"] == bundle_id:
            return dict(preview)
    raise AssertionError(f"missing bundle {bundle_id}")


def test_existing_source_intake_files_were_inventoried() -> None:
    inventory = inventory_existing_source_files(".")
    paths = {record.path for record in inventory}
    assert set(DEFAULT_INVENTORY_FILES).issubset(paths)
    assert all(record.exists for record in inventory)
    source_resource = next(record for record in inventory if record.path == "source_resource_state.py")
    assert "SourceResourceRowState" in source_resource.detected_symbols
    assert "parse_source_url_intake" in source_resource.detected_symbols
    package_preview = next(record for record in inventory if record.path == "profile_media_source_package_preview.py")
    assert "ProfileMediaSourcePackagePreview" in package_preview.detected_symbols
    assert "build_profile_media_source_package_preview" in package_preview.detected_symbols


def test_no_parallel_source_intake_model_created() -> None:
    module_text = Path("profile_media_existing_source_intake_bundle_preview_r42gl.py").read_text(encoding="utf-8")
    assert "class SourceRowInput" not in module_text
    assert "from profile_media_source_row_evidence_bundle_plan_r42gk import" in module_text
    assert "build_source_resource_row" in module_text
    assert "build_profile_media_source_package_preview" in module_text


def test_bridge_accepts_existing_source_resource_row_shape() -> None:
    row = build_source_resource_row("https://x.com/BBCr4today/status/2097217541416308845?s=20")
    source_row = source_row_input_from_existing_shape(row)
    preview = evidence_bundle_plan_preview_from_existing_source(row)
    assert source_row.source_family_hint == "twitter_x"
    assert preview["canonical_url"] == "https://x.com/BBCr4today/status/2097217541416308845"
    assert preview["evidence_bundle_id"] == "bundle:twitter_x:post:2097217541416308845"
    assert preview["preview_only"] is True
    assert preview["read_only_bridge"] is True
    assert any("Dr Peter Prinsley" in item for item in preview["review_string_index_link"]["records_by_string"])


def test_bridge_accepts_existing_source_url_intake_result_rows() -> None:
    result = parse_source_url_intake("https://x.com/examaddaorg https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/")
    assert len(result.rows) == 2
    previews = [evidence_bundle_plan_preview_from_existing_source(row) for row in result.rows]
    bundle_ids = {preview["evidence_bundle_id"] for preview in previews}
    assert "bundle:twitter_x:timeline:examaddaorg" in bundle_ids
    assert "bundle:news_websites:article:metro_seagull_eater_20260717" in bundle_ids


def test_read_only_enrichment_accepts_existing_source_package_preview_payload() -> None:
    preview = build_profile_media_source_package_preview(
        database_root="",
        case_title="R42GL read-only enrichment",
        source_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        canonical_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        source_title="People shout seagull eater at me in the street after far right lies",
        artifacts=({"kind": "article_text", "text_preview": "Picture: Supplied", "source_url": "https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/"},),
    )
    original = preview.batch_payload
    enriched = enrich_source_package_preview_payload_read_only(original)
    assert "evidence_bundle_plan_preview" not in original["source_package_preview"]
    bridge = enriched["source_package_preview"]["evidence_bundle_plan_preview"]
    assert bridge["evidence_bundle_id"] == "bundle:news_websites:article:metro_seagull_eater_20260717"
    assert bridge["promotion_status"] == "not_promoted_review_bridge_only"
    assert bridge["access_status"] == "metadata_only_until_marker_gated_capture"


def test_report_covers_required_sample_cases_and_guardrails() -> None:
    report = validate_existing_source_intake_preview_bridge_report(".")
    assert report.status == R42GL_PASS_STATUS
    bbc = _preview_by_bundle(report, "bundle:twitter_x:post:2097217541416308845")
    assert any("West Bank settlements" in item for item in bbc["review_string_index_link"]["records_by_string"])
    exam = _preview_by_bundle(report, "bundle:twitter_x:timeline:examaddaorg")
    assert all("record_count=6700" not in item for item in exam["review_string_index_link"]["records_by_string"])
    metro = _preview_by_bundle(report, "bundle:news_websites:article:metro_seagull_eater_20260717")
    assert metro["promotion_status"] == "not_promoted_review_bridge_only"
    assert metro["access_status"] == "metadata_only_until_marker_gated_capture"
    audio = _preview_by_bundle(report, "bundle:public_broadcast_catchup_audio:episode:2zGwFmzE7xNLAfiMVL5BMHmPeB")
    assert audio["capture_method_id"] == "yt_dlp_python_module"
    assert any(child["path"].endswith("media/original.m4a") for child in audio["expected_child_paths"])
    private = next(preview for preview in report.sample_preview_plans if preview["planned_record_type"] == "unknown_source_row")
    assert "live_browser" in private["blocked_methods"]
    assert private["promotion_status"] == "not_promoted_review_bridge_only"


def test_source_role_bridge_preview_is_compatible_not_assignment() -> None:
    report = build_existing_source_intake_preview_bridge_report(".")
    for bridge in report.sample_source_role_preview_bridges:
        assert bridge["role_status"] == "compatible_bridge_not_role_assignment"
        assert bridge["role_hint"] == "none"
        assert bridge["promotion_status"] == "not_promoted_review_bridge_only"
        assert bridge["no_jump_counter_safe"] is True


def test_plain_url_and_side_effect_boundaries() -> None:
    report = build_existing_source_intake_preview_bridge_report(".")
    for preview in report.sample_preview_plans:
        assert not str(preview["canonical_url"]).startswith("[")
        assert "](" not in str(preview["canonical_url"])
        assert not str(preview["raw_url"]).startswith("[")
        assert "](" not in str(preview["raw_url"])
        assert "no network fetch" in preview["side_effect_boundary"]
        assert preview["no_source_role_assignment"] is True
        assert preview["no_counter_no_jump_mutation"] is True


def test_cli_report_writer_outputs_required_files() -> None:
    report = build_existing_source_intake_preview_bridge_report(".")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_report(report, root)
        expected = {
            "R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT_REPORT.json",
            "R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT_REPORT.md",
            "R42GL_EXISTING_SOURCE_FILE_INVENTORY.json",
            "R42GL_SAMPLE_PREVIEW_PLANS.json",
            "R42GL_SAMPLE_SOURCE_ROLE_PREVIEW_BRIDGES.json",
            "R42GL_SAMPLE_REVIEW_STRING_PREVIEW_LINKS.json",
        }
        assert expected.issubset({path.name for path in root.iterdir()})
        assert R42GL_MARKER in (root / "R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT_REPORT.json").read_text(encoding="utf-8")


def main() -> int:
    tests = [
        test_existing_source_intake_files_were_inventoried,
        test_no_parallel_source_intake_model_created,
        test_bridge_accepts_existing_source_resource_row_shape,
        test_bridge_accepts_existing_source_url_intake_result_rows,
        test_read_only_enrichment_accepts_existing_source_package_preview_payload,
        test_report_covers_required_sample_cases_and_guardrails,
        test_source_role_bridge_preview_is_compatible_not_assignment,
        test_plain_url_and_side_effect_boundaries,
        test_cli_report_writer_outputs_required_files,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("PASS_R42GL_EXISTING_SOURCE_INTAKE_PREVIEW_BRIDGE_AUDIT_TESTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
