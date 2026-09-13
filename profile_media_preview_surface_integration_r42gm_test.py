from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_preview_surface_integration_r42gm import (
    EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD,
    EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD,
    R42GM_MARKER,
    R42GM_PASS_STATUS,
    build_preview_surface_payload,
    compact_evidence_bundle_plan_summary,
    enrich_source_package_preview_surface_read_only,
    preview_surface_payload_from_source_row,
    preview_surface_payload_from_source_url_intake,
    render_preview_surface_summary_text,
    validate_preview_surface_integration,
    write_report,
)
from profile_media_source_package_preview import build_profile_media_source_package_preview, source_package_preview_payload
from source_resource_state import build_source_resource_row, parse_source_url_intake


def test_existing_source_package_preview_can_be_enriched_read_only() -> None:
    preview = build_profile_media_source_package_preview(
        database_root="",
        case_title="R42GM package preview",
        source_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        canonical_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        source_title="People shout seagull eater at me in the street after far right lies",
        artifacts=({"kind": "article_text", "text_preview": "Picture: Supplied"},),
    )
    original_payload = source_package_preview_payload(preview)
    original_json = json.dumps(original_payload, sort_keys=True)
    enriched = enrich_source_package_preview_surface_read_only(original_payload)
    assert json.dumps(original_payload, sort_keys=True) == original_json
    original_section = original_payload["batch_payload"]["source_package_preview"]
    enriched_section = enriched["batch_payload"]["source_package_preview"]
    assert EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD not in original_section
    assert EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD in enriched_section
    assert "artifacts" in enriched_section
    assert "source_role_policy" in enriched_section
    assert enriched_section[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD]["evidence_bundle_id"] == "bundle:news_websites:article:metro_seagull_eater_20260717"
    assert enriched_section[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]["promotion_status"] == "not_promoted_review_bridge_only"
    assert enriched_section[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]["metadata_only_not_evidence"] is True


def test_existing_source_resource_row_surfaces_bundle_plan_preview() -> None:
    row = build_source_resource_row("https://x.com/BBCr4today/status/2097217541416308845?s=20")
    payload = preview_surface_payload_from_source_row(row)
    preview = payload[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD]
    summary = payload[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]
    assert payload["surface_kind"] == "source_row_preview"
    assert preview["canonical_url"] == "https://x.com/BBCr4today/status/2097217541416308845"
    assert preview["evidence_bundle_id"] == "bundle:twitter_x:post:2097217541416308845"
    assert preview["requires_manual_receipt"] is True
    assert preview["planned_source_role_bridge_status"] == "compatible_bridge_not_role_assignment"
    assert summary["source_role_assignment_performed"] is False
    assert any("Dr Peter Prinsley" in item for item in preview["review_string_index_link"]["records_by_string"])


def test_pasted_txt_batch_intake_rows_surface_preview_output() -> None:
    result = parse_source_url_intake(
        "https://x.com/BBCr4today/status/2097217541416308845\n"
        "https://x.com/examaddaorg?utm_source=test&s=20\n"
        "https://www.globalplayer.com/catchup/lbc/uk/episodes/2zGwFmzE7xNLAfiMVL5BMHmPeB/"
    )
    payload = preview_surface_payload_from_source_url_intake(result)
    assert payload["surface_kind"] == "source_url_intake_preview"
    assert payload["row_count"] == 3
    bundle_ids = {row[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD]["evidence_bundle_id"] for row in payload["rows"]}
    assert "bundle:twitter_x:post:2097217541416308845" in bundle_ids
    assert "bundle:twitter_x:timeline:examaddaorg" in bundle_ids
    assert "bundle:public_broadcast_catchup_audio:episode:2zGwFmzE7xNLAfiMVL5BMHmPeB" in bundle_ids


def test_global_player_metadata_is_preserved_in_preview_surface() -> None:
    payload = build_preview_surface_payload(
        {
            "row_id": "audio_row",
            "source_url": "https://www.globalplayer.com/catchup/lbc/uk/episodes/2zGwFmzE7xNLAfiMVL5BMHmPeB/",
            "source_title": "Global Player LBC public catch-up audio",
        }
    )
    preview = payload[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD]
    summary = payload[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]
    assert preview["source_family"] == "public_broadcast_catchup_audio"
    assert preview["capture_method_id"] == "yt_dlp_python_module"
    assert summary["capture_method_id"] == "yt_dlp_python_module"
    assert any(child["path"].endswith("media/original.m4a") for child in preview["expected_child_paths"])
    assert any(child["path"].endswith("sidecars/info.json") for child in preview["expected_child_paths"])
    strings = preview["review_string_index_link"]["records_by_string"]
    assert any("py -m yt_dlp" in value for value in strings)
    assert any("preserve_native_m4a_no_conversion" in value for value in strings)


def test_unknown_private_row_stays_review_only_and_non_promoted() -> None:
    payload = build_preview_surface_payload(
        {
            "row_id": "private_row",
            "source_url": "https://private.example.local/protected",
            "capture_mode_hint": "private login blocked",
            "requires_review": True,
        }
    )
    preview = payload[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD]
    summary = payload[EVIDENCE_BUNDLE_PLAN_SURFACE_FIELD]
    assert preview["planned_record_type"] == "unknown_source_row"
    assert preview["promotion_status"] == "not_promoted_review_bridge_only"
    assert preview["blocked_reason"] == "source_row_marked_private_login_blocked_or_prohibited"
    assert "live_browser" in preview["blocked_methods"]
    assert summary["requires_login"] is True
    assert summary["metadata_only_not_evidence"] is True


def test_examaddaorg_benchmark_context_is_not_hard_limit() -> None:
    payload = build_preview_surface_payload(build_source_resource_row("https://x.com/examaddaorg?utm_source=test&s=20"))
    preview = payload[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD]
    strings = preview["review_string_index_link"]["records_by_string"]
    assert preview["evidence_bundle_id"] == "bundle:twitter_x:timeline:examaddaorg"
    assert any("6.7k records" in item and "not a hard-coded threshold" in item for item in strings)
    assert all("record_count=6700" not in item for item in strings)


def test_plain_urls_and_review_strings_are_not_markdown_wrapped() -> None:
    payload = build_preview_surface_payload(build_source_resource_row("[Example](https://x.com/BBCr4today/status/2097217541416308845?s=20)"))
    preview = payload[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD]
    assert preview["canonical_url"] == "https://x.com/BBCr4today/status/2097217541416308845"
    assert not preview["canonical_url"].startswith("[")
    assert "](" not in preview["canonical_url"]
    values = preview["review_string_index_link"]["records_by_string"]
    assert all(not str(item).startswith("[") for item in values if str(item).startswith("http"))
    assert all("](" not in str(item) for item in values)


def test_compact_summary_and_text_renderer_expose_ui_surface_fields() -> None:
    payload = build_preview_surface_payload(build_source_resource_row("https://x.com/BBCr4today/status/2097217541416308845"))
    summary = compact_evidence_bundle_plan_summary(payload[EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD])
    text = render_preview_surface_summary_text(payload)
    assert summary["bundle_id"] == "bundle:twitter_x:post:2097217541416308845"
    assert summary["source_role_bridge_status"] == "compatible_bridge_not_role_assignment"
    assert "Evidence bundle plan preview" in text
    assert "Bundle ID: bundle:twitter_x:post:2097217541416308845" in text
    assert "Read-only preview: true" in text


def test_report_and_cli_writer_emit_required_outputs() -> None:
    report = validate_preview_surface_integration(".")
    assert report.status == R42GM_PASS_STATUS
    assert report.existing_files_edited is False
    assert report.preview_field_name == EVIDENCE_BUNDLE_PLAN_PREVIEW_FIELD
    assert any(item["bundle_id"] == "bundle:public_broadcast_catchup_audio:episode:2zGwFmzE7xNLAfiMVL5BMHmPeB" for item in report.compact_surface_summaries)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_report(report, root)
        expected = {
            "R42GM_PREVIEW_SURFACE_INTEGRATION_REPORT.json",
            "R42GM_PREVIEW_SURFACE_INTEGRATION_REPORT.md",
            "R42GM_SAMPLE_PREVIEW_PAYLOADS.json",
            "R42GM_COMPACT_SURFACE_SUMMARIES.json",
        }
        assert expected.issubset({path.name for path in root.iterdir()})
        report_json = (root / "R42GM_PREVIEW_SURFACE_INTEGRATION_REPORT.json").read_text(encoding="utf-8")
        assert R42GM_MARKER in report_json
        assert R42GM_PASS_STATUS in report_json


def main() -> int:
    tests = [
        test_existing_source_package_preview_can_be_enriched_read_only,
        test_existing_source_resource_row_surfaces_bundle_plan_preview,
        test_pasted_txt_batch_intake_rows_surface_preview_output,
        test_global_player_metadata_is_preserved_in_preview_surface,
        test_unknown_private_row_stays_review_only_and_non_promoted,
        test_examaddaorg_benchmark_context_is_not_hard_limit,
        test_plain_urls_and_review_strings_are_not_markdown_wrapped,
        test_compact_summary_and_text_renderer_expose_ui_surface_fields,
        test_report_and_cli_writer_emit_required_outputs,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("PASS_R42GM_PREVIEW_SURFACE_INTEGRATION_TESTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
