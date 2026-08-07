from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_handoff_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_STATUS = "HANDOFF_READY_METADATA_ONLY"

_UNSAFE_INPUT_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "client_secret",
        "credential",
        "credential_value",
        "key",
        "key_value",
        "password",
        "secret",
        "secret_value",
        "token",
    }
)

_EXPECTED_FALSE_FLAGS = (
    "provider_call_allowed_without_user_approval",
    "runtime_provider_call_performed",
    "credential_value_read",
    "plaintext_secret_storage_allowed",
    "secret_value_recorded",
    "raw_media_payload_included",
    "raw_media_serialized",
    "full_local_path_included",
    "full_local_path_serialized",
    "completed_transcription_claimed",
    "verified_transcription_claimed",
)
_EXPECTED_TRUE_FLAGS = (
    "metadata_only",
    "local_only",
)
_ONLINE_ASR_KEYS_ACCOUNTS_HANDOFF_COMPONENTS = (
    "online_asr_provider_catalog",
    "online_asr_execution_gate",
    "online_asr_keys_accounts_app_state",
    "online_asr_keys_accounts_state_store",
    "online_asr_keys_accounts_review_export",
    "online_asr_keys_accounts_review_package",
    "online_asr_keys_accounts_review_package_store",
    "online_asr_keys_accounts_review_activity",
    "online_asr_keys_accounts_review_activity_store",
    "online_asr_keys_accounts_review_workflow",
    "online_asr_keys_accounts_review_workflow_cli",
    "online_asr_keys_accounts_review_smoke_fixture",
    "online_asr_keys_accounts_review_smoke_fixture_cli",
    "online_asr_keys_accounts_review_closeout",
    "online_asr_keys_accounts_review_closeout_store",
    "online_asr_keys_accounts_review_closeout_cli",
    "online_asr_keys_accounts_review_verifier",
    "online_asr_keys_accounts_review_verifier_store",
    "online_asr_keys_accounts_review_verifier_store_cli",
)
_NEXT_SESSION_CONTEXT_FILES = (
    "SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md",
    "SOURCE_EVIDENCE_ROADMAP.md",
    "PROJECT_CURRENT_STATE_HANDOFF.md",
    "CURRENT_DEV_STATE.md",
)
_NEXT_REVIEW_ACTIONS = (
    "Keep Online ASR provider execution gated until an explicit manual approval is recorded.",
    "Keep KEYS/ACCOUNTS showing added providers only while Add Provider searches the full catalogue.",
    "Use large-v3 Vulkan as the benchmark-backed local ASR baseline and do not replace it with small by convenience.",
    "Treat ElevenLabs Scribe v2 keyterms as the current best cloud-candidate path, pending explicit credential/provider-call approval.",
)


class OnlineASRReviewHandoffError(ValueError):
    pass


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())


def _reject_unsafe_secret_keys(value: Any, *, source: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = _safe_text(key).casefold()
            if (
                key_text in _UNSAFE_INPUT_KEYS
                or key_text.endswith("_secret")
                or key_text.endswith("_token")
            ):
                raise OnlineASRReviewHandoffError(
                    f"Refusing {source}: secret-like field '{key}' must not be provided to handoff builder"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, list):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


def _as_mapping(value: Mapping[str, Any] | Any, *, source: str) -> Mapping[str, Any]:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise OnlineASRReviewHandoffError(f"{source} must be a JSON object")
    _reject_unsafe_secret_keys(value, source=source)
    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (_safe_text(value),)
    if isinstance(value, Sequence):
        return tuple(_safe_text(item) for item in value)
    return (_safe_text(value),)


def _contains_path_like_value(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_path_like_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_path_like_value(item) for item in value)
    if not isinstance(value, str):
        return False
    lowered = value.casefold()
    return (
        ":\\" in value
        or ":/" in value
        or lowered.startswith("/home/")
        or lowered.startswith("/users/")
        or lowered.startswith("c:\\")
        or lowered.startswith("t:\\")
        or lowered.startswith("\\\\")
    )


def _json_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safety_issues(name: str, payload: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for flag in _EXPECTED_FALSE_FLAGS:
        if flag in payload and payload.get(flag) is not False:
            issues.append(f"{name}.{flag} must be false")
    for flag in _EXPECTED_TRUE_FLAGS:
        if payload.get(flag) is not True:
            issues.append(f"{name}.{flag} must be true")
    if payload.get("review_status") != "USER_REVIEW_REQUIRED":
        issues.append(f"{name}.review_status must be USER_REVIEW_REQUIRED")
    if payload.get("execution_state") != "EXECUTION_GATED":
        issues.append(f"{name}.execution_state must be EXECUTION_GATED")
    if _contains_path_like_value(payload):
        issues.append(f"{name} must not serialize full local paths")
    return issues


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewHandoffReport:
    package_id: str
    created_at_utc: str
    selected_provider_id: str
    source_schema_version: str
    review_verdict: str
    handoff_status: str
    completed_workflow_components: tuple[str, ...]
    completed_workflow_component_count: int
    next_session_context_files: tuple[str, ...]
    next_session_context_file_count: int
    next_review_actions: tuple[str, ...]
    next_review_action_count: int
    reviewed_artifact_names: tuple[str, ...]
    reviewed_artifact_hashes: tuple[str, ...]
    reviewed_artifact_count: int
    issue_count: int
    issues: tuple[str, ...]
    handoff_hash: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
    keys_accounts_shows_added_providers_only: bool = True
    add_provider_searches_full_catalog: bool = True
    online_asr_requires_explicit_provider_call_approval: bool = True
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS review handoff",
                f"Package ID: {self.package_id}",
                f"Selected provider: {self.selected_provider_id or 'none'}",
                f"Source schema: {self.source_schema_version}",
                f"Review verdict: {self.review_verdict}",
                f"Completed workflow components: {self.completed_workflow_component_count}",
                f"Next-session context files: {self.next_session_context_file_count}",
                f"Reviewed artifacts: {self.reviewed_artifact_count}",
                f"Issue count: {self.issue_count}",
                "Handoff status: HANDOFF_READY_METADATA_ONLY",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_handoff_report(
    verifier_store_cli_result: Mapping[str, Any] | Any,
    *,
    created_at_utc: str | None = None,
) -> OnlineASRKeysAccountsReviewHandoffReport:
    """Build a safe next-session handoff from the verifier-store CLI result.

    The handoff is intentionally metadata-only. It captures component names,
    expected roadmap context filenames, safe artifact filenames/hashes, and
    explicit safety flags. It does not read credential values, execute provider
    calls, process media, serialize full local paths, or claim a completed or
    verified transcription.
    """
    payload = _as_mapping(verifier_store_cli_result, source="verifier store CLI result")
    issues = _safety_issues("verifier_store_cli_result", payload)

    package_id = _safe_text(payload.get("package_id"))
    selected_provider_id = _safe_text(payload.get("selected_provider_id"))
    source_schema_version = _safe_text(payload.get("schema_version"))
    review_verdict = _safe_text(payload.get("review_verdict"))
    artifact_names = tuple(sorted(_string_tuple(payload.get("stored_file_names"))))
    artifact_hashes = tuple(sorted(_string_tuple(payload.get("stored_file_hashes"))))
    stored_file_count = int(payload.get("stored_file_count", 0) or 0)

    if not package_id:
        issues.append("verifier_store_cli_result.package_id is required")
    if not selected_provider_id:
        issues.append("verifier_store_cli_result.selected_provider_id is required")
    if not source_schema_version:
        issues.append("verifier_store_cli_result.schema_version is required")
    if stored_file_count != len(artifact_names):
        issues.append("verifier_store_cli_result.stored_file_count must match stored_file_names")
    if artifact_hashes and len(artifact_hashes) != len(artifact_names):
        issues.append("verifier_store_cli_result.stored_file_hashes must match stored_file_names")

    seed = {
        "package_id": package_id,
        "created_at_utc": str(created_at_utc or payload.get("created_at_utc") or ""),
        "selected_provider_id": selected_provider_id,
        "source_schema_version": source_schema_version,
        "review_verdict": review_verdict,
        "completed_workflow_components": list(_ONLINE_ASR_KEYS_ACCOUNTS_HANDOFF_COMPONENTS),
        "next_session_context_files": list(_NEXT_SESSION_CONTEXT_FILES),
        "next_review_actions": list(_NEXT_REVIEW_ACTIONS),
        "reviewed_artifact_names": list(artifact_names),
        "reviewed_artifact_hashes": list(artifact_hashes),
        "issue_count": len(issues),
        "handoff_status": ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_STATUS,
    }
    return OnlineASRKeysAccountsReviewHandoffReport(
        package_id=package_id,
        created_at_utc=seed["created_at_utc"],
        selected_provider_id=selected_provider_id,
        source_schema_version=source_schema_version,
        review_verdict=review_verdict,
        handoff_status=ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_STATUS,
        completed_workflow_components=_ONLINE_ASR_KEYS_ACCOUNTS_HANDOFF_COMPONENTS,
        completed_workflow_component_count=len(_ONLINE_ASR_KEYS_ACCOUNTS_HANDOFF_COMPONENTS),
        next_session_context_files=_NEXT_SESSION_CONTEXT_FILES,
        next_session_context_file_count=len(_NEXT_SESSION_CONTEXT_FILES),
        next_review_actions=_NEXT_REVIEW_ACTIONS,
        next_review_action_count=len(_NEXT_REVIEW_ACTIONS),
        reviewed_artifact_names=artifact_names,
        reviewed_artifact_hashes=artifact_hashes,
        reviewed_artifact_count=len(artifact_names),
        issue_count=len(issues),
        issues=tuple(issues),
        handoff_hash=_json_hash(seed),
    )


def online_asr_keys_accounts_review_handoff_report_to_json(
    report: OnlineASRKeysAccountsReviewHandoffReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
