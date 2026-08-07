from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_release_gate_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY = (
    "READY_FOR_USER_REVIEW_METADATA_ONLY"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW = (
    "NEEDS_USER_REVIEW"
)

REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS = (
    "online_asr_keys_accounts_review_workflow_cli_v1",
    "online_asr_keys_accounts_review_closeout_cli_v1",
    "online_asr_keys_accounts_review_verifier_store_cli_v1",
    "online_asr_keys_accounts_review_handoff_verifier_store_cli_v1",
    "online_asr_keys_accounts_review_safety_audit_store_cli_v1",
)

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
_UNSAFE_VERDICT_MARKERS = ("FAILED", "FAILURE", "ERROR", "NEEDS", "UNSAFE", "BLOCKED")
_FULL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\|[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)"
)


class OnlineASRKeysAccountsReviewReleaseGateError(ValueError):
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
    return text[:128] or "unknown"


def _normalise_artifacts(artifacts: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    if isinstance(artifacts, Mapping):
        return (dict(artifacts),)
    if isinstance(artifacts, (str, bytes)):
        raise OnlineASRKeysAccountsReviewReleaseGateError(
            "artifacts must be a JSON object or a sequence of JSON objects"
        )
    normalised: list[dict[str, Any]] = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            raise OnlineASRKeysAccountsReviewReleaseGateError(f"artifact {index} must be a JSON object")
        normalised.append(dict(artifact))
    if not normalised:
        raise OnlineASRKeysAccountsReviewReleaseGateError("at least one artifact is required")
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


def _is_secret_like_key(key: Any) -> bool:
    text = _safe_text(key).casefold()
    return text in _SECRET_LIKE_KEYS or text.endswith("_secret") or text.endswith("_token")


def _looks_like_full_local_path(value: Any) -> bool:
    return isinstance(value, str) and bool(_FULL_PATH_RE.search(value))


def _safe_string_tuple(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(sorted({_safe_component(value) for value in values if _safe_text(value)}))


def _extract_string_items(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (_safe_component(value),) if _safe_text(value) else ()
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return _safe_string_tuple(value)
    return ()


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewReleaseGateIssue:
    artifact_index: int
    field_path: str
    issue_code: str
    expected: str
    observed: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewReleaseGateReport:
    source_artifact_count: int
    review_verdict: str
    release_gate_ready: bool
    issue_count: int
    issues: tuple[OnlineASRKeysAccountsReviewReleaseGateIssue, ...]
    required_schema_versions: tuple[str, ...]
    observed_schema_versions: tuple[str, ...]
    missing_schema_versions: tuple[str, ...]
    coverage_component_count: int
    package_ids: tuple[str, ...]
    selected_provider_ids: tuple[str, ...]
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    user_selected_directory_required: bool = True
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
                "Online ASR KEYS/ACCOUNTS review release gate",
                f"Review verdict: {self.review_verdict}",
                f"Release gate ready: {str(self.release_gate_ready).lower()}",
                f"Source artifacts checked: {self.source_artifact_count}",
                f"Component coverage: {self.coverage_component_count}/{len(self.required_schema_versions)}",
                f"Issue count: {self.issue_count}",
                f"Missing schema versions: {', '.join(self.missing_schema_versions) or 'none'}",
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
    issues: list[OnlineASRKeysAccountsReviewReleaseGateIssue],
    *,
    artifact_index: int,
    field_path: str,
    issue_code: str,
    expected: str,
    observed: Any,
) -> None:
    issues.append(
        OnlineASRKeysAccountsReviewReleaseGateIssue(
            artifact_index=artifact_index,
            field_path=_safe_component(field_path),
            issue_code=issue_code,
            expected=expected,
            observed=_safe_component(type(observed).__name__ if isinstance(observed, (dict, list)) else observed),
        )
    )


def build_online_asr_keys_accounts_review_release_gate_report(
    artifacts: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    required_schema_versions: Sequence[str] = REQUIRED_ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_COMPONENT_SCHEMAS,
) -> OnlineASRKeysAccountsReviewReleaseGateReport:
    """Build the metadata-only release gate report for Online ASR KEYS/ACCOUNTS review artifacts.

    This checks that the safe review chain contains expected component schema
    coverage and preserves safety invariants. It does not read credential values,
    execute provider calls, process raw media, expose full local paths, or claim
    completed/verified transcription.
    """
    normalised = _normalise_artifacts(artifacts)
    required = tuple(_safe_component(version) for version in required_schema_versions)
    issues: list[OnlineASRKeysAccountsReviewReleaseGateIssue] = []
    observed_schema_versions: set[str] = set()
    package_ids: set[str] = set()
    selected_provider_ids: set[str] = set()
    stored_file_names: set[str] = set()
    stored_file_hashes: set[str] = set()

    for artifact_index, artifact in enumerate(normalised):
        schema_version = _safe_text(artifact.get("schema_version"))
        if schema_version:
            observed_schema_versions.add(_safe_component(schema_version))
        package_id = _safe_text(artifact.get("package_id"))
        if package_id:
            package_ids.add(_safe_component(package_id))
        selected_provider_id = _safe_text(artifact.get("selected_provider_id"))
        if selected_provider_id:
            selected_provider_ids.add(_safe_component(selected_provider_id))
        stored_file_names.update(_extract_string_items(artifact.get("stored_file_names")))
        stored_file_hashes.update(_extract_string_items(artifact.get("stored_file_hashes")))

        issue_count = artifact.get("issue_count")
        if isinstance(issue_count, int) and issue_count != 0:
            _add_issue(
                issues,
                artifact_index=artifact_index,
                field_path="issue_count",
                issue_code="source_issue_count_not_zero",
                expected="0",
                observed=issue_count,
            )

        review_verdict = _safe_text(artifact.get("review_verdict"))
        verdict_upper = review_verdict.upper()
        if review_verdict and any(marker in verdict_upper for marker in _UNSAFE_VERDICT_MARKERS):
            _add_issue(
                issues,
                artifact_index=artifact_index,
                field_path="review_verdict",
                issue_code="source_verdict_not_ready",
                expected="READY metadata-only verdict",
                observed=review_verdict,
            )

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
                    expected="no secret-like fields",
                    observed=key,
                )
            if _looks_like_full_local_path(value):
                _add_issue(
                    issues,
                    artifact_index=artifact_index,
                    field_path=field_path,
                    issue_code="full_local_path_present",
                    expected="safe filename/hash/role only",
                    observed="full_local_path_like_value",
                )

    observed = tuple(sorted(observed_schema_versions))
    missing = tuple(version for version in required if version not in observed_schema_versions)
    for version in missing:
        _add_issue(
            issues,
            artifact_index=-1,
            field_path="schema_version",
            issue_code="required_component_schema_missing",
            expected=version,
            observed="missing",
        )

    issue_tuple = tuple(issues)
    ready = not issue_tuple
    return OnlineASRKeysAccountsReviewReleaseGateReport(
        source_artifact_count=len(normalised),
        review_verdict=(
            ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_READY
            if ready
            else ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_RELEASE_GATE_VERDICT_NEEDS_REVIEW
        ),
        release_gate_ready=ready,
        issue_count=len(issue_tuple),
        issues=issue_tuple,
        required_schema_versions=required,
        observed_schema_versions=observed,
        missing_schema_versions=missing,
        coverage_component_count=len(required) - len(missing),
        package_ids=tuple(sorted(package_ids)),
        selected_provider_ids=tuple(sorted(selected_provider_ids)),
        stored_file_names=tuple(sorted(stored_file_names)),
        stored_file_hashes=tuple(sorted(stored_file_hashes)),
    )


def online_asr_keys_accounts_review_release_gate_report_to_json(
    report: OnlineASRKeysAccountsReviewReleaseGateReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
