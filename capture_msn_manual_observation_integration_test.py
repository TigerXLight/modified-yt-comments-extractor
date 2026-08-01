import json

from capture_live_smoke_plan import (
    MANUAL_ACTION_SCOPE_ARCHIVE,
    MANUAL_ACTION_SCOPE_COMMENTS,
    MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
    MANUAL_ACTION_SCOPE_LIVECHAT,
    MANUAL_ACTION_SCOPE_MEDIA,
    MANUAL_ACTION_SCOPE_RENDERED_CITATION,
    MANUAL_ACTION_SCOPE_WARC_WACZ,
    MANUAL_ACTION_SCOPE_WEBPAGE,
    MSN_MANUAL_SMOKE_SITE_LABEL,
    MSN_MANUAL_SMOKE_SOURCE_URL,
    import_msn_article_manual_operator_observation_fixture,
)
from capture_msn_extraction_fields import (
    MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT,
    MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY,
    MSN_EXTRACTION_STATUS_NEEDS_MANUAL_SOURCE_CONTENT,
    build_msn_manual_observation_extraction_review_bundle,
    msn_extraction_review_bundle_to_export_queue_metadata,
)


def _imports():
    return import_msn_article_manual_operator_observation_fixture(
        observed_at_local_text="2026-07-17 14:44 GMT+1",
        operator_label="Fahad",
    )


def test_approved_manual_observation_integrates_as_review_bundle() -> None:
    bundle = build_msn_manual_observation_extraction_review_bundle(
        manual_observation_imports=_imports(),
    )
    data = bundle.to_dict()

    assert data["site_label"] == MSN_MANUAL_SMOKE_SITE_LABEL
    assert data["source_url"] == MSN_MANUAL_SMOKE_SOURCE_URL
    assert data["manual_operator_only"] is True
    assert data["user_review_required"] is True
    assert data["automation_performed"] is False
    assert data["network_actions_performed"] == "none"
    assert data["artifact_files_claimed"] is False
    assert data["manual_observation_scopes"] == [
        MANUAL_ACTION_SCOPE_WEBPAGE,
        MANUAL_ACTION_SCOPE_COMMENTS,
        MANUAL_ACTION_SCOPE_MEDIA,
        MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
    ]
    assert data["article"]["status"] == MSN_EXTRACTION_STATUS_NEEDS_MANUAL_SOURCE_CONTENT
    assert data["comments"]["status"] == MSN_EXTRACTION_STATUS_NEEDS_MANUAL_SOURCE_CONTENT
    assert data["media"]["static_media_observed"] is True
    assert data["export_review"]["export_queue_status"] == "user_review_required"
    assert "completed_manually" not in repr(data)
    assert "live-site verified" not in repr(data).lower()


def test_metadata_only_observation_does_not_fabricate_article_or_comments() -> None:
    data = build_msn_manual_observation_extraction_review_bundle(
        manual_observation_imports=_imports(),
    ).to_dict()

    assert data["article"]["content_source"] == MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY
    assert data["article"]["requires_manual_source_content"] is True
    assert data["article"]["text"] == ""
    assert data["article"]["title"] == ""
    assert data["comments"]["content_source"] == MSN_EXTRACTION_PROVENANCE_MANUAL_OBSERVATION_ONLY
    assert data["comments"]["requires_manual_source_content"] is True
    assert data["comments"]["comments_present_observed"] is True
    assert data["comments"]["thread_records"] == []
    assert data["comments"]["comment_count"] == 0
    assert data["export_review"]["artifact_file_claimed"] is False
    assert data["export_review"]["file_existence_claimed"] is False
    assert data["export_review"]["automatic_classification_performed"] is False


def test_local_supplied_content_populates_fields_without_live_claims() -> None:
    bundle = build_msn_manual_observation_extraction_review_bundle(
        manual_observation_imports=_imports(),
        supplied_article_text="Supplied article headline. Supplied article body.",
        supplied_comment_records=(
            {
                "comment_id": "c1",
                "text": "Supplied local comment.",
                "author": "Reader A",
                "thread_id": "t1",
                "source_order": 1,
            },
            {
                "comment_id": "c2",
                "text": "Supplied local reply.",
                "author": "Reader B",
                "parent_id": "c1",
                "depth": 1,
                "thread_id": "t1",
                "source_order": 2,
            },
        ),
    )
    data = bundle.to_dict()
    rendered = json.dumps(data, sort_keys=True)

    assert data["article"]["content_source"] == MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
    assert data["article"]["requires_manual_source_content"] is False
    assert "Supplied article body" in data["article"]["text"]
    assert data["comments"]["content_source"] == MSN_EXTRACTION_PROVENANCE_LOCAL_SUPPLIED_OPERATOR_CONTENT
    assert data["comments"]["requires_manual_source_content"] is False
    assert data["comments"]["comment_count"] == 2
    assert data["comments"]["thread_records"][1]["parent_id"] == "c1"
    assert data["comments"]["thread_records"][1]["depth"] == 1
    assert data["comments"]["article_text_included"] is False
    assert "requests.get" not in rendered
    assert "playwright" not in rendered


def test_wrong_url_and_site_are_rejected() -> None:
    try:
        build_msn_manual_observation_extraction_review_bundle(
            manual_observation_imports=_imports(),
            source_url="https://www.msn.com/",
        )
    except ValueError as exc:
        assert MSN_MANUAL_SMOKE_SOURCE_URL in str(exc)
    else:
        raise AssertionError("wrong MSN URL must be rejected")

    try:
        build_msn_manual_observation_extraction_review_bundle(
            manual_observation_imports=_imports(),
            site_label="Other",
        )
    except ValueError as exc:
        assert "non-MSN" in str(exc)
    else:
        raise AssertionError("wrong site must be rejected")


def test_unapproved_manual_scopes_are_rejected() -> None:
    for scope in (
        MANUAL_ACTION_SCOPE_ARCHIVE,
        MANUAL_ACTION_SCOPE_WARC_WACZ,
        MANUAL_ACTION_SCOPE_RENDERED_CITATION,
        MANUAL_ACTION_SCOPE_LIVECHAT,
        "arbitrary_scope",
    ):
        try:
            build_msn_manual_observation_extraction_review_bundle(
                manual_observation_imports=(
                    {
                        "site_label": MSN_MANUAL_SMOKE_SITE_LABEL,
                        "source_url": MSN_MANUAL_SMOKE_SOURCE_URL,
                        "action_scope_id": scope,
                        "result_status": "observed",
                    },
                )
            )
        except ValueError as exc:
            assert "unapproved scope" in str(exc)
        else:
            raise AssertionError(f"scope should be rejected: {scope}")


def test_automation_and_completion_claims_are_rejected() -> None:
    claim_fields = (
        "claims_browser_automation",
        "claims_network_capture",
        "claims_archive_submission",
        "claims_downloaded_files",
        "claims_screenshot",
        "claims_ocr",
        "claims_credentials_cookies_accounts",
        "claims_completed_live_verification",
        "claims_automatic_evidence_classification",
        "claims_file_exists",
    )
    for claim_field in claim_fields:
        try:
            build_msn_manual_observation_extraction_review_bundle(
                manual_observation_imports=(
                    {
                        "site_label": MSN_MANUAL_SMOKE_SITE_LABEL,
                        "source_url": MSN_MANUAL_SMOKE_SOURCE_URL,
                        "action_scope_id": MANUAL_ACTION_SCOPE_WEBPAGE,
                        "result_status": "observed",
                        claim_field: True,
                    },
                )
            )
        except ValueError as exc:
            assert claim_field in str(exc)
        else:
            raise AssertionError(f"claim should be rejected: {claim_field}")


def test_export_review_queue_metadata_remains_safe_and_metadata_only() -> None:
    bundle = build_msn_manual_observation_extraction_review_bundle(
        manual_observation_imports=_imports(),
    )
    metadata = msn_extraction_review_bundle_to_export_queue_metadata(bundle)
    rendered = json.dumps(metadata, sort_keys=True)

    assert metadata["export_queue_status"] == "user_review_required"
    assert metadata["manual_operator_only"] is True
    assert metadata["user_review_required"] is True
    assert metadata["artifact_file_claimed"] is False
    assert metadata["file_existence_claimed"] is False
    assert metadata["automatic_classification_performed"] is False
    assert metadata["browser_or_download_command"] == ""
    assert metadata["provider_or_archive_action"] == "none"
    assert metadata["network_actions_performed"] == "none"
    for forbidden in ("archivebox", "yt-dlp", "ffmpeg", "playwright", "requests."):
        assert forbidden not in rendered.lower()


def run_self_test() -> None:
    test_approved_manual_observation_integrates_as_review_bundle()
    test_metadata_only_observation_does_not_fabricate_article_or_comments()
    test_local_supplied_content_populates_fields_without_live_claims()
    test_wrong_url_and_site_are_rejected()
    test_unapproved_manual_scopes_are_rejected()
    test_automation_and_completion_claims_are_rejected()
    test_export_review_queue_metadata_remains_safe_and_metadata_only()


if __name__ == "__main__":
    run_self_test()
    print("Capture MSN manual observation integration self-test passed.")
