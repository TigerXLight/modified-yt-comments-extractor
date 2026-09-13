from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_source_row_evidence_bundle_plan_r42gk import (
    EVIDENCE_BUNDLE_PLAN_SCHEMA_FIELDS,
    R42GK_MARKER,
    R42GK_PASS_STATUS,
    SOURCE_ROW_INPUT_SCHEMA_FIELDS,
    SourceRowInput,
    build_evidence_bundle_plan_from_source_row,
    build_evidence_bundle_plan_report,
    build_planned_source_role_bridge,
    machine_url_fields_are_plain,
    url_like_review_strings_are_plain,
    validate_evidence_bundle_plan_report,
    write_report,
)


def _strings(plan) -> list[str]:
    return [item.value for item in plan.review_strings]


def test_source_row_input_schema_contains_required_fields() -> None:
    required = {
        "row_id",
        "raw_input",
        "source_url",
        "source_family_hint",
        "source_candidate_id",
        "capture_method_hint",
        "requires_review",
        "raw_row_payload",
    }
    assert required.issubset(set(SOURCE_ROW_INPUT_SCHEMA_FIELDS))


def test_evidence_bundle_plan_schema_contains_required_fields() -> None:
    required = {
        "schema_version",
        "plan_id",
        "source_family",
        "record_type",
        "canonical_url",
        "bundle_id",
        "root_output_path",
        "manifest_path",
        "review_strings_path",
        "expected_media_candidate_ids",
        "source_role_bridge_status",
        "promotion_status",
        "requires_manual_receipt",
        "capture_method_id",
        "side_effect_boundary",
        "no_jump_counter_safe",
    }
    assert required.issubset(set(EVIDENCE_BUNDLE_PLAN_SCHEMA_FIELDS))


def test_twitter_single_post_row_maps_to_bbc_bundle_and_meaningful_review_strings() -> None:
    row = SourceRowInput(
        row_id="row_bbc",
        raw_input="[Example](https://x.com/BBCr4today/status/2097217541416308845?s=20)",
        source_candidate_id="candidate:bbc",
    )
    plan = build_evidence_bundle_plan_from_source_row(row)
    strings = _strings(plan)

    assert plan.canonical_url == "https://x.com/BBCr4today/status/2097217541416308845"
    assert plan.raw_url == "https://x.com/BBCr4today/status/2097217541416308845"
    assert plan.bundle_id == "bundle:twitter_x:post:2097217541416308845"
    assert plan.requires_manual_receipt is True
    assert plan.requires_human_chain is True
    assert any(path.endswith("/post.json") for path in plan.expected_record_paths)
    assert any(path.path.endswith("/media/") for path in plan.expected_child_paths)
    assert any(path.path.endswith("/comments/") for path in plan.expected_child_paths)
    assert any(path.path.endswith("/replies/") for path in plan.expected_child_paths)
    assert "I think it carries a real risk of increased chances of attacks on the British Jewish community." in strings
    assert any("Dr Peter Prinsley" in item for item in strings)
    assert any("@bbcnickrobinson" in item for item in strings)
    assert any("Ed Miliband" in item for item in strings)
    assert any("West Bank settlements" in item for item in strings)
    assert machine_url_fields_are_plain(plan.to_dict())
    assert url_like_review_strings_are_plain((plan,))


def test_twitter_timeline_plan_keeps_examaddaorg_benchmark_context_only() -> None:
    row = SourceRowInput(row_id="row_exam", raw_input="https://x.com/examaddaorg?utm_source=test&s=20")
    plan = build_evidence_bundle_plan_from_source_row(row)
    strings = _strings(plan)

    assert plan.canonical_url == "https://x.com/examaddaorg"
    assert plan.bundle_id == "bundle:twitter_x:timeline:examaddaorg"
    assert plan.record_type == "timeline/account_export"
    assert any("6.7k records" in item and "not a hard-coded threshold" in item for item in strings)
    assert all("record_count=6700" not in item for item in strings)
    assert not hasattr(plan, "record_count")


def test_metro_news_article_plan_links_media_candidates_without_promotion() -> None:
    row = SourceRowInput(
        row_id="row_metro",
        raw_input="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
    )
    plan = build_evidence_bundle_plan_from_source_row(row)
    bridge = build_planned_source_role_bridge(plan)

    assert plan.bundle_id == "bundle:news_websites:article:metro_seagull_eater_20260717"
    assert plan.record_type == "article"
    assert any(path.kind == "archive" for path in plan.expected_child_paths)
    assert any(media_id.startswith("media:news_websites:") for media_id in plan.expected_media_candidate_ids)
    assert plan.promotion_status == "not_promoted_review_bridge_only"
    assert bridge.role_status == "compatible_bridge_not_role_assignment"
    assert bridge.role_hint == "none"


def test_global_player_public_audio_plan_preserves_r42gh_method_metadata() -> None:
    row = SourceRowInput(
        row_id="row_audio",
        raw_input="https://www.globalplayer.com/catchup/lbc/uk/episodes/2zGwFmzE7xNLAfiMVL5BMHmPeB/",
    )
    plan = build_evidence_bundle_plan_from_source_row(row)
    strings = _strings(plan)

    assert plan.bundle_id == "bundle:public_broadcast_catchup_audio:episode:2zGwFmzE7xNLAfiMVL5BMHmPeB"
    assert plan.capture_method_id == "yt_dlp_python_module"
    assert "yt_dlp_python_module" in plan.allowed_methods
    assert any(path.path.endswith("media/original.m4a") for path in plan.expected_child_paths)
    assert any(path.path.endswith("sidecars/info.json") for path in plan.expected_child_paths)
    assert "py -m yt_dlp" in strings
    assert "0" in strings
    assert "m4a" in strings
    assert "preserve_native_m4a_no_conversion" in strings


def test_unknown_private_rows_are_review_only_and_do_not_plan_execution() -> None:
    row = SourceRowInput(
        row_id="row_private",
        raw_input="https://private.example.local/protected",
        capture_mode_hint="private login blocked",
    )
    plan = build_evidence_bundle_plan_from_source_row(row)

    assert plan.record_type == "unknown_source_row"
    assert plan.promotion_status == "not_promoted_review_bridge_only"
    assert plan.access_status == "prohibited_no_bypass"
    assert plan.requires_login is True
    assert "live_browser" in plan.blocked_methods
    assert "yt_dlp" in plan.blocked_methods
    assert "jdownloader" in plan.blocked_methods


def test_review_string_index_and_source_role_bridge_are_compatible_only() -> None:
    report = build_evidence_bundle_plan_report(".")
    assert report.status == R42GK_PASS_STATUS
    for bridge in report.sample_source_role_bridges:
        assert bridge["role_status"] == "compatible_bridge_not_role_assignment"
        assert bridge["promotion_status"] == "not_promoted_review_bridge_only"
        assert bridge["role_hint"] == "none"
        assert bridge["no_jump_counter_safe"] is True
    for link in report.sample_review_string_index_links:
        assert link["source_role_bridge_status"] == "compatible_bridge_not_role_assignment"


def test_machine_url_fields_and_url_like_review_strings_are_plain() -> None:
    report = validate_evidence_bundle_plan_report(".")
    plans = [build_evidence_bundle_plan_from_source_row(SourceRowInput(row_id=plan["row_id"], raw_input=plan["canonical_url"])) for plan in report.sample_plans]
    assert all(machine_url_fields_are_plain(plan.to_dict()) for plan in plans)
    assert url_like_review_strings_are_plain(plans)


def test_cli_report_writer_emits_marker_status_and_samples() -> None:
    report = build_evidence_bundle_plan_report(".")
    with tempfile.TemporaryDirectory() as tmp:
        output_root = Path(tmp)
        write_report(report, output_root)
        report_json = output_root / "R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_REPORT.json"
        report_md = output_root / "R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_REPORT.md"
        assert report_json.exists()
        assert report_md.exists()
        assert R42GK_MARKER in report_json.read_text(encoding="utf-8")
        assert R42GK_PASS_STATUS in report_md.read_text(encoding="utf-8")


def main() -> int:
    tests = [
        test_source_row_input_schema_contains_required_fields,
        test_evidence_bundle_plan_schema_contains_required_fields,
        test_twitter_single_post_row_maps_to_bbc_bundle_and_meaningful_review_strings,
        test_twitter_timeline_plan_keeps_examaddaorg_benchmark_context_only,
        test_metro_news_article_plan_links_media_candidates_without_promotion,
        test_global_player_public_audio_plan_preserves_r42gh_method_metadata,
        test_unknown_private_rows_are_review_only_and_do_not_plan_execution,
        test_review_string_index_and_source_role_bridge_are_compatible_only,
        test_machine_url_fields_and_url_like_review_strings_are_plain,
        test_cli_report_writer_emits_marker_status_and_samples,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("PASS_R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_BRIDGE_TESTS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
