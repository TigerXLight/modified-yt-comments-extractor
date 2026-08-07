from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from online_asr_keys_accounts_review_handoff_verifier import (
    OnlineASRHandoffVerifierError,
    build_online_asr_keys_accounts_review_handoff_verification_report,
)
from online_asr_keys_accounts_review_handoff_verifier_store import (
    write_online_asr_keys_accounts_review_handoff_verification_report,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_CLI_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_handoff_verifier_store_cli_v1"
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


class OnlineASRHandoffVerifierStoreCLIError(ValueError):
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
                raise OnlineASRHandoffVerifierStoreCLIError(
                    f"Refusing {source}: secret-like field '{key}' must not be provided to handoff verifier store CLI"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, list):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


def _load_safe_json_mapping(path: str | Path, *, source: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    _reject_unsafe_secret_keys(data, source=source)
    if not isinstance(data, Mapping):
        raise OnlineASRHandoffVerifierStoreCLIError(f"{source} must be a JSON object")
    return dict(data)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewHandoffVerifierStoreCLIResult:
    package_id: str
    selected_provider_id: str
    review_verdict: str
    source_review_verdict: str
    handoff_status: str
    handoff_store_cli_schema_version: str
    verifier_schema_version: str
    store_schema_version: str
    store_output_directory_role: str
    issue_count: int
    required_context_file_count: int
    stored_handoff_file_count: int
    stored_file_count: int
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_HANDOFF_VERIFIER_STORE_CLI_SCHEMA_VERSION
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
                "Online ASR KEYS/ACCOUNTS review handoff verifier store CLI",
                f"Package ID: {self.package_id}",
                f"Selected provider: {self.selected_provider_id or 'none'}",
                f"Handoff status: {self.handoff_status}",
                f"Source review verdict: {self.source_review_verdict}",
                f"Review verdict: {self.review_verdict}",
                f"Issue count: {self.issue_count}",
                f"Required context files: {self.required_context_file_count}",
                f"Stored handoff files checked: {self.stored_handoff_file_count}",
                f"Stored verifier files: {self.stored_file_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_handoff_verifier_store_cli_result(
    handoff_store_cli_result: Mapping[str, Any],
    output_directory: str | Path,
    *,
    created_at_utc: str | None = None,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewHandoffVerifierStoreCLIResult:
    """Build, verify, persist, and summarize a safe handoff verifier report.

    The caller supplies only the metadata-only handoff-store CLI result. This
    function never reads credential values, executes provider calls, processes
    raw media, returns full local paths, or claims completed/verified
    transcription.
    """
    _reject_unsafe_secret_keys(handoff_store_cli_result, source="handoff store CLI result")
    report = build_online_asr_keys_accounts_review_handoff_verification_report(
        handoff_store_cli_result,
        created_at_utc=created_at_utc,
    )
    store_result = write_online_asr_keys_accounts_review_handoff_verification_report(
        report,
        output_directory,
        allow_overwrite=allow_overwrite,
    )
    files = tuple(store_result.files)
    return OnlineASRKeysAccountsReviewHandoffVerifierStoreCLIResult(
        package_id=report.package_id,
        selected_provider_id=report.selected_provider_id,
        review_verdict=report.review_verdict,
        source_review_verdict=report.source_review_verdict,
        handoff_status=report.handoff_status,
        handoff_store_cli_schema_version=report.handoff_store_cli_schema_version,
        verifier_schema_version=report.schema_version,
        store_schema_version=store_result.schema_version,
        store_output_directory_role=store_result.output_directory_role,
        issue_count=report.issue_count,
        required_context_file_count=report.required_context_file_count,
        stored_handoff_file_count=report.stored_file_count,
        stored_file_count=store_result.file_count,
        stored_file_names=tuple(file.filename for file in files),
        stored_file_hashes=tuple(file.sha256 for file in files),
    )


def online_asr_keys_accounts_review_handoff_verifier_store_cli_result_to_json(
    result: OnlineASRKeysAccountsReviewHandoffVerifierStoreCLIResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build, verify, and persist a metadata-only Online ASR KEYS/ACCOUNTS handoff verifier "
            "from a safe handoff-store CLI result. This does not read secrets, call providers, or process media."
        )
    )
    parser.add_argument("--handoff-store-cli-result-json", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--created-at-utc")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a text summary instead of the full safe JSON result.",
    )
    return parser


def run_online_asr_keys_accounts_review_handoff_verifier_store_cli(
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
        handoff_store_cli_result = _load_safe_json_mapping(
            args.handoff_store_cli_result_json,
            source="handoff store CLI result JSON",
        )
        result = build_online_asr_keys_accounts_review_handoff_verifier_store_cli_result(
            handoff_store_cli_result,
            args.output_directory,
            created_at_utc=args.created_at_utc,
            allow_overwrite=not args.no_overwrite,
        )
    except (OnlineASRHandoffVerifierStoreCLIError, OnlineASRHandoffVerifierError) as exc:
        print(f"Online ASR KEYS/ACCOUNTS handoff verifier store CLI error: {exc}", file=err)
        return 2
    except FileExistsError as exc:
        print(f"Online ASR KEYS/ACCOUNTS handoff verifier store CLI error: {exc}", file=err)
        return 3
    except Exception as exc:  # pragma: no cover - CLI safety net for user-facing command failures.
        print(f"Online ASR KEYS/ACCOUNTS handoff verifier store CLI unexpected error: {exc}", file=err)
        return 1

    if args.summary:
        print(result.to_summary_text(), file=out)
    else:
        print(
            online_asr_keys_accounts_review_handoff_verifier_store_cli_result_to_json(result),
            end="",
            file=out,
        )
    return 0 if result.issue_count == 0 else 4


def main(argv: Sequence[str] | None = None) -> int:
    return run_online_asr_keys_accounts_review_handoff_verifier_store_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
