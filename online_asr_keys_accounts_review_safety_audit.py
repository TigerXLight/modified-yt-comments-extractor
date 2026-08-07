from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_safety_audit_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY = "SAFETY_REVIEW_READY_METADATA_ONLY"
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_NEEDS_REVIEW = "SAFETY_NEEDS_USER_REVIEW"

_FALSE_SAFETY_FLAGS = (
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
_TRUE_SAFETY_FLAGS = (
    "metadata_only",
    "local_only",
    "user_selected_directory_required",
)
_EXPECTED_TEXT_FIELDS = {
    "review_status": "USER_REVIEW_REQUIRED",
    "execution_state": "EXECUTION_GATED",
    "keys_accounts_sidebar_label": "KEYS/ACCOUNTS",
}
_SECRET_LIKE_KEYS = frozenset(
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
_FULL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\|[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)"
)


class OnlineASRKeysAccountsReviewSafetyAuditError(ValueError):
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


def _safe_component(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return "unknown"
    text = re.sub(r"[^A-Za-z0-9_.:-]+", "_", text)
    return text[:96] or "unknown"


def _is_secret_like_key(key: Any) -> bool:
    text = _safe_text(key).casefold()
    return text in _SECRET_LIKE_KEYS or text.endswith("_secret") or text.endswith("_token")


def _looks_like_full_local_path(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_FULL_PATH_RE.search(value))


def _normalise_artifacts(artifacts: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    if isinstance(artifacts, Mapping):
        return (dict(artifacts),)
    if isinstance(artifacts, (str, bytes)):
        raise OnlineASRKeysAccountsReviewSafetyAuditError("artifacts must be a JSON object or a sequence of JSON objects")
    normalised: list[dict[str, Any]] = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            raise OnlineASRKeysAccountsReviewSafetyAuditError(f"artifact {index} must be a JSON object")
        normalised.append(dict(artifact))
    if not normalised:
        raise OnlineASRKeysAccountsReviewSafetyAuditError("at least one artifact is required")
    return tuple(normalised)


def _iter_pairs(value: Any, *, prefix: str = "artifact") -> Iterable[tuple[str, Any, Any]]:
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda item: str(item)):
            child_prefix = f"{prefix}.{_safe_component(key)}"
            yield child_prefix, key, value[key]
            yield from _iter_pairs(value[key], prefix=child_prefix)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_pairs(item, prefix=f"{prefix}[{index}]")


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewSafetyAuditIssue:
    artifact_index: int
    field_path: str
    issue_code: str
    expected: str
    observed: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewSafetyAuditReport:
    source_artifact_count: int
    review_verdict: str
    issue_count: int
    issues: tuple[OnlineASRKeysAccountsReviewSafetyAuditIssue, ...]
    schema_versions: tuple[str, ...]
    package_ids: tuple[str, ...]
    selected_provider_ids: tuple[str, ...]
    false_safety_flag_count: int
    true_safety_flag_count: int
    expected_text_field_count: int
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    raw_media_serialized: bool = False
    full_local_path_included: bool = False
    full_local_path_serialized: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS review safety audit",
                f"Review verdict: {self.review_verdict}",
                f"Source artifacts checked: {self.source_artifact_count}",
                f"Issue count: {self.issue_count}",
                f"Schema versions: {', '.join(self.schema_versions) or 'none'}",
                f"Packages: {', '.join(self.package_ids) or 'none'}",
                f"Selected providers: {', '.join(self.selected_provider_ids) or 'none'}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def _add_issue(
    issues: list[OnlineASRKeysAccountsReviewSafetyAuditIssue],
    *,
    artifact_index: int,
    field_path: str,
    issue_code: str,
    expected: str,
    observed: Any,
) -> None:
    issues.append(
        OnlineASRKeysAccountsReviewSafetyAuditIssue(
            artifact_index=artifact_index,
            field_path=_safe_component(field_path),
            issue_code=issue_code,
            expected=expected,
            observed=_safe_component(type(observed).__name__ if isinstance(observed, (dict, list)) else observed),
        )
    )


def build_online_asr_keys_accounts_review_safety_audit_report(
    artifacts: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> OnlineASRKeysAccountsReviewSafetyAuditReport:
    """Audit Online ASR KEYS/ACCOUNTS metadata artifacts for safety invariants.

    This is a metadata-only reviewer. It does not read credential values, execute
    provider calls, process media, expose full paths, or validate transcript
    correctness. It checks that supplied JSON-like artifacts preserve those
    safety limits before a human review step.
    """
    normalised = _normalise_artifacts(artifacts)
    issues: list[OnlineASRKeysAccountsReviewSafetyAuditIssue] = []
    schema_versions: set[str] = set()
    package_ids: set[str] = set()
    selected_provider_ids: set[str] = set()

    for artifact_index, artifact in enumerate(normalised):
        schema_version = _safe_text(artifact.get("schema_version"))
        if schema_version:
            schema_versions.add(schema_version)
        package_id = _safe_text(artifact.get("package_id"))
        if package_id:
            package_ids.add(package_id)
        selected_provider_id = _safe_text(artifact.get("selected_provider_id"))
        if selected_provider_id:
            selected_provider_ids.add(selected_provider_id)

        for key in _FALSE_SAFETY_FLAGS:
            if key in artifact and artifact[key] is not False:
                _add_issue(
                    issues,
                    artifact_index=artifact_index,
                    field_path=key,
                    issue_code="false_safety_flag_not_false",
                    expected="false",
                    observed=artifact[key],
                )
        for key in _TRUE_SAFETY_FLAGS:
            if key in artifact and artifact[key] is not True:
                _add_issue(
                    issues,
                    artifact_index=artifact_index,
                    field_path=key,
                    issue_code="true_safety_flag_not_true",
                    expected="true",
                    observed=artifact[key],
                )
        for key, expected in _EXPECTED_TEXT_FIELDS.items():
            if key in artifact and artifact[key] != expected:
                _add_issue(
                    issues,
                    artifact_index=artifact_index,
                    field_path=key,
                    issue_code="expected_text_field_mismatch",
                    expected=expected,
                    observed=artifact[key],
                )

        for field_path, key, value in _iter_pairs(artifact):
            if _is_secret_like_key(key):
                _add_issue(
                    issues,
                    artifact_index=artifact_index,
                    field_path=field_path,
                    issue_code="secret_like_field_present",
                    expected="secret-like fields absent",
                    observed=key,
                )
            if _looks_like_full_local_path(value):
                _add_issue(
                    issues,
                    artifact_index=artifact_index,
                    field_path=field_path,
                    issue_code="full_local_path_value_present",
                    expected="no full local path values",
                    observed="full_local_path_value",
                )

    review_verdict = (
        ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_READY
        if not issues
        else ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_VERDICT_NEEDS_REVIEW
    )
    return OnlineASRKeysAccountsReviewSafetyAuditReport(
        source_artifact_count=len(normalised),
        review_verdict=review_verdict,
        issue_count=len(issues),
        issues=tuple(issues),
        schema_versions=tuple(sorted(schema_versions)),
        package_ids=tuple(sorted(package_ids)),
        selected_provider_ids=tuple(sorted(selected_provider_ids)),
        false_safety_flag_count=len(_FALSE_SAFETY_FLAGS),
        true_safety_flag_count=len(_TRUE_SAFETY_FLAGS),
        expected_text_field_count=len(_EXPECTED_TEXT_FIELDS),
    )


def online_asr_keys_accounts_review_safety_audit_report_to_json(
    report: OnlineASRKeysAccountsReviewSafetyAuditReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
