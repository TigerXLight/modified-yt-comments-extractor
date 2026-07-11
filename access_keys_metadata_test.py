import json
from dataclasses import fields

from access_keys_metadata import (
    ACCESS_KEYS_METADATA_SCOPE,
    AccessEntryKind,
    AccessEntryMetadata,
    AccessKeysCatalog,
    AccessMode,
    ConnectionTestMetadata,
    ConnectionTestStatus,
    CredentialStatus,
    access_entry_metadata_to_dict,
    access_keys_catalog_to_dict,
    build_access_keys_catalog,
    build_access_keys_markdown,
    build_access_keys_text,
    connection_test_metadata_to_dict,
    render_access_keys_catalog,
)


EXPECTED_ACCESS_MODES = (
    "NO_CREDENTIALS_REQUIRED",
    "API_KEY",
    "OAUTH_OR_BROWSER_LOGIN",
    "APP_PASSWORD",
    "USER_AUTHENTICATED_BROWSER_PROFILE",
    "DEDICATED_CAPTURE_BROWSER_PROFILE",
    "MANUAL_IMPORT_ONLY",
    "LOCAL_ONLY",
    "BLOCKED_OR_NOT_CONFIGURED",
)

EXPECTED_CREDENTIAL_STATUSES = (
    "NOT_NEEDED",
    "OPTIONAL",
    "REQUIRED_MISSING",
    "CONFIGURED_UNTESTED",
    "CONFIGURED_TEST_PASSED",
    "CONFIGURED_TEST_FAILED",
    "EXPIRED_OR_REVOKED",
    "DISABLED_BY_USER",
    "UNSUPPORTED",
)

EXPECTED_TEST_STATUSES = (
    "TEST_NOT_SUPPORTED",
    "TEST_NOT_RUN",
    "TEST_RUNNING",
    "TEST_PASSED",
    "TEST_FAILED",
    "TEST_SKIPPED_BY_USER",
)

EXPECTED_ENTRY_KINDS = (
    "ASR_PROVIDER",
    "SOURCE_ADAPTER",
    "ARCHIVE_SERVICE",
    "BROWSER_ASSISTED_CAPTURE",
)

FORBIDDEN_SECRET_FIELD_NAMES = {
    "api_key",
    "password",
    "secret",
    "cookie",
    "cookies",
    "token",
    "access_token",
    "refresh_token",
    "authorization_header",
    "browser_profile_path",
}


def run_self_test() -> None:
    assert tuple(item.value for item in AccessMode) == EXPECTED_ACCESS_MODES
    assert tuple(item.value for item in CredentialStatus) == EXPECTED_CREDENTIAL_STATUSES
    assert tuple(item.value for item in ConnectionTestStatus) == EXPECTED_TEST_STATUSES
    assert tuple(item.value for item in AccessEntryKind) == EXPECTED_ENTRY_KINDS

    local_asr = AccessEntryMetadata(
        entry_id="local_whisper_cpp",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        display_name="whisper.cpp local",
        platform_family="asr_provider",
        access_mode=AccessMode.LOCAL_ONLY,
        credential_status=CredentialStatus.NOT_NEEDED,
        implementation_state="existing_local_runtime",
        credential_type="none",
        supports_captions_or_transcripts=True,
        supports_keyterms=True,
        supports_phrase_prompts=True,
        project_status="candidate",
        setup_hint="Use the existing local/offline workflow.",
        privacy_notes="Audio remains local when the local engine is used.",
        access_limitations="Project accuracy remains below the strict acceptance gate.",
    )
    assert local_asr.credentials_required is False
    assert local_asr.credentials_optional is False
    assert local_asr.supports_connection_test is False
    assert local_asr.last_tested_at_utc == ""
    assert local_asr.last_test_status is ConnectionTestStatus.TEST_NOT_SUPPORTED

    cloud_asr = AccessEntryMetadata(
        entry_id="elevenlabs_scribe_v2",
        entry_kind=AccessEntryKind.ASR_PROVIDER,
        display_name="ElevenLabs Scribe v2",
        platform_family="asr_provider",
        access_mode=AccessMode.API_KEY,
        credential_status=CredentialStatus.REQUIRED_MISSING,
        implementation_state="optional_future_integration",
        credential_type="api_key",
        credentials_required=True,
        supports_connection_test=True,
        supports_captions_or_transcripts=True,
        supports_keyterms=True,
        project_status="candidate",
        setup_hint="Configure only in a later explicit credential-storage milestone.",
        privacy_notes="Cloud use may send selected audio to the provider.",
        cost_or_rate_limit_notes="Cloud usage may incur cost and rate limits.",
        access_limitations="Missing access does not mean the provider lacks the capability.",
        last_test_status=ConnectionTestStatus.TEST_NOT_RUN,
    )
    assert cloud_asr.credential_status is CredentialStatus.REQUIRED_MISSING
    assert cloud_asr.last_test_status is ConnectionTestStatus.TEST_NOT_RUN
    assert cloud_asr.project_status == "candidate"

    source_adapter = AccessEntryMetadata(
        entry_id="youtube",
        entry_kind=AccessEntryKind.SOURCE_ADAPTER,
        display_name="YouTube",
        platform_family="video_social",
        access_mode=AccessMode.API_KEY,
        credential_status=CredentialStatus.CONFIGURED_UNTESTED,
        implementation_state="existing_runtime_plus_metadata_skeleton",
        credential_type="api_key",
        credentials_required=True,
        supports_comments=True,
        supports_replies=True,
        supports_live_chat=True,
        supports_captions_or_transcripts=True,
        supports_media_evidence=True,
        supports_connection_test=False,
        setup_hint="Keep the current sidebar field working until a later migration.",
        privacy_notes="Requests may expose selected source access patterns.",
        cost_or_rate_limit_notes="YouTube Data API quota applies.",
        access_limitations="This model does not migrate or test the configured value.",
    )
    assert source_adapter.supports_comments
    assert source_adapter.supports_replies
    assert source_adapter.supports_live_chat
    assert source_adapter.credential_status is not CredentialStatus.UNSUPPORTED

    archive_check = AccessEntryMetadata(
        entry_id="wayback_check",
        entry_kind=AccessEntryKind.ARCHIVE_SERVICE,
        display_name="Wayback Machine check",
        platform_family="archive_service",
        access_mode=AccessMode.NO_CREDENTIALS_REQUIRED,
        credential_status=CredentialStatus.NOT_NEEDED,
        implementation_state="roadmap_only",
        credential_type="none",
        supports_archive_check=True,
        supports_archive_submit=False,
        supports_connection_test=False,
        access_limitations="Read-only lookup is not implemented by this model.",
    )
    archive_submit = AccessEntryMetadata(
        entry_id="wayback_submit",
        entry_kind=AccessEntryKind.ARCHIVE_SERVICE,
        display_name="Wayback save/submit",
        platform_family="archive_service",
        access_mode=AccessMode.NO_CREDENTIALS_REQUIRED,
        credential_status=CredentialStatus.DISABLED_BY_USER,
        implementation_state="roadmap_only",
        credential_type="none",
        supports_archive_check=False,
        supports_archive_submit=True,
        supports_connection_test=False,
        access_limitations="Submission must remain explicit and user-selected.",
    )
    assert archive_check.supports_archive_check
    assert not archive_check.supports_archive_submit
    assert archive_submit.supports_archive_submit
    assert not archive_submit.supports_archive_check
    assert archive_submit.credential_status is CredentialStatus.DISABLED_BY_USER

    failed_test = ConnectionTestMetadata(
        entry_id="elevenlabs_scribe_v2",
        status=ConnectionTestStatus.TEST_FAILED,
        user_triggered=True,
        tested_at_utc="2026-07-11T21:45:00Z",
        test_type="explicit_connection_test",
        safe_diagnostic="Provider rejected the test request.",
        cost_or_rate_limit_warning="A future live test may consume quota.",
    )
    assert failed_test.user_triggered is True
    assert failed_test.status is ConnectionTestStatus.TEST_FAILED

    entry_dict = access_entry_metadata_to_dict(cloud_asr)
    assert entry_dict["entry_kind"] == "ASR_PROVIDER"
    assert entry_dict["access_mode"] == "API_KEY"
    assert entry_dict["credential_status"] == "REQUIRED_MISSING"
    assert entry_dict["last_test_status"] == "TEST_NOT_RUN"
    assert entry_dict["supports_keyterms"] is True
    assert entry_dict["supports_archive_submit"] is False

    test_dict = connection_test_metadata_to_dict(failed_test)
    assert test_dict == {
        "entry_id": "elevenlabs_scribe_v2",
        "status": "TEST_FAILED",
        "user_triggered": True,
        "tested_at_utc": "2026-07-11T21:45:00Z",
        "test_type": "explicit_connection_test",
        "safe_diagnostic": "Provider rejected the test request.",
        "cost_or_rate_limit_warning": "A future live test may consume quota.",
    }

    catalog = build_access_keys_catalog(
        (local_asr, cloud_asr, source_adapter, archive_check, archive_submit),
        (failed_test,),
    )
    assert isinstance(catalog, AccessKeysCatalog)
    assert isinstance(catalog.entries, tuple)
    assert isinstance(catalog.test_results, tuple)
    assert catalog.scope == ACCESS_KEYS_METADATA_SCOPE

    catalog_dict = access_keys_catalog_to_dict(catalog)
    assert list(catalog_dict) == [
        "scope",
        "entry_count",
        "entries",
        "test_result_count",
        "test_results",
    ]
    assert catalog_dict["entry_count"] == 5
    assert catalog_dict["test_result_count"] == 1
    assert catalog_dict["entries"][2]["entry_kind"] == "SOURCE_ADAPTER"
    assert catalog_dict["entries"][3]["supports_archive_check"] is True
    assert catalog_dict["entries"][4]["supports_archive_submit"] is True
    assert catalog.to_dict() == catalog_dict

    markdown = build_access_keys_markdown(catalog)
    assert "# Access & Keys Metadata" in markdown
    assert "## ElevenLabs Scribe v2" in markdown
    assert "Credential status: REQUIRED_MISSING" in markdown
    assert "## YouTube" in markdown
    assert "## Wayback Machine check" in markdown
    assert "archive_check" in markdown
    assert "## Recorded Connection-Test Metadata" in markdown
    assert "Explicitly user-triggered: yes" in markdown
    assert "does not store or test credentials" in markdown

    text = build_access_keys_text(catalog)
    assert "Access & Keys metadata" in text
    assert "elevenlabs_scribe_v2 (ElevenLabs Scribe v2)" in text
    assert "credential_status: REQUIRED_MISSING" in text
    assert "wayback_submit (Wayback save/submit)" in text
    assert "user_triggered: True" in text
    assert "no credential storage/testing" in text

    rendered_json = render_access_keys_catalog(catalog, output_format="json")
    parsed = json.loads(rendered_json)
    assert parsed["entry_count"] == 5
    assert parsed["entries"][0]["access_mode"] == "LOCAL_ONLY"
    assert parsed["test_results"][0]["status"] == "TEST_FAILED"
    assert render_access_keys_catalog(catalog, output_format="markdown") == markdown
    assert render_access_keys_catalog(catalog, output_format="text") == text

    empty_catalog = build_access_keys_catalog()
    assert empty_catalog.entries == ()
    assert empty_catalog.test_results == ()
    assert "No access entries" in build_access_keys_markdown(empty_catalog)

    try:
        render_access_keys_catalog(catalog, output_format="html")
    except ValueError as exc:
        assert "unsupported output format" in str(exc)
    else:
        raise AssertionError("unsupported format should fail")

    model_field_names = {
        field.name
        for model in (
            AccessEntryMetadata,
            ConnectionTestMetadata,
            AccessKeysCatalog,
        )
        for field in fields(model)
    }
    assert model_field_names.isdisjoint(FORBIDDEN_SECRET_FIELD_NAMES)

    serialized_keys = set(entry_dict) | set(test_dict) | set(catalog_dict)
    assert serialized_keys.isdisjoint(FORBIDDEN_SECRET_FIELD_NAMES)
    assert "credential storage" in ACCESS_KEYS_METADATA_SCOPE
    assert "key testing" in ACCESS_KEYS_METADATA_SCOPE
    assert "provider/API calls" in ACCESS_KEYS_METADATA_SCOPE


if __name__ == "__main__":
    run_self_test()
    print("Access & Keys metadata self-test passed.")
