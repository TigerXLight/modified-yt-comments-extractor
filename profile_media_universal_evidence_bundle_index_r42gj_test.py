from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_source_map_raw_url_audio_catchup_r42gh import GLOBAL_PLAYER_METHOD_METADATA, R42GH_PASS_STATUS, validate_source_map_raw_url_audio_catchup
from profile_media_universal_evidence_bundle_index_r42gj import (
    BUNDLE_MANIFEST_SCHEMA_FIELDS,
    EVIDENCE_RECORD_SCHEMA_FIELDS,
    PROMOTION_NONE,
    R42GJ_MARKER,
    R42GJ_PASS_STATUS,
    REVIEW_STRING_INDEX_SCHEMA_FIELDS,
    SOURCE_ROLE_BRIDGE_SCHEMA_FIELDS,
    EvidenceBundleManifest,
    ReviewStringIndex,
    SourceRoleBridgeRecord,
    UniversalEvidenceRecord,
    build_global_player_audio_record,
    build_news_article_record,
    build_report,
    build_sample_bundles,
    build_sample_records,
    build_sample_review_indexes,
    build_sample_source_role_bridges,
    build_twitter_single_post_record,
    build_twitter_timeline_record,
    machine_url_fields_are_plain,
    main,
    render_twitter_post_card,
    url_like_review_strings_are_plain,
)
from profile_media_universal_media_method_matrix_r42gi import R42GI_PASS_STATUS, build_global_player_media_candidate, validate_universal_media_method_matrix
from profile_media_universal_source_map_r42gg import R42GG_PASS_STATUS, sanitize_source_url, validate_universal_source_map


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_all_schema_fields_are_present() -> None:
    _assert(set(EVIDENCE_RECORD_SCHEMA_FIELDS).issubset(set(UniversalEvidenceRecord.__dataclass_fields__)), "evidence schema")
    _assert(set(BUNDLE_MANIFEST_SCHEMA_FIELDS).issubset(set(EvidenceBundleManifest.__dataclass_fields__)), "bundle schema")
    _assert(set(REVIEW_STRING_INDEX_SCHEMA_FIELDS).issubset(set(ReviewStringIndex.__dataclass_fields__)), "review index schema")
    _assert(set(SOURCE_ROLE_BRIDGE_SCHEMA_FIELDS).issubset(set(SourceRoleBridgeRecord.__dataclass_fields__)), "bridge schema")


def test_twitter_single_post_card_renders_requested_human_format() -> None:
    record = build_twitter_single_post_record()
    card = render_twitter_post_card(record)
    _assert(record.canonical_url == "https://x.com/BBCr4today/status/2097217541416308845", "canonical twitter URL")
    _assert(record.requires_manual_receipt is True, "single-post sample uses receipt/local exporter import contract")
    _assert("BBC Radio 4 Today" in card, "display name")
    _assert("@BBCr4today" in card, "handle")
    _assert("I think it carries a real risk of increased chances of attacks on the British Jewish community." in card, "quote text")
    _assert("Dr Peter Prinsley" in card, "Dr Peter Prinsley")
    _assert("@bbcnickrobinson" in card, "bbcnickrobinson")
    _assert("Ed Miliband" in card, "Ed Miliband")
    _assert("West Bank settlements" in card, "West Bank settlements")
    _assert("7:56 AM · Sep 8, 2026" in card, "created text")
    _assert("256K Views" in card, "views")
    _assert("309 comments 76 Retweets 92 Likes 40 Bookmarks" in card, "stats")
    _assert("Source URL: https://x.com/BBCr4today/status/2097217541416308845" in card, "source URL")
    _assert("Media folder: posts/2097217541416308845/media/" in card, "media folder")
    _assert("Comments folder: posts/2097217541416308845/comments/" in card, "comments folder")
    _assert("Replies folder: posts/2097217541416308845/replies/" in card, "replies folder")


def test_twitter_timeline_export_layout_keeps_dynamic_benchmark_context_non_hard_limit() -> None:
    record = build_twitter_timeline_record()
    bundles = {bundle.source_family: bundle for bundle in build_sample_bundles()}
    timeline = [bundle for bundle in build_sample_bundles() if bundle.bundle_id == "bundle:twitter_x:timeline:examaddaorg"][0]
    _assert(record.canonical_url == "https://x.com/examaddaorg", "timeline canonical URL")
    _assert("6.7k records" in record.text, "benchmark records")
    _assert("not a hard-coded threshold" in record.text, "not hard-coded")
    _assert(timeline.root_output_path.startswith("source_exports/twitter_x/examaddaorg/capture_"), "timeline root")
    _assert(timeline.record_count == 1, "sample manifest does not encode observed benchmark as fixed record count")
    _assert(timeline.records_index_path.endswith("records.ndjson"), "records index")
    _assert(bundles["twitter_x"].review_strings_path.endswith("review_strings.txt"), "review strings path")


def test_folder_layouts_for_news_article_and_audio_are_present() -> None:
    bundles = build_sample_bundles()
    roots = [bundle.root_output_path for bundle in bundles]
    _assert(any("source_exports/news_websites/metro.co.uk" in root for root in roots), "news article layout")
    _assert(any("source_exports/public_broadcast_catchup_audio/lbc" in root for root in roots), "audio layout")
    news = build_news_article_record()
    _assert("metro.co.uk" in news.canonical_url, "metro sample URL")


def test_global_player_lbc_audio_bundle_preserves_r42gh_method_metadata() -> None:
    record = build_global_player_audio_record()
    candidate = build_global_player_media_candidate()
    _assert(record.canonical_url == "https://globalplayer.com/catchup/lbc/uk/episodes/2zGwFmzE7xNLAfiMVL5BMHmPeB/", "global player canonical")
    _assert(str(GLOBAL_PLAYER_METHOD_METADATA["backend_id"]) == "yt_dlp_python_module", "backend id")
    _assert(str(GLOBAL_PLAYER_METHOD_METADATA["preferred_invocation"]) == "py -m yt_dlp", "invocation")
    _assert(str(GLOBAL_PLAYER_METHOD_METADATA["native_format_id_observed"]) == "0", "format id")
    _assert(str(GLOBAL_PLAYER_METHOD_METADATA["native_container"]) == "m4a", "native container")
    _assert(candidate.relative_output_path == "media/original.m4a", "candidate media path")
    _assert("sidecars/info.json" in candidate.sidecar_paths, "info sidecar")


def test_r42gi_media_candidates_link_into_evidence_records_without_promotion() -> None:
    records = build_sample_records()
    candidate_ids = {candidate_id for record in records for candidate_id in record.media_candidate_ids}
    _assert(build_global_player_media_candidate().candidate_id in candidate_ids, "global player candidate linked")
    for record in records:
        _assert(record.promotion_status == PROMOTION_NONE, f"record promoted: {record.evidence_id}")
        _assert(record.source_role_status == "compatible_bridge_not_role_assignment", "role status")


def test_review_string_index_includes_bridge_fields_and_plain_urls() -> None:
    records = build_sample_records()
    indexes = build_sample_review_indexes()
    all_strings = {value for index in indexes for value in index.strings}
    _assert("https://x.com/BBCr4today/status/2097217541416308845" in all_strings, "canonical URL")
    _assert("2097217541416308845" in all_strings, "status id")
    _assert("@BBCr4today" in all_strings, "handle")
    _assert("BBC Radio 4 Today" in all_strings, "display name")
    _assert(any("increased chances of attacks on the British Jewish community" in value for value in all_strings), "quote review string")
    _assert(any("Dr Peter Prinsley" in value for value in all_strings), "Dr Peter Prinsley review string")
    _assert(any("@bbcnickrobinson" in value for value in all_strings), "bbcnickrobinson review string")
    _assert(any("Ed Miliband" in value for value in all_strings), "Ed Miliband review string")
    _assert(any("West Bank settlements" in value for value in all_strings), "West Bank settlements review string")
    _assert(any("256K" in value for value in all_strings), "stats text")
    _assert(any("media:public_broadcast_catchup_audio" in value for value in all_strings), "media candidate id")
    _assert(url_like_review_strings_are_plain(indexes, records), "plain review URLs")


def test_source_role_bridge_is_compatible_but_not_assignment_engine() -> None:
    bridges = build_sample_source_role_bridges()
    for bridge in bridges:
        _assert(bridge.source_role_compatible is True, "compatible")
        _assert(bridge.no_jump_counter_safe is True, "no-jump safe")
        _assert(bridge.role_hint == "none", "no role hint")
        _assert(bridge.role_status == "compatible_bridge_not_role_assignment", "bridge role status")
        _assert(bridge.promotion_status == PROMOTION_NONE, "not promoted")
        _assert(bridge.requires_review is True, "review required")


def test_machine_url_fields_and_url_like_review_strings_are_plain() -> None:
    payloads = []
    payloads.extend(record.to_dict() for record in build_sample_records())
    payloads.extend(bundle.to_dict() for bundle in build_sample_bundles())
    payloads.extend(index.to_dict() for index in build_sample_review_indexes())
    payloads.extend(bridge.to_dict() for bridge in build_sample_source_role_bridges())
    for payload in payloads:
        _assert(machine_url_fields_are_plain(payload), f"markdown URL leaked: {payload}")


def test_prior_green_layers_import_and_still_report_pass() -> None:
    _assert(validate_universal_source_map(".").status == R42GG_PASS_STATUS, "R42GG")
    _assert(validate_source_map_raw_url_audio_catchup(".").status == R42GH_PASS_STATUS, "R42GH")
    _assert(validate_universal_media_method_matrix(".").status == R42GI_PASS_STATUS, "R42GI")


def test_r42gj_report_and_cli_emit_marker_and_pass_status() -> None:
    report = build_report(".")
    _assert(report.marker == R42GJ_MARKER, "marker")
    _assert(report.status == R42GJ_PASS_STATUS, report.status)
    checks = {check["name"]: check["status"] for check in report.checks}
    for name in (
        "evidence_record_schema_complete",
        "bundle_manifest_schema_complete",
        "review_string_index_schema_complete",
        "source_role_bridge_schema_complete",
        "twitter_single_post_card_layout_present",
        "twitter_timeline_layout_present",
        "news_article_layout_present",
        "public_audio_layout_present",
        "global_player_fixture_preserved",
        "r42gi_media_candidates_linked",
        "plain_machine_urls_not_markdown",
        "review_strings_bridge_required_fields",
        "metadata_review_blocked_not_promoted",
        "source_role_bridge_guardrail",
        "side_effect_boundary_declared",
        "prior_green_layers_import",
    ):
        _assert(checks.get(name) == "pass", f"check failed: {name}")
    with tempfile.TemporaryDirectory() as tmp:
        exit_code = main(["--source-root", ".", "--output-root", tmp])
        _assert(exit_code == 0, "CLI exit")
        report_path = Path(tmp) / "R42GJ_UNIVERSAL_EVIDENCE_BUNDLE_REVIEW_STRING_INDEX_REPORT.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        _assert(data["marker"] == R42GJ_MARKER, "CLI marker")
        _assert(data["status"] == R42GJ_PASS_STATUS, "CLI status")


def run_tests() -> None:
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"PASS {name}")


if __name__ == "__main__":
    run_tests()
