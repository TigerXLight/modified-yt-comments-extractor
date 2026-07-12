from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


CREDENTIAL_ARCHITECTURE_SCOPE = (
    "row 2A local non-secret credential architecture and audit only; no credential "
    "values, storage reads or writes, migration, clearing, reveal/copy UI, connection "
    "tests, provider/API calls, OAuth, browser access, network access, or runtime wiring"
)
CREDENTIAL_ARCHITECTURE_SCHEMA_VERSION = "1.0"
REPORT_FORMATS = ("markdown", "text", "json")
REDACTION_TEXT = "[REDACTED]"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class CredentialKind(_StringEnum):
    API_KEY = "API_KEY"
    CLOUD_ACCOUNT = "CLOUD_ACCOUNT"
    OAUTH_CREDENTIAL_SET = "OAUTH_CREDENTIAL_SET"
    APP_PASSWORD = "APP_PASSWORD"
    PROVIDER_DEFINED = "PROVIDER_DEFINED"


class StorageBackendKind(_StringEnum):
    MEMORY_ONLY = "MEMORY_ONLY"
    ENVIRONMENT_VARIABLE = "ENVIRONMENT_VARIABLE"
    OS_KEYRING = "OS_KEYRING"
    LEGACY_PLAINTEXT_SETTINGS = "LEGACY_PLAINTEXT_SETTINGS"


class FindingSeverity(_StringEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SinkDisposition(_StringEnum):
    FORBIDDEN = "FORBIDDEN"
    REDACTED_ONLY = "REDACTED_ONLY"
    EXPLICIT_USER_ACTION_ONLY = "EXPLICIT_USER_ACTION_ONLY"


@dataclass(frozen=True)
class CredentialDescriptor:
    credential_id: str
    entry_id: str
    display_name: str
    credential_kind: CredentialKind
    required: bool
    environment_variable_names: tuple[str, ...] = ()
    keyring_service_name: str = ""
    keyring_account_name: str = ""
    legacy_field_name: str = ""
    implementation_state: str = "architecture only"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class StorageBackendPolicy:
    backend: StorageBackendKind
    priority: int
    persistent: bool
    secure_at_rest_expected: bool
    allowed_for_new_writes: bool
    automatic_fallback_allowed: bool
    automatic_migration_allowed: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class SecretSinkRule:
    sink_id: str
    display_name: str
    disposition: SinkDisposition
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class CredentialAuditFinding:
    finding_id: str
    severity: FindingSeverity
    component: str
    summary: str
    evidence: str
    recommendation: str
    later_milestone: str

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class CredentialArchitecturePlan:
    schema_version: str
    scope: str
    descriptors: tuple[CredentialDescriptor, ...]
    storage_policies: tuple[StorageBackendPolicy, ...]
    sink_rules: tuple[SecretSinkRule, ...]
    findings: tuple[CredentialAuditFinding, ...]
    invariants: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return credential_architecture_to_dict(self)


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _value_for_dict(item) for key, item in value.items()}
    return value


def _dataclass_to_dict(instance: Any) -> dict[str, Any]:
    return {
        key: _value_for_dict(value)
        for key, value in asdict(instance).items()
    }


def _descriptor(
    credential_id: str,
    entry_id: str,
    display_name: str,
    credential_kind: CredentialKind,
    *,
    environment_variable_names: Sequence[str] = (),
    keyring_service_name: str = "",
    keyring_account_name: str = "",
    legacy_field_name: str = "",
    notes: str = "",
) -> CredentialDescriptor:
    return CredentialDescriptor(
        credential_id=credential_id,
        entry_id=entry_id,
        display_name=display_name,
        credential_kind=credential_kind,
        required=True,
        environment_variable_names=tuple(environment_variable_names),
        keyring_service_name=keyring_service_name,
        keyring_account_name=keyring_account_name,
        legacy_field_name=legacy_field_name,
        notes=notes,
    )


def _build_descriptors() -> tuple[CredentialDescriptor, ...]:
    return (
        _descriptor(
            "youtube_data_api_key",
            "source:youtube",
            "YouTube Data API key",
            CredentialKind.API_KEY,
            environment_variable_names=("YOUTUBE_API_KEY",),
            keyring_service_name="yt-comments-extractor",
            keyring_account_name="youtube_api_key",
            legacy_field_name="api_key",
            notes=(
                "Existing runtime credential. Row 2A describes identifiers and "
                "boundaries only and does not change current loading or saving."
            ),
        ),
        _descriptor(
            "elevenlabs_scribe_api_key",
            "asr:elevenlabs_scribe",
            "ElevenLabs Scribe API key",
            CredentialKind.API_KEY,
            environment_variable_names=("ELEVENLABS_API_KEY",),
            notes="Leading optional cloud ASR candidate; no provider integration is added.",
        ),
        _descriptor(
            "assemblyai_api_key",
            "asr:assemblyai_universal_3_5_pro",
            "AssemblyAI API key",
            CredentialKind.API_KEY,
            environment_variable_names=("ASSEMBLYAI_API_KEY",),
            notes="Rejected benchmark provider remains catalogued without runtime access.",
        ),
        _descriptor(
            "deepgram_api_key",
            "asr:deepgram_nova_3",
            "Deepgram API key",
            CredentialKind.API_KEY,
            environment_variable_names=("DEEPGRAM_API_KEY",),
            notes="Rejected benchmark provider remains catalogued without runtime access.",
        ),
        _descriptor(
            "speechmatics_api_key",
            "asr:speechmatics_enhanced",
            "Speechmatics API key",
            CredentialKind.API_KEY,
            environment_variable_names=("SPEECHMATICS_API_KEY",),
            notes="Rejected benchmark provider remains catalogued without runtime access.",
        ),
        _descriptor(
            "azure_speech_account",
            "asr:azure_speech",
            "Azure Speech account credentials",
            CredentialKind.CLOUD_ACCOUNT,
            environment_variable_names=(
                "AZURE_SPEECH_KEY",
                "AZURE_SPEECH_REGION",
            ),
            notes=(
                "Compound/provider-specific credential shape requires a later explicit "
                "design; no values or region are read in row 2A."
            ),
        ),
        _descriptor(
            "google_stt_provider_credentials",
            "asr:google_stt_video_enhanced",
            "Google STT provider credentials",
            CredentialKind.PROVIDER_DEFINED,
            environment_variable_names=("GOOGLE_APPLICATION_CREDENTIALS",),
            notes=(
                "Provider-specific authentication may not be a single API key. A later "
                "milestone must choose the supported method before any integration."
            ),
        ),
        _descriptor(
            "cohere_api_key",
            "asr:cohere_transcribe",
            "Cohere API key",
            CredentialKind.API_KEY,
            environment_variable_names=("CO_API_KEY", "COHERE_API_KEY"),
            notes="Rejected benchmark provider remains catalogued without runtime access.",
        ),
        _descriptor(
            "aws_transcribe_account",
            "asr:aws_transcribe_custom_vocabulary",
            "AWS Transcribe account credentials",
            CredentialKind.CLOUD_ACCOUNT,
            environment_variable_names=(
                "AWS_PROFILE",
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AWS_REGION",
            ),
            notes=(
                "Blocked provider. Row 2A records identifier names only and does not "
                "inspect AWS configuration or enable service access."
            ),
        ),
    )


def _build_storage_policies() -> tuple[StorageBackendPolicy, ...]:
    return (
        StorageBackendPolicy(
            backend=StorageBackendKind.MEMORY_ONLY,
            priority=10,
            persistent=False,
            secure_at_rest_expected=False,
            allowed_for_new_writes=True,
            automatic_fallback_allowed=False,
            automatic_migration_allowed=False,
            notes=(
                "Session-only material may be supplied explicitly for a single run. "
                "It must not be copied into another backend automatically."
            ),
        ),
        StorageBackendPolicy(
            backend=StorageBackendKind.ENVIRONMENT_VARIABLE,
            priority=20,
            persistent=False,
            secure_at_rest_expected=False,
            allowed_for_new_writes=False,
            automatic_fallback_allowed=False,
            automatic_migration_allowed=False,
            notes=(
                "Environment variables are a read-only future source. The application "
                "must not write process or user environment variables."
            ),
        ),
        StorageBackendPolicy(
            backend=StorageBackendKind.OS_KEYRING,
            priority=30,
            persistent=True,
            secure_at_rest_expected=True,
            allowed_for_new_writes=True,
            automatic_fallback_allowed=False,
            automatic_migration_allowed=False,
            notes=(
                "Preferred persistent backend when explicitly selected and available. "
                "A keyring failure must not silently downgrade to plaintext."
            ),
        ),
        StorageBackendPolicy(
            backend=StorageBackendKind.LEGACY_PLAINTEXT_SETTINGS,
            priority=900,
            persistent=True,
            secure_at_rest_expected=False,
            allowed_for_new_writes=False,
            automatic_fallback_allowed=False,
            automatic_migration_allowed=False,
            notes=(
                "Compatibility/audit source only. Reading, migrating, or clearing a "
                "legacy value requires a later explicit milestone and user-visible result."
            ),
        ),
    )


def _build_sink_rules() -> tuple[SecretSinkRule, ...]:
    forbidden = (
        ("exports", "Exports and evidence packages"),
        ("logs", "Application, activity, debug, and crash logs"),
        ("manifests", "Manifests and sidecars"),
        ("screenshots", "Screenshots and captured visible text"),
        ("clipboard_automatic", "Automatic clipboard operations"),
        ("command_output", "Command output and diagnostic reports"),
        ("source_control", "Source control and committed files"),
        ("telemetry", "Telemetry and analytics"),
    )
    rules = [
        SecretSinkRule(
            sink_id=sink_id,
            display_name=display_name,
            disposition=SinkDisposition.FORBIDDEN,
            notes="Secret material must never be written to this sink.",
        )
        for sink_id, display_name in forbidden
    ]
    rules.extend(
        (
            SecretSinkRule(
                sink_id="safe_diagnostics",
                display_name="User-visible safe diagnostics",
                disposition=SinkDisposition.REDACTED_ONLY,
                notes=(
                    "Diagnostics may report backend, presence, and error category only; "
                    "known secret material must be replaced with a fixed marker."
                ),
            ),
            SecretSinkRule(
                sink_id="reveal_or_copy",
                display_name="Reveal or copy controls",
                disposition=SinkDisposition.EXPLICIT_USER_ACTION_ONLY,
                notes=(
                    "Not implemented in row 2A. Any later reveal/copy action must be "
                    "separate, explicit, temporary, and scoped to one credential."
                ),
            ),
        )
    )
    return tuple(rules)


def _build_findings() -> tuple[CredentialAuditFinding, ...]:
    return (
        CredentialAuditFinding(
            finding_id="R2A-001",
            severity=FindingSeverity.HIGH,
            component="core/settings.py SettingsManager.save/_save_api_key",
            summary="Keyring failure or absence can silently downgrade a key to plaintext settings.json.",
            evidence=(
                "The current manager changes _use_keyring to False after an exception and "
                "then includes api_key in the general settings JSON."
            ),
            recommendation=(
                "In a later approved milestone, fail closed for persistent writes and "
                "require explicit user choice before any insecure legacy storage."
            ),
            later_milestone="row 2B or later; no runtime change in row 2A",
        ),
        CredentialAuditFinding(
            finding_id="R2A-002",
            severity=FindingSeverity.HIGH,
            component="core/settings.py SettingsManager.delete_api_key",
            summary="The delete path does not remove a legacy plaintext api_key field.",
            evidence=(
                "delete_api_key deletes only the keyring entry when keyring is active and "
                "otherwise returns success without editing settings.json."
            ),
            recommendation=(
                "Design an explicit clear operation that addresses every known backend, "
                "reports partial failure, and never claims success while a legacy copy remains."
            ),
            later_milestone="row 2C clear/migration workflow",
        ),
        CredentialAuditFinding(
            finding_id="R2A-003",
            severity=FindingSeverity.MEDIUM,
            component="core/settings.py AppSettings",
            summary="Secret material is coupled to ordinary application settings.",
            evidence=(
                "AppSettings contains api_key beside spam filters, sort settings, and window "
                "preferences, and serialization behavior depends on a boolean flag."
            ),
            recommendation=(
                "Use a provider-neutral credential boundary so ordinary settings objects and "
                "serializers never carry credential material."
            ),
            later_milestone="row 2B credential-provider abstraction",
        ),
        CredentialAuditFinding(
            finding_id="R2A-004",
            severity=FindingSeverity.MEDIUM,
            component="main.py API-key sidebar",
            summary="The current YouTube key is loaded into a long-lived GUI entry with a reveal toggle.",
            evidence=(
                "_load_settings inserts the full key into api_key_entry and the eye button can "
                "show the complete value."
            ),
            recommendation=(
                "Preserve current behavior until a separately approved migration; later use a "
                "masked/presence-oriented control and an explicit temporary reveal action."
            ),
            later_milestone="row 2C UI and migration",
        ),
        CredentialAuditFinding(
            finding_id="R2A-005",
            severity=FindingSeverity.MEDIUM,
            component="credential identifiers and storage mapping",
            summary="The current storage contract supports one globally named YouTube key only.",
            evidence=(
                "KEYRING_SERVICE_NAME and KEYRING_API_KEY_NAME are fixed constants and no "
                "provider-neutral descriptor registry exists in runtime settings."
            ),
            recommendation=(
                "Adopt stable credential IDs and backend locator metadata before adding any "
                "cloud ASR credential values."
            ),
            later_milestone="row 2B credential-provider abstraction",
        ),
        CredentialAuditFinding(
            finding_id="R2A-006",
            severity=FindingSeverity.MEDIUM,
            component="migration and provenance",
            summary="There is no explicit migration state, provenance, or downgrade record.",
            evidence=(
                "The current manager reads keyring first and then settings.json but does not "
                "report which source supplied the key or whether a fallback occurred."
            ),
            recommendation=(
                "Return non-secret provenance/status records and require explicit confirmation "
                "before moving or deleting any legacy credential."
            ),
            later_milestone="row 2B status model and row 2C migration",
        ),
        CredentialAuditFinding(
            finding_id="R2A-007",
            severity=FindingSeverity.LOW,
            component="main.py storage status label",
            summary="The storage label is a startup snapshot and may become stale after a backend failure.",
            evidence=(
                "The label is created from get_storage_info during sidebar construction and is "
                "not refreshed when _use_keyring changes later."
            ),
            recommendation=(
                "Later bind the UI to a non-secret backend-status snapshot instead of inferring "
                "state from a one-time string."
            ),
            later_milestone="row 2C UI status wiring",
        ),
        CredentialAuditFinding(
            finding_id="R2A-008",
            severity=FindingSeverity.LOW,
            component="diagnostic redaction",
            summary="No central credential-aware diagnostic redaction boundary exists.",
            evidence=(
                "Current credential errors are logged as exception text and future provider "
                "SDKs may include request details unless diagnostics are normalized."
            ),
            recommendation=(
                "Route future credential/provider errors through fixed safe categories and exact "
                "known-value redaction before display or logging."
            ),
            later_milestone="row 2B safe status/diagnostic layer",
        ),
    )


def _build_invariants() -> tuple[str, ...]:
    return (
        "Credential values never appear in dataclasses, serialized architecture reports, exports, logs, manifests, sidecars, screenshots, evidence packages, command output, or source control.",
        "Keyring failure must not silently fall back to plaintext persistence.",
        "Environment-variable credentials are read-only inputs and are never copied into persistent storage automatically.",
        "No credential is migrated, overwritten, or deleted without an explicit user action and a user-visible outcome.",
        "Credential presence is reported separately from provider support and connection-test status.",
        "Connection tests and provider runs remain explicit user-triggered actions and are outside row 2A.",
        "A clear operation must target every known backend and report partial failure without exposing values.",
        "Legacy plaintext settings are compatibility/audit input only and are not an allowed destination for new writes.",
        "The existing YouTube workflow remains unchanged until a separately approved migration milestone.",
        "Cloud ASR credentials do not enable cloud ASR by themselves; provider integration, cost, privacy, and network approval remain separate boundaries.",
    )


def build_row2a_credential_architecture() -> CredentialArchitecturePlan:
    return CredentialArchitecturePlan(
        schema_version=CREDENTIAL_ARCHITECTURE_SCHEMA_VERSION,
        scope=CREDENTIAL_ARCHITECTURE_SCOPE,
        descriptors=_build_descriptors(),
        storage_policies=_build_storage_policies(),
        sink_rules=_build_sink_rules(),
        findings=_build_findings(),
        invariants=_build_invariants(),
    )


def credential_architecture_to_dict(
    plan: CredentialArchitecturePlan,
) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "scope": plan.scope,
        "descriptor_count": len(plan.descriptors),
        "descriptors": [item.to_dict() for item in plan.descriptors],
        "storage_policy_count": len(plan.storage_policies),
        "storage_policies": [item.to_dict() for item in plan.storage_policies],
        "sink_rule_count": len(plan.sink_rules),
        "sink_rules": [item.to_dict() for item in plan.sink_rules],
        "finding_count": len(plan.findings),
        "findings": [item.to_dict() for item in plan.findings],
        "invariant_count": len(plan.invariants),
        "invariants": list(plan.invariants),
    }


def redact_known_secret_values(
    text: str,
    known_values: Iterable[str],
    *,
    replacement: str = REDACTION_TEXT,
) -> str:
    """Replace exact known credential material without retaining or fingerprinting it."""
    result = str(text)
    candidates = sorted(
        {str(item) for item in known_values if str(item)},
        key=len,
        reverse=True,
    )
    for candidate in candidates:
        result = result.replace(candidate, replacement)
    return result


def safe_presence_label(*, configured: bool, backend_label: str = "") -> str:
    """Return a non-secret status label; never accepts or returns credential material."""
    if not configured:
        return "Missing"
    if backend_label.strip():
        return f"Configured ({backend_label.strip()})"
    return "Configured"


_FORBIDDEN_SERIALIZED_FIELD_NAMES = frozenset(
    {
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
)


def serialized_secret_field_paths(value: Any, path: str = "$") -> tuple[str, ...]:
    """Return forbidden secret-bearing field paths in a serialized structure."""
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if key_text.casefold() in _FORBIDDEN_SERIALIZED_FIELD_NAMES:
                findings.append(child_path)
            findings.extend(serialized_secret_field_paths(item, child_path))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(serialized_secret_field_paths(item, f"{path}[{index}]"))
    return tuple(findings)


def validate_credential_architecture(
    plan: CredentialArchitecturePlan,
) -> tuple[str, ...]:
    errors: list[str] = []

    if plan.schema_version != CREDENTIAL_ARCHITECTURE_SCHEMA_VERSION:
        errors.append("unexpected schema version")
    if plan.scope != CREDENTIAL_ARCHITECTURE_SCOPE:
        errors.append("unexpected architecture scope")

    credential_ids = [item.credential_id for item in plan.descriptors]
    if len(credential_ids) != len(set(credential_ids)):
        errors.append("duplicate credential_id")
    entry_pairs = [(item.entry_id, item.credential_id) for item in plan.descriptors]
    if len(entry_pairs) != len(set(entry_pairs)):
        errors.append("duplicate entry/credential mapping")

    backend_ids = [item.backend.value for item in plan.storage_policies]
    if len(backend_ids) != len(set(backend_ids)):
        errors.append("duplicate storage backend policy")
    priorities = [item.priority for item in plan.storage_policies]
    if priorities != sorted(priorities):
        errors.append("storage policies are not deterministically ordered")

    plaintext = next(
        (
            item
            for item in plan.storage_policies
            if item.backend is StorageBackendKind.LEGACY_PLAINTEXT_SETTINGS
        ),
        None,
    )
    if plaintext is None:
        errors.append("legacy plaintext policy is missing")
    elif plaintext.allowed_for_new_writes:
        errors.append("legacy plaintext storage allows new writes")

    for policy in plan.storage_policies:
        if policy.automatic_fallback_allowed:
            errors.append(f"automatic fallback enabled for {policy.backend.value}")
        if policy.automatic_migration_allowed:
            errors.append(f"automatic migration enabled for {policy.backend.value}")

    sink_ids = [item.sink_id for item in plan.sink_rules]
    if len(sink_ids) != len(set(sink_ids)):
        errors.append("duplicate sink rule")
    forbidden_sinks = {
        item.sink_id
        for item in plan.sink_rules
        if item.disposition is SinkDisposition.FORBIDDEN
    }
    required_forbidden = {
        "exports",
        "logs",
        "manifests",
        "screenshots",
        "command_output",
        "source_control",
    }
    missing_forbidden = sorted(required_forbidden - forbidden_sinks)
    if missing_forbidden:
        errors.append("missing forbidden sinks: " + ", ".join(missing_forbidden))

    finding_ids = [item.finding_id for item in plan.findings]
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("duplicate audit finding")
    if not any(item.severity is FindingSeverity.HIGH for item in plan.findings):
        errors.append("audit has no high-severity finding")

    serialized = credential_architecture_to_dict(plan)
    secret_paths = serialized_secret_field_paths(serialized)
    if secret_paths:
        errors.append("secret-bearing serialized fields: " + ", ".join(secret_paths))

    return tuple(errors)


def build_credential_architecture_markdown(
    plan: CredentialArchitecturePlan,
) -> str:
    lines = [
        "# Credential Architecture — Row 2A",
        "",
        f"- Schema version: {plan.schema_version}",
        f"- Scope: {plan.scope}",
        f"- Credential descriptors: {len(plan.descriptors)}",
        f"- Audit findings: {len(plan.findings)}",
        "",
        "This report contains identifiers, policies, and audit findings only. It does not contain or access credential values.",
        "",
        "## Credential Descriptors",
        "",
    ]
    for item in plan.descriptors:
        lines.extend(
            [
                f"### {item.display_name}",
                "",
                f"- Credential ID: {item.credential_id}",
                f"- Entry ID: {item.entry_id}",
                f"- Kind: {item.credential_kind.value}",
                f"- Required: {'yes' if item.required else 'no'}",
                "- Environment variable names: "
                + (", ".join(item.environment_variable_names) or "none"),
                f"- Keyring service name: {item.keyring_service_name or 'not assigned'}",
                f"- Keyring account name: {item.keyring_account_name or 'not assigned'}",
                f"- Legacy field name: {item.legacy_field_name or 'none'}",
                f"- Implementation state: {item.implementation_state}",
            ]
        )
        if item.notes:
            lines.append(f"- Notes: {item.notes}")
        lines.append("")

    lines.extend(["## Storage Backend Policies", ""])
    for item in plan.storage_policies:
        lines.extend(
            [
                f"### {item.backend.value}",
                "",
                f"- Priority: {item.priority}",
                f"- Persistent: {'yes' if item.persistent else 'no'}",
                f"- Secure at rest expected: {'yes' if item.secure_at_rest_expected else 'no'}",
                f"- Allowed for new writes: {'yes' if item.allowed_for_new_writes else 'no'}",
                f"- Automatic fallback allowed: {'yes' if item.automatic_fallback_allowed else 'no'}",
                f"- Automatic migration allowed: {'yes' if item.automatic_migration_allowed else 'no'}",
                f"- Notes: {item.notes}",
                "",
            ]
        )

    lines.extend(["## Secret Sink Rules", ""])
    for item in plan.sink_rules:
        lines.append(
            f"- **{item.display_name}** (`{item.sink_id}`): "
            f"{item.disposition.value}. {item.notes}"
        )

    lines.extend(["", "## Existing-Code Audit Findings", ""])
    for item in plan.findings:
        lines.extend(
            [
                f"### {item.finding_id} — {item.severity.value}",
                "",
                f"- Component: {item.component}",
                f"- Summary: {item.summary}",
                f"- Evidence: {item.evidence}",
                f"- Recommendation: {item.recommendation}",
                f"- Boundary: {item.later_milestone}",
                "",
            ]
        )

    lines.extend(["## Security Invariants", ""])
    lines.extend(f"- {item}" for item in plan.invariants)
    return "\n".join(lines).rstrip()


def build_credential_architecture_text(plan: CredentialArchitecturePlan) -> str:
    lines = [
        "Credential architecture - Row 2A",
        f"schema_version: {plan.schema_version}",
        f"scope: {plan.scope}",
        f"descriptor_count: {len(plan.descriptors)}",
        f"storage_policy_count: {len(plan.storage_policies)}",
        f"sink_rule_count: {len(plan.sink_rules)}",
        f"finding_count: {len(plan.findings)}",
        f"invariant_count: {len(plan.invariants)}",
        "credential_values_present: false",
    ]
    for item in plan.findings:
        lines.extend(
            [
                "",
                f"{item.finding_id}: {item.severity.value}",
                f"component: {item.component}",
                f"summary: {item.summary}",
                f"later_milestone: {item.later_milestone}",
            ]
        )
    return "\n".join(lines)


def render_credential_architecture(
    plan: CredentialArchitecturePlan,
    *,
    output_format: str,
) -> str:
    if output_format == "markdown":
        return build_credential_architecture_markdown(plan)
    if output_format == "text":
        return build_credential_architecture_text(plan)
    if output_format == "json":
        return json.dumps(
            credential_architecture_to_dict(plan),
            indent=2,
            sort_keys=True,
        )
    raise ValueError(f"unsupported output format: {output_format}")
