from __future__ import annotations

import json

from source_named_site_method_packs import (
    build_msn_named_site_method_packs,
    build_source_named_site_method_pack_collection,
    source_named_site_method_pack_collection_to_json,
    validate_source_named_site_method_pack_collection,
)
from source_selector_approval_workflow import build_source_selector_approval_packet_collection
from source_site_method_audit_registry import build_source_site_method_audit_registry


def test_named_site_method_pack_collection_covers_current_site_method_registry() -> None:
    registry = build_source_site_method_audit_registry()
    collection = build_source_named_site_method_pack_collection(registry)

    assert collection.pack_count == registry.row_count
    assert collection.msn_pack_count == 2
    assert collection.twitter_x_pack_count == 2
    assert collection.youtube_pack_count == 2
    assert collection.generic_archive_pack_count == 5
    assert collection.selector_audit_required_count == 1
    assert collection.live_approved_only_count == 1
    assert collection.no_live_execution_status == "no_live_execution_performed"

    payload = collection.to_dict()
    validate_source_named_site_method_pack_collection(payload)
    assert payload["live_execution_performed"] is False
    assert payload["browser_automation_performed"] is False
    assert payload["provider_call_performed"] is False
    assert payload["archive_submission_performed"] is False
    assert payload["download_performed"] is False
    assert payload["file_move_performed"] is False
    assert payload["completed_evidence_claimed"] is False
    assert payload["automatic_classification"] is False


def test_named_site_method_packs_preserve_site_specific_metadata_and_boundaries() -> None:
    collection = build_source_named_site_method_pack_collection()
    packs_by_method = {pack.method_id: pack for pack in collection.packs}

    msn_comments = packs_by_method["msn_shadow_dom_comments"]
    assert msn_comments.site_specific_metadata["shadow_dom_host"] == "social-comment-wc"
    assert msn_comments.site_specific_metadata["shadow_dom_scroll_container"] == ".overlay-container"
    assert "comment_reference_ids" in msn_comments.source_record_typed_reference_mapping
    assert msn_comments.live_execution_performed is False

    twitter_thread = packs_by_method["twitter_x_reply_thread_archive_manual_import"]
    assert "thread_boundary" in twitter_thread.site_specific_metadata["expected_thread_metadata"]
    assert "archive.ph" in twitter_thread.site_specific_metadata["archive_fallback_providers"]
    assert twitter_thread.provider_call_performed is False

    youtube_media = packs_by_method["youtube_media_transcript"]
    assert youtube_media.site_specific_metadata["yt_dlp_ffmpeg_asr_performed"] is False
    assert "TRANSCRIPT_REFERENCE" in youtube_media.expected_artifact_refs

    generic_selector = packs_by_method["generic_comments_site_specific_selector"]
    assert generic_selector.selector_audit_required is True
    assert generic_selector.live_approved_only is True
    assert "site_specific_selector_audit_required" in generic_selector.exact_remaining_audit_blockers
    assert generic_selector.site_specific_metadata["universal_selector_support_claimed"] is False


def test_msn_named_site_method_packs_expose_article_and_shadow_dom_operator_paths() -> None:
    msn_packs = build_msn_named_site_method_packs()
    assert tuple(pack.method_id for pack in msn_packs) == ("msn_article", "msn_shadow_dom_comments")

    article = msn_packs[0]
    assert article.site_profile_id == "msn_article"
    assert "Android/Firefox responsive-design-mode" in article.site_specific_metadata[
        "manual_operator_notes"
    ][0]
    assert "RAW_HTML" in article.site_specific_metadata["article_html_snapshot_refs"]
    assert "SCREENSHOT" in article.site_specific_metadata["screenshot_snapshot_refs"]
    assert article.not_live_executed_status == "not_live_executed"
    assert article.completed_evidence_claimed is False

    comments = msn_packs[1]
    assert comments.site_profile_id == "msn_shadow_dom_comments"
    assert comments.site_specific_metadata["shadow_dom_host"] == "social-comment-wc"
    assert comments.site_specific_metadata["shadow_dom_scroll_container"] == ".overlay-container"
    assert any(
        ".overlay-container" in note for note in comments.site_specific_metadata["comment_selector_notes"]
    )
    assert comments.live_execution_performed is False
    assert comments.provider_call_performed is False


def test_named_site_method_packs_link_selector_approval_packet_ids() -> None:
    registry = build_source_site_method_audit_registry()
    approval_packets = build_source_selector_approval_packet_collection(registry)
    collection = build_source_named_site_method_pack_collection(
        registry,
        selector_approval_packets=approval_packets,
    )
    generic_selector = next(
        pack for pack in collection.packs if pack.method_id == "generic_comments_site_specific_selector"
    )

    assert len(generic_selector.selector_approval_packet_ids) == 1
    assert generic_selector.selector_approval_packet_ids[0].startswith("source_selector_approval_packet_")


def test_named_site_method_pack_json_is_deterministic_and_summary_only() -> None:
    first = build_source_named_site_method_pack_collection()
    second = build_source_named_site_method_pack_collection()

    first_json = source_named_site_method_pack_collection_to_json(first)
    second_json = source_named_site_method_pack_collection_to_json(second)
    assert first_json == second_json
    payload = json.loads(first_json)
    validate_source_named_site_method_pack_collection(payload)
    assert "C:\\" not in first_json
    assert "T:\\" not in first_json
    assert "completed_evidence_claimed" in first_json


if __name__ == "__main__":
    test_named_site_method_pack_collection_covers_current_site_method_registry()
    test_named_site_method_packs_preserve_site_specific_metadata_and_boundaries()
    test_msn_named_site_method_packs_expose_article_and_shadow_dom_operator_paths()
    test_named_site_method_packs_link_selector_approval_packet_ids()
    test_named_site_method_pack_json_is_deterministic_and_summary_only()
    print("source_named_site_method_packs_test.py passed")
