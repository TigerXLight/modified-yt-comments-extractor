import ast
import json
from dataclasses import fields
from pathlib import Path

from credential_architecture import (
    CREDENTIAL_ARCHITECTURE_SCHEMA_VERSION,
    CREDENTIAL_ARCHITECTURE_SCOPE,
    REDACTION_TEXT,
    CredentialArchitecturePlan,
    CredentialAuditFinding,
    CredentialDescriptor,
    CredentialKind,
    FindingSeverity,
    SecretSinkRule,
    SinkDisposition,
    StorageBackendKind,
    StorageBackendPolicy,
    build_credential_architecture_markdown,
    build_credential_architecture_text,
    build_row2a_credential_architecture,
    credential_architecture_to_dict,
    redact_known_secret_values,
    render_credential_architecture,
    safe_presence_label,
    serialized_secret_field_paths,
    validate_credential_architecture,
)


EXPECTED_CREDENTIAL_KINDS = (
    "API_KEY",
    "CLOUD_ACCOUNT",
    "OAUTH_CREDENTIAL_SET",
    "APP_PASSWORD",
    "PROVIDER_DEFINED",
)
EXPECTED_STORAGE_BACKENDS = (
    "MEMORY_ONLY",
    "ENVIRONMENT_VARIABLE",
    "OS_KEYRING",
    "LEGACY_PLAINTEXT_SETTINGS",
)
EXPECTED_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
EXPECTED_SINK_DISPOSITIONS = (
    "FORBIDDEN",
    "REDACTED_ONLY",
    "EXPLICIT_USER_ACTION_ONLY",
)
EXPECTED_CREDENTIAL_IDS = (
    "youtube_data_api_key",
    "elevenlabs_scribe_api_key",
    "assemblyai_api_key",
    "deepgram_api_key",
    "speechmatics_api_key",
    "azure_speech_account",
    "google_stt_provider_credentials",
    "cohere_api_key",
    "aws_transcribe_account",
)
EXPECTED_FINDING_IDS = tuple(f"R2A-{index:03d}" for index in range(1, 9))
FORBIDDEN_VALUE_FIELD_NAMES = {
    "value",
    "credential_value",
    "secret_value",
    "api_key_value",
    "password_value",
    "token_value",
    "access_token_value",
    "refresh_token_value",
    "authorization_header",
    "cookie_value",
    "browser_profile_path",
}
FORBIDDEN_RUNTIME_IMPORT_ROOTS = {
    "keyring",
    "requests",
    "httpx",
    "aiohttp",
    "urllib",
    "socket",
    "subprocess",
    "selenium",
    "playwright",
}


def test_enums() -> None:
    assert tuple(item.value for item in CredentialKind) == EXPECTED_CREDENTIAL_KINDS
    assert tuple(item.value for item in StorageBackendKind) == EXPECTED_STORAGE_BACKENDS
    assert tuple(item.value for item in FindingSeverity) == EXPECTED_SEVERITIES
    assert tuple(item.value for item in SinkDisposition) == EXPECTED_SINK_DISPOSITIONS


def test_plan_content() -> None:
    plan = build_row2a_credential_architecture()
    assert isinstance(plan, CredentialArchitecturePlan)
    assert plan.schema_version == CREDENTIAL_ARCHITECTURE_SCHEMA_VERSION
    assert plan.scope == CREDENTIAL_ARCHITECTURE_SCOPE
    assert tuple(item.credential_id for item in plan.descriptors) == EXPECTED_CREDENTIAL_IDS
    assert tuple(item.finding_id for item in plan.findings) == EXPECTED_FINDING_IDS
    assert validate_credential_architecture(plan) == ()

    youtube = plan.descriptors[0]
    assert youtube.entry_id == "source:youtube"
    assert youtube.credential_kind is CredentialKind.API_KEY
    assert youtube.environment_variable_names == ("YOUTUBE_API_KEY",)
    assert youtube.keyring_service_name == "yt-comments-extractor"
    assert youtube.keyring_account_name == "youtube_api_key"
    assert youtube.legacy_field_name == "api_key"
    assert "does not change" in youtube.notes

    aws = plan.descriptors[-1]
    assert aws.credential_kind is CredentialKind.CLOUD_ACCOUNT
    assert "AWS_SECRET_ACCESS_KEY" in aws.environment_variable_names
    assert "does not inspect" in aws.notes

    policies = {item.backend: item for item in plan.storage_policies}
    assert list(policies) == list(StorageBackendKind)
    assert policies[StorageBackendKind.OS_KEYRING].allowed_for_new_writes is True
    assert policies[StorageBackendKind.OS_KEYRING].automatic_fallback_allowed is False
    assert policies[StorageBackendKind.ENVIRONMENT_VARIABLE].allowed_for_new_writes is False
    assert policies[StorageBackendKind.LEGACY_PLAINTEXT_SETTINGS].allowed_for_new_writes is False
    assert all(not item.automatic_migration_allowed for item in plan.storage_policies)

    sinks = {item.sink_id: item for item in plan.sink_rules}
    for sink_id in (
        "exports",
        "logs",
        "manifests",
        "screenshots",
        "command_output",
        "source_control",
    ):
        assert sinks[sink_id].disposition is SinkDisposition.FORBIDDEN
    assert sinks["safe_diagnostics"].disposition is SinkDisposition.REDACTED_ONLY
    assert (
        sinks["reveal_or_copy"].disposition
        is SinkDisposition.EXPLICIT_USER_ACTION_ONLY
    )

    findings = {item.finding_id: item for item in plan.findings}
    assert findings["R2A-001"].severity is FindingSeverity.HIGH
    assert "plaintext" in findings["R2A-001"].summary
    assert findings["R2A-002"].severity is FindingSeverity.HIGH
    assert "legacy" in findings["R2A-002"].summary
    assert "row 2B" in findings["R2A-005"].later_milestone
    assert len(plan.invariants) == 10


def test_serialization_and_renderers() -> None:
    plan = build_row2a_credential_architecture()
    data = credential_architecture_to_dict(plan)
    assert list(data) == [
        "schema_version",
        "scope",
        "descriptor_count",
        "descriptors",
        "storage_policy_count",
        "storage_policies",
        "sink_rule_count",
        "sink_rules",
        "finding_count",
        "findings",
        "invariant_count",
        "invariants",
    ]
    assert data["descriptor_count"] == 9
    assert data["storage_policy_count"] == 4
    assert data["finding_count"] == 8
    assert serialized_secret_field_paths(data) == ()
    assert plan.to_dict() == data

    rendered_json = render_credential_architecture(plan, output_format="json")
    parsed = json.loads(rendered_json)
    assert parsed == data
    assert parsed["descriptors"][0]["credential_id"] == "youtube_data_api_key"
    assert "credential_value" not in rendered_json
    assert "secret_value" not in rendered_json

    markdown = build_credential_architecture_markdown(plan)
    assert "# Credential Architecture — Row 2A" in markdown
    assert "R2A-001 — HIGH" in markdown
    assert "LEGACY_PLAINTEXT_SETTINGS" in markdown
    assert "does not contain or access credential values" in markdown
    assert render_credential_architecture(plan, output_format="markdown") == markdown

    text = build_credential_architecture_text(plan)
    assert "credential_values_present: false" in text
    assert "R2A-008: LOW" in text
    assert render_credential_architecture(plan, output_format="text") == text

    try:
        render_credential_architecture(plan, output_format="html")
    except ValueError as exc:
        assert "unsupported output format" in str(exc)
    else:
        raise AssertionError("unsupported renderer should fail")


def test_redaction_and_status_helpers() -> None:
    first = "dummy-api-key-1234567890"
    second = "dummy-session-token-abcdef"
    original = f"request failed for {first}; retry used {second}; {first}"
    redacted = redact_known_secret_values(original, (first, second, ""))
    assert first not in redacted
    assert second not in redacted
    assert redacted.count(REDACTION_TEXT) == 3
    assert redact_known_secret_values("unchanged", ()) == "unchanged"
    assert safe_presence_label(configured=False) == "Missing"
    assert safe_presence_label(configured=True) == "Configured"
    assert (
        safe_presence_label(configured=True, backend_label="OS keyring")
        == "Configured (OS keyring)"
    )


def test_validation_rejects_unsafe_policy() -> None:
    plan = build_row2a_credential_architecture()
    unsafe_policy = StorageBackendPolicy(
        backend=StorageBackendKind.LEGACY_PLAINTEXT_SETTINGS,
        priority=900,
        persistent=True,
        secure_at_rest_expected=False,
        allowed_for_new_writes=True,
        automatic_fallback_allowed=True,
        automatic_migration_allowed=True,
        notes="intentionally unsafe test fixture",
    )
    unsafe = CredentialArchitecturePlan(
        schema_version=plan.schema_version,
        scope=plan.scope,
        descriptors=plan.descriptors,
        storage_policies=plan.storage_policies[:-1] + (unsafe_policy,),
        sink_rules=plan.sink_rules,
        findings=plan.findings,
        invariants=plan.invariants,
    )
    errors = validate_credential_architecture(unsafe)
    assert "legacy plaintext storage allows new writes" in errors
    assert any("automatic fallback" in item for item in errors)
    assert any("automatic migration" in item for item in errors)

    unsafe_serialized = {"nested": {"credential_value": "dummy"}}
    assert serialized_secret_field_paths(unsafe_serialized) == (
        "$.nested.credential_value",
    )


def test_model_fields_and_static_safety() -> None:
    model_types = (
        CredentialDescriptor,
        StorageBackendPolicy,
        SecretSinkRule,
        CredentialAuditFinding,
        CredentialArchitecturePlan,
    )
    model_field_names = {
        field.name.casefold()
        for model_type in model_types
        for field in fields(model_type)
    }
    assert model_field_names.isdisjoint(FORBIDDEN_VALUE_FIELD_NAMES)

    source_path = Path(__file__).with_name("credential_architecture.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots.isdisjoint(FORBIDDEN_RUNTIME_IMPORT_ROOTS)

    forbidden_calls = {
        "open",
        "getenv",
        "putenv",
        "set_password",
        "get_password",
        "delete_password",
    }
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            called_names.add(node.func.attr)
    assert called_names.isdisjoint(forbidden_calls)


def run_self_test() -> None:
    test_enums()
    test_plan_content()
    test_serialization_and_renderers()
    test_redaction_and_status_helpers()
    test_validation_rejects_unsafe_policy()
    test_model_fields_and_static_safety()


if __name__ == "__main__":
    run_self_test()
    print("Credential architecture self-test passed.")
