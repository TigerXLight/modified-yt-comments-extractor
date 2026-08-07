from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from online_asr_keys_accounts_review_safety_audit import (
    OnlineASRKeysAccountsReviewSafetyAuditError,
    build_online_asr_keys_accounts_review_safety_audit_report,
)
from online_asr_keys_accounts_review_safety_audit_store import (
    write_online_asr_keys_accounts_review_safety_audit_report,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_CLI_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_safety_audit_store_cli_v1"
)
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


class OnlineASRKeysAccountsReviewSafetyAuditStoreCLIError(ValueError):
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
                raise OnlineASRKeysAccountsReviewSafetyAuditStoreCLIError(
                    f"Refusing {source}: secret-like field '{key}' must not be provided to safety audit store CLI"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, list):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


def _load_safe_json_mapping(path: str | Path, *, source: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    _reject_unsafe_secret_keys(data, source=source)
    if not isinstance(data, Mapping):
        raise OnlineASRKeysAccountsReviewSafetyAuditStoreCLIError(f"{source} must be a JSON object")
    return dict(data)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewSafetyAuditStoreCLIResult:
    source_artifact_count: int
    review_verdict: str
    issue_count: int
    audit_schema_version: str
    store_schema_version: str
    store_output_directory_role: str
    schema_versions: tuple[str, ...]
    package_ids: tuple[str, ...]
    selected_provider_ids: tuple[str, ...]
    stored_file_count: int
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SAFETY_AUDIT_STORE_CLI_SCHEMA_VERSION
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
                "Online ASR KEYS/ACCOUNTS review safety audit store CLI",
                f"Review verdict: {self.review_verdict}",
                f"Source artifacts checked: {self.source_artifact_count}",
                f"Issue count: {self.issue_count}",
                f"Schema versions: {', '.join(self.schema_versions) or 'none'}",
                f"Packages: {', '.join(self.package_ids) or 'none'}",
                f"Selected providers: {', '.join(self.selected_provider_ids) or 'none'}",
                f"Stored audit files: {self.stored_file_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_safety_audit_store_cli_result(
    artifacts: Sequence[Mapping[str, Any]],
    output_directory: str | Path,
    *,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewSafetyAuditStoreCLIResult:
    """Build and persist a metadata-only Online ASR KEYS/ACCOUNTS safety audit.

    The caller supplies safe JSON-like metadata artifacts only. This function
    refuses secret-like input keys and does not read credential values, execute
    provider calls, process raw media, return full local paths, or claim
    completed/verified transcription.
    """
    if not artifacts:
        raise OnlineASRKeysAccountsReviewSafetyAuditStoreCLIError("at least one artifact JSON object is required")
    normalised = tuple(dict(artifact) for artifact in artifacts)
    _reject_unsafe_secret_keys(normalised, source="artifact JSON")
    report = build_online_asr_keys_accounts_review_safety_audit_report(normalised)
    store_result = write_online_asr_keys_accounts_review_safety_audit_report(
        report,
        output_directory,
        allow_overwrite=allow_overwrite,
    )
    files = tuple(store_result.files)
    return OnlineASRKeysAccountsReviewSafetyAuditStoreCLIResult(
        source_artifact_count=report.source_artifact_count,
        review_verdict=report.review_verdict,
        issue_count=report.issue_count,
        audit_schema_version=report.schema_version,
        store_schema_version=store_result.schema_version,
        store_output_directory_role=store_result.output_directory_role,
        schema_versions=report.schema_versions,
        package_ids=report.package_ids,
        selected_provider_ids=report.selected_provider_ids,
        stored_file_count=store_result.file_count,
        stored_file_names=tuple(file.filename for file in files),
        stored_file_hashes=tuple(file.sha256 for file in files),
    )


def online_asr_keys_accounts_review_safety_audit_store_cli_result_to_json(
    result: OnlineASRKeysAccountsReviewSafetyAuditStoreCLIResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build and persist a metadata-only Online ASR KEYS/ACCOUNTS safety audit "
            "from one or more safe JSON artifacts. This does not read secrets, call providers, or process media."
        )
    )
    parser.add_argument(
        "--artifact-json",
        action="append",
        required=True,
        help="Path to a safe metadata-only JSON object. Repeat for multiple artifacts.",
    )
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a text summary instead of the full safe JSON result.",
    )
    return parser


def run_online_asr_keys_accounts_review_safety_audit_store_cli(
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
        artifacts = tuple(
            _load_safe_json_mapping(path, source=f"artifact JSON {index + 1}")
            for index, path in enumerate(args.artifact_json or ())
        )
        result = build_online_asr_keys_accounts_review_safety_audit_store_cli_result(
            artifacts,
            args.output_directory,
            allow_overwrite=not args.no_overwrite,
        )
    except (
        OnlineASRKeysAccountsReviewSafetyAuditStoreCLIError,
        OnlineASRKeysAccountsReviewSafetyAuditError,
    ) as exc:
        print(f"Online ASR KEYS/ACCOUNTS safety audit store CLI error: {exc}", file=err)
        return 2
    except FileExistsError as exc:
        print(f"Online ASR KEYS/ACCOUNTS safety audit store CLI error: {exc}", file=err)
        return 3
    except Exception as exc:  # pragma: no cover - CLI safety net for user-facing command failures.
        print(f"Online ASR KEYS/ACCOUNTS safety audit store CLI unexpected error: {exc}", file=err)
        return 1

    if args.summary:
        print(result.to_summary_text(), file=out)
    else:
        print(
            online_asr_keys_accounts_review_safety_audit_store_cli_result_to_json(result),
            end="",
            file=out,
        )
    return 0


def main() -> int:
    return run_online_asr_keys_accounts_review_safety_audit_store_cli()


if __name__ == "__main__":
    raise SystemExit(main())
