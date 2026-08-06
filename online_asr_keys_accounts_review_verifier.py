from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERIFIER_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_verifier_v1"
)
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERDICT_READY = "REVIEW_READY_METADATA_ONLY"
ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERDICT_NEEDS_REVIEW = "NEEDS_USER_REVIEW"

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
    "full_local_path_included",
    "completed_transcription_claimed",
    "verified_transcription_claimed",
)
_EXPECTED_TRUE_FLAGS = (
    "metadata_only",
    "local_only",
)


class OnlineASRReviewVerifierError(ValueError):
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
                raise OnlineASRReviewVerifierError(
                    f"Refusing {source}: secret-like field '{key}' must not be provided"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, list):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


def _as_mapping(value: Mapping[str, Any] | Any, *, source: str) -> Mapping[str, Any]:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise OnlineASRReviewVerifierError(f"{source} must be a JSON object")
    _reject_unsafe_secret_keys(value, source=source)
    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(_safe_text(item) for item in value)
    return (_safe_text(value),)


def _contains_path_like_value(value: Any) -> bool:
    """Conservative check for accidental local-path exposure in result values."""
    if isinstance(value, Mapping):
        return any(_contains_path_like_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_path_like_value(item) for item in value)
    if not isinstance(value, str):
        return False
    lowered = value.casefold()
    # Filenames are allowed; Windows/Unix absolute or user-home paths are not.
    return (
        ":\\" in value
        or ":/" in value
        or lowered.startswith("/home/")
        or lowered.startswith("/users/")
        or lowered.startswith("c:\\")
        or lowered.startswith("t:\\")
        or lowered.startswith("\\\\")
    )


def _safety_issues(name: str, payload: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for flag in _EXPECTED_FALSE_FLAGS:
        if payload.get(flag) is not False:
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
class OnlineASRKeysAccountsReviewVerificationReport:
    package_id: str
    selected_provider_id: str
    created_at_utc: str
    closeout_cli_schema_version: str
    closeout_report_schema_version: str
    reviewed_artifact_names: tuple[str, ...]
    reviewed_artifact_count: int
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    stored_file_count: int
    issue_count: int
    issues: tuple[str, ...]
    review_verdict: str
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERIFIER_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    local_only: bool = True
    keys_accounts_sidebar_label: str = "KEYS/ACCOUNTS"
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
                "Online ASR KEYS/ACCOUNTS review verifier",
                f"Package ID: {self.package_id}",
                f"Selected provider: {self.selected_provider_id or 'none'}",
                f"Reviewed artifacts: {self.reviewed_artifact_count}",
                f"Stored metadata files: {self.stored_file_count}",
                f"Issue count: {self.issue_count}",
                f"Review verdict: {self.review_verdict}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_verification_report(
    closeout_cli_result: Mapping[str, Any] | Any,
    closeout_report: Mapping[str, Any] | Any | None = None,
    *,
    created_at_utc: str | None = None,
) -> OnlineASRKeysAccountsReviewVerificationReport:
    """Validate safe Online ASR KEYS/ACCOUNTS closeout artifacts.

    The verifier reads only previously generated metadata summaries. It rejects
    secret-like input keys, checks the explicit safety flags, and returns only
    safe names, counts, hashes, and issue text. It does not read credential
    values, execute provider calls, process raw media, expose full local paths,
    or claim a completed/verified transcription.
    """
    cli_payload = _as_mapping(closeout_cli_result, source="closeout CLI result")
    report_payload = (
        _as_mapping(closeout_report, source="closeout report")
        if closeout_report is not None
        else None
    )

    issues = _safety_issues("closeout_cli_result", cli_payload)
    package_id = _safe_text(cli_payload.get("package_id"))
    selected_provider_id = _safe_text(cli_payload.get("selected_provider_id"))
    if not package_id:
        issues.append("closeout_cli_result.package_id is required")
    if not selected_provider_id:
        issues.append("closeout_cli_result.selected_provider_id is required")

    stored_file_names = _string_tuple(cli_payload.get("stored_file_names"))
    stored_file_hashes = _string_tuple(cli_payload.get("stored_file_hashes"))
    stored_file_count = int(cli_payload.get("stored_file_count", 0) or 0)
    if stored_file_count != len(stored_file_names):
        issues.append("closeout_cli_result.stored_file_count must match stored_file_names")
    if stored_file_hashes and len(stored_file_hashes) != len(stored_file_names):
        issues.append("closeout_cli_result.stored_file_hashes must match stored_file_names")

    closeout_report_schema_version = ""
    reviewed_artifacts = ["closeout_cli_result"]
    if report_payload is not None:
        reviewed_artifacts.append("closeout_report")
        issues.extend(_safety_issues("closeout_report", report_payload))
        closeout_report_schema_version = _safe_text(report_payload.get("schema_version"))
        if _safe_text(report_payload.get("package_id")) != package_id:
            issues.append("closeout_report.package_id must match closeout CLI result")
        if _safe_text(report_payload.get("selected_provider_id")) != selected_provider_id:
            issues.append("closeout_report.selected_provider_id must match closeout CLI result")

    verdict = (
        ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERDICT_READY
        if not issues
        else ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_VERDICT_NEEDS_REVIEW
    )
    return OnlineASRKeysAccountsReviewVerificationReport(
        package_id=package_id,
        selected_provider_id=selected_provider_id,
        created_at_utc=_safe_text(created_at_utc),
        closeout_cli_schema_version=_safe_text(cli_payload.get("schema_version")),
        closeout_report_schema_version=closeout_report_schema_version,
        reviewed_artifact_names=tuple(reviewed_artifacts),
        reviewed_artifact_count=len(reviewed_artifacts),
        stored_file_names=stored_file_names,
        stored_file_hashes=stored_file_hashes,
        stored_file_count=stored_file_count,
        issue_count=len(issues),
        issues=tuple(issues),
        review_verdict=verdict,
    )


def online_asr_keys_accounts_review_verification_report_to_json(
    report: OnlineASRKeysAccountsReviewVerificationReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def _load_json_file(path: str | Path, *, source: str) -> Mapping[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _as_mapping(data, source=source)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify metadata-only Online ASR KEYS/ACCOUNTS closeout artifacts. "
            "This does not read secrets, call providers, or process media."
        )
    )
    parser.add_argument("--closeout-cli-result-json", required=True)
    parser.add_argument("--closeout-report-json")
    parser.add_argument("--created-at-utc")
    parser.add_argument("--summary", action="store_true")
    return parser


def run_online_asr_keys_accounts_review_verifier_cli(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
        cli_payload = _load_json_file(
            args.closeout_cli_result_json,
            source="closeout CLI result JSON",
        )
        report_payload = (
            _load_json_file(args.closeout_report_json, source="closeout report JSON")
            if args.closeout_report_json
            else None
        )
        report = build_online_asr_keys_accounts_review_verification_report(
            cli_payload,
            report_payload,
            created_at_utc=args.created_at_utc,
        )
    except OnlineASRReviewVerifierError as exc:
        print(f"Online ASR KEYS/ACCOUNTS verifier error: {exc}", file=err)
        return 2
    except Exception as exc:  # pragma: no cover - CLI safety net for user-facing failures.
        print(f"Online ASR KEYS/ACCOUNTS verifier unexpected error: {exc}", file=err)
        return 1

    if args.summary:
        print(report.to_summary_text(), file=out)
    else:
        print(online_asr_keys_accounts_review_verification_report_to_json(report), end="", file=out)
    return 0 if report.issue_count == 0 else 4


def main(argv: Sequence[str] | None = None) -> int:
    return run_online_asr_keys_accounts_review_verifier_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
