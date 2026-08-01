import json
from dataclasses import replace

from capture_live_smoke_plan import (
    MANUAL_ACTION_SCOPE_WEBPAGE,
    MSN_MANUAL_SMOKE_SITE_LABEL,
    MSN_MANUAL_SMOKE_SOURCE_URL,
    import_msn_article_manual_operator_observation_fixture,
)
from capture_msn_extraction_fields import (
    MSN_EXPORT_QUEUE_REVIEW_PROVENANCE_MANUAL_OPERATOR_ONLY,
    MSN_EXPORT_QUEUE_REVIEW_STATUS_USER_REVIEW_REQUIRED,
    MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT,
    MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY,
    build_export_review_item_from_msn_extraction_bundle,
    build_msn_manual_observation_extraction_review_bundle,
    msn_extraction_review_bundle_to_evidence_queue_item,
    msn_extraction_review_bundle_to_export_queue_metadata,
)
from evidence_item_queue import EvidenceItemRole, EvidenceItemStatus


def _imports():
    return import_msn_article_manual_operator_observation_fixture(
        observed_at_local_text="2026-07-17 14:44 GMT+1",
        operator_label="Fahad",
    )


def _metadata_only_bundle():
    return build_msn_manual_observation_extraction_review_bundle(
        manual_observation_imports=_imports(),
    )


def _local_supplied_bundle():
    return build_msn_manual_observation_extraction_review_bundle(
        manual_observation_imports=_imports(),
        supplied_article_text="Locally supplied MSN article text.",
        supplied_comment_records=(
            {
                "comment_id": "c1",
                "text": "Locally supplied comment.",
                "author": "Reader A",
            },
            {
                "comment_id": "c2",
                "text": "Locally supplied reply.",
                "author": "Reader B",
                "parent_id": "c1",
                "depth": 1,
            },
        ),
    )


def test_metadata_only_bundle_converts_to_queue_review_item_without_content_claims() -> None:
    item = build_export_review_item_from_msn_extraction_bundle(_metadata_only_bundle())
    data = item.to_dict()

    assert data["site_label"] == MSN_MANUAL_SMOKE_SITE_LABEL
    assert data["source_url"] == MSN_MANUAL_SMOKE_SOURCE_URL
    assert data["review_status"] == MSN_EXPORT_QUEUE_REVIEW_STATUS_USER_REVIEW_REQUIRED
    assert data["provenance_status"] == MSN_EXPORT_QUEUE_REVIEW_PROVENANCE_MANUAL_OPERATOR_ONLY
    assert data["manual_operator_only"] is True
    assert data["user_review_required"] is True
    assert data["article_section"]["has_article_text"] is False
    assert data["article_section"]["article_requires_manual_source_content"] is True
    assert (
        data["article_section"]["article_content_source"]
        == MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY
    )
    assert data["comments_section"]["has_extracted_comments"] is False
    assert data["comments_section"]["comment_count"] == 0
    assert data["comments_section"]["comments_panel_observed"] is True
    assert data["comments_section"]["comments_requires_manual_source_content"] is True
    assert data["media_section"]["static_media_observed"] is True
    assert data["export_review_section"]["queue_status"] == "USER_REVIEW_REQUIRED"


def test_local_supplied_content_converts_without_live_capture_claims() -> None:
    item = build_export_review_item_from_msn_extraction_bundle(_local_supplied_bundle())
    data = item.to_dict()
    rendered = json.dumps(data, sort_keys=True)

    assert data["article_section"]["has_article_text"] is True
    assert data["article_section"]["article_requires_manual_source_content"] is False
    assert (
        data["article_section"]["article_content_source"]
        == MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
    )
    assert data["comments_section"]["has_extracted_comments"] is True
    assert data["comments_section"]["comment_count"] == 2
    assert data["comments_section"]["comments_requires_manual_source_content"] is False
    assert (
        data["comments_section"]["comments_content_source"]
        == MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
    )
    assert data["review_status"] == "USER_REVIEW_REQUIRED"
    assert "completed_live_capture" not in rendered
    assert "LIVE_SITE_MANUALLY_VERIFIED" not in rendered


def test_section_separation_and_no_artifact_or_file_claims_are_preserved() -> None:
    data = build_export_review_item_from_msn_extraction_bundle(_metadata_only_bundle()).to_dict()

    assert "comment_count" not in data["article_section"]
    assert "has_article_text" not in data["comments_section"]
    assert "media_downloaded" not in data["article_section"]
    assert "media_downloaded" in data["media_section"]
    assert data["artifact_files_claimed"] is False
    assert data["file_existence_claimed"] is False
    assert data["live_verification_claimed"] is False
    assert data["automatic_classification"] is False
    assert data["browser_automation_claimed"] is False
    assert data["network_capture_claimed"] is False
    assert data["archive_provider_result_claimed"] is False
    assert data["downloaded_media_claimed"] is False
    assert data["screenshot_claimed"] is False
    assert data["ocr_claimed"] is False
    assert "artifact_paths" not in data
    assert "file_paths" not in data


def test_review_item_projects_to_evidence_queue_item_without_paths_or_timestamps() -> None:
    queue_item = msn_extraction_review_bundle_to_evidence_queue_item(_metadata_only_bundle())
    data = queue_item.to_dict()
    notes = json.loads(queue_item.user_notes)

    assert queue_item.item_role is EvidenceItemRole.MANUAL_EVIDENCE_NOTE
    assert queue_item.item_status is EvidenceItemStatus.NEEDS_REVIEW
    assert queue_item.source_url == MSN_MANUAL_SMOKE_SOURCE_URL
    assert queue_item.local_path == ""
    assert queue_item.file_hash == ""
    assert queue_item.created_at_utc == ""
    assert queue_item.updated_at_utc == ""
    assert data["local_path"] == ""
    assert notes["review_status"] == "USER_REVIEW_REQUIRED"
    assert notes["artifact_files_claimed"] is False
    assert "artifact_paths" not in notes


def test_existing_metadata_converter_includes_safe_queue_review_item() -> None:
    metadata = msn_extraction_review_bundle_to_export_queue_metadata(_metadata_only_bundle())
    review_item = metadata["queue_review_item"]

    assert metadata["export_queue_status"] == "user_review_required"
    assert metadata["artifact_file_claimed"] is False
    assert metadata["artifact_files_claimed"] is False
    assert metadata["file_existence_claimed"] is False
    assert metadata["automatic_classification_performed"] is False
    assert metadata["provider_or_archive_action"] == "none"
    assert metadata["network_actions_performed"] == "none"
    assert review_item["review_status"] == "USER_REVIEW_REQUIRED"
    assert review_item["export_review_section"]["artifact_files_claimed"] is False


def test_invalid_site_url_scope_and_unsafe_claims_are_rejected() -> None:
    bundle = _metadata_only_bundle()
    invalid_bundles = (
        replace(bundle, site_label="Other"),
        replace(bundle, source_url="https://www.msn.com/"),
        replace(bundle, manual_observation_scopes=("archive_manual_note",)),
        replace(bundle, artifact_files_claimed=True),
        replace(bundle, article={**dict(bundle.article), "claims_browser_automation": True}),
        replace(bundle, comments={**dict(bundle.comments), "claims_network_capture": True}),
        replace(bundle, media={**dict(bundle.media or {}), "claims_downloaded_files": True}),
        replace(bundle, media={**dict(bundle.media or {}), "downloaded_files_claimed": True}),
        replace(bundle, media={**dict(bundle.media or {}), "media_files_claimed": True}),
        replace(bundle, media={**dict(bundle.media or {}), "playback_capture_claimed": True}),
        replace(bundle, export_review={**dict(bundle.export_review or {}), "claims_file_exists": True}),
        replace(bundle, export_review={**dict(bundle.export_review or {}), "artifact_file_claimed": True}),
        replace(bundle, export_review={**dict(bundle.export_review or {}), "file_existence_claimed": True}),
        replace(bundle, export_review={**dict(bundle.export_review or {}), "claims_screenshot": True}),
        replace(bundle, export_review={**dict(bundle.export_review or {}), "claims_ocr": True}),
        replace(
            bundle,
            export_review={**dict(bundle.export_review or {}), "claims_archive_submission": True},
        ),
        replace(
            bundle,
            export_review={
                **dict(bundle.export_review or {}),
                "claims_credentials_cookies_accounts": True,
            },
        ),
        replace(
            bundle,
            export_review={
                **dict(bundle.export_review or {}),
                "claims_completed_live_verification": True,
            },
        ),
        replace(
            bundle,
            export_review={
                **dict(bundle.export_review or {}),
                "claims_automatic_evidence_classification": True,
            },
        ),
    )
    for invalid_bundle in invalid_bundles:
        try:
            build_export_review_item_from_msn_extraction_bundle(invalid_bundle)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe MSN extraction bundle should be rejected")


def test_manual_observation_builder_still_rejects_unapproved_claims_before_conversion() -> None:
    try:
        build_msn_manual_observation_extraction_review_bundle(
            manual_observation_imports=(
                {
                    "site_label": MSN_MANUAL_SMOKE_SITE_LABEL,
                    "source_url": MSN_MANUAL_SMOKE_SOURCE_URL,
                    "action_scope_id": MANUAL_ACTION_SCOPE_WEBPAGE,
                    "result_status": "observed",
                    "claims_file_artifacts": True,
                },
            )
        )
    except ValueError as exc:
        assert "claims_file_artifacts" in str(exc)
    else:
        raise AssertionError("manual observation file-artifact claims must be rejected")


def test_review_item_serialization_is_deterministic() -> None:
    bundle = _metadata_only_bundle()
    first = build_export_review_item_from_msn_extraction_bundle(bundle)
    second = build_export_review_item_from_msn_extraction_bundle(bundle)

    assert first.to_dict() == second.to_dict()
    assert first.to_evidence_queue_item().to_dict() == second.to_evidence_queue_item().to_dict()
    assert first.item_id == second.item_id
    assert first.observed_manual_scope_ids == tuple(sorted(first.observed_manual_scope_ids))
    assert first.approved_manual_scope_ids == tuple(sorted(first.approved_manual_scope_ids))


def run_self_test() -> None:
    test_metadata_only_bundle_converts_to_queue_review_item_without_content_claims()
    test_local_supplied_content_converts_without_live_capture_claims()
    test_section_separation_and_no_artifact_or_file_claims_are_preserved()
    test_review_item_projects_to_evidence_queue_item_without_paths_or_timestamps()
    test_existing_metadata_converter_includes_safe_queue_review_item()
    test_invalid_site_url_scope_and_unsafe_claims_are_rejected()
    test_manual_observation_builder_still_rejects_unapproved_claims_before_conversion()
    test_review_item_serialization_is_deterministic()


if __name__ == "__main__":
    run_self_test()
    print("Capture MSN extraction export queue self-test passed.")
