from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from online_asr_keys_accounts_review_closeout import (
    ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_STATUS,
    build_online_asr_keys_accounts_review_closeout_report,
)
from online_asr_keys_accounts_review_closeout_store import (
    write_online_asr_keys_accounts_review_closeout_report,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_CLI_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_closeout_cli_v1"
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


class OnlineASRCloseoutCLIError(ValueError):
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
            if key_text in _UNSAFE_INPUT_KEYS or key_text.endswith("_secret") or key_text.endswith("_token"):
                raise OnlineASRCloseoutCLIError(
                    f"Refusing {source}: secret-like field '{key}' must not be provided to closeout CLI"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, list):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


def _load_safe_smoke_fixture_result(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    _reject_unsafe_secret_keys(data, source="smoke fixture result JSON")
    if not isinstance(data, Mapping):
        raise OnlineASRCloseoutCLIError("Smoke fixture result JSON must be an object")
    package_id = _safe_text(data.get("package_id"))
    selected_provider_id = _safe_text(data.get("selected_provider_id"))
    if not package_id or not selected_provider_id:
        raise OnlineASRCloseoutCLIError(
            "Smoke fixture result JSON must include package_id and selected_provider_id"
        )
    return dict(data)


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewCloseoutCLIResult:
    package_id: str
    selected_provider_id: str
    closeout_status: str
    report_schema_version: str
    store_schema_version: str
    stored_file_count: int
    stored_file_names: tuple[str, ...]
    stored_file_hashes: tuple[str, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_CLI_SCHEMA_VERSION
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
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False
    verified_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS review closeout CLI",
                f"Package ID: {self.package_id}",
                f"Selected provider: {self.selected_provider_id}",
                f"Closeout status: {self.closeout_status}",
                f"Stored closeout files: {self.stored_file_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Credential value read: false",
                "Completed transcription claimed: false",
            )
        )


def build_online_asr_keys_accounts_review_closeout_cli_result(
    smoke_fixture_result: Mapping[str, Any],
    output_directory: str | Path,
    *,
    created_at_utc: str | None = None,
    allow_overwrite: bool = True,
) -> OnlineASRKeysAccountsReviewCloseoutCLIResult:
    """Build, persist, and summarize the safe closeout report for a smoke fixture result."""
    report = build_online_asr_keys_accounts_review_closeout_report(
        smoke_fixture_result,
        created_at_utc=created_at_utc,
    )
    store_result = write_online_asr_keys_accounts_review_closeout_report(
        report,
        output_directory,
        allow_overwrite=allow_overwrite,
    )
    files = tuple(store_result.files)
    return OnlineASRKeysAccountsReviewCloseoutCLIResult(
        package_id=report.package_id,
        selected_provider_id=report.selected_provider_id,
        closeout_status=ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_CLOSEOUT_STATUS,
        report_schema_version=report.schema_version,
        store_schema_version=store_result.schema_version,
        stored_file_count=store_result.file_count,
        stored_file_names=tuple(file.filename for file in files),
        stored_file_hashes=tuple(file.sha256 for file in files),
    )


def online_asr_keys_accounts_review_closeout_cli_result_to_json(
    result: OnlineASRKeysAccountsReviewCloseoutCLIResult,
) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build and persist a metadata-only Online ASR KEYS/ACCOUNTS closeout report "
            "from a safe smoke fixture result. This does not read secrets, call providers, or process media."
        )
    )
    parser.add_argument("--smoke-fixture-result-json", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--created-at-utc")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a text summary instead of the full safe JSON result.",
    )
    return parser


def run_online_asr_keys_accounts_review_closeout_cli(
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
        smoke_fixture_result = _load_safe_smoke_fixture_result(args.smoke_fixture_result_json)
        result = build_online_asr_keys_accounts_review_closeout_cli_result(
            smoke_fixture_result,
            args.output_directory,
            created_at_utc=args.created_at_utc,
            allow_overwrite=not args.no_overwrite,
        )
    except OnlineASRCloseoutCLIError as exc:
        print(f"Online ASR KEYS/ACCOUNTS closeout CLI error: {exc}", file=err)
        return 2
    except FileExistsError as exc:
        print(f"Online ASR KEYS/ACCOUNTS closeout CLI error: {exc}", file=err)
        return 3
    except Exception as exc:  # pragma: no cover - CLI safety net for user-facing command failures.
        print(f"Online ASR KEYS/ACCOUNTS closeout CLI unexpected error: {exc}", file=err)
        return 1

    if args.summary:
        print(result.to_summary_text(), file=out)
    else:
        print(online_asr_keys_accounts_review_closeout_cli_result_to_json(result), end="", file=out)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_online_asr_keys_accounts_review_closeout_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
