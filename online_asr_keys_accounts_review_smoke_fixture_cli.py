from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from online_asr_keys_accounts_review_smoke_fixture import (
    build_online_asr_keys_accounts_review_smoke_fixture,
    online_asr_keys_accounts_review_smoke_fixture_result_to_json,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_SMOKE_FIXTURE_CLI_SCHEMA_VERSION = (
    "online_asr_keys_accounts_review_smoke_fixture_cli_v1"
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


class OnlineASRSmokeFixtureCLIError(ValueError):
    pass


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())


def _load_json_file(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _reject_unsafe_secret_keys(value: Any, *, source: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = _safe_text(key).casefold()
            if key_text in _UNSAFE_INPUT_KEYS or key_text.endswith("_secret") or key_text.endswith("_token"):
                raise OnlineASRSmokeFixtureCLIError(
                    f"Refusing {source}: secret-like field '{key}' must not be provided to smoke fixture CLI"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, list):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


def _load_safe_provider_catalog(path: str | None) -> list[dict[str, Any]] | None:
    if not path:
        return None
    data = _load_json_file(path)
    _reject_unsafe_secret_keys(data, source="provider catalogue JSON")
    if not isinstance(data, list):
        raise OnlineASRSmokeFixtureCLIError("Provider catalogue JSON must be a list of provider objects")
    providers: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, Mapping):
            raise OnlineASRSmokeFixtureCLIError(f"Provider entry {index} must be an object")
        provider_id = _safe_text(item.get("provider_id"))
        credential_entry_id = _safe_text(item.get("credential_entry_id"))
        if not provider_id or not credential_entry_id:
            raise OnlineASRSmokeFixtureCLIError(
                f"Provider entry {index} must include provider_id and credential_entry_id"
            )
        providers.append(dict(item))
    return providers


def _load_safe_credential_statuses(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    data = _load_json_file(path)
    _reject_unsafe_secret_keys(data, source="credential status JSON")
    if not isinstance(data, Mapping):
        raise OnlineASRSmokeFixtureCLIError("Credential status JSON must be an object keyed by credential_entry_id")
    statuses: dict[str, Any] = {}
    for key, value in data.items():
        credential_entry_id = _safe_text(key)
        if not credential_entry_id:
            raise OnlineASRSmokeFixtureCLIError("Credential status keys must not be blank")
        statuses[credential_entry_id] = value
    return statuses


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create safe local Online ASR KEYS/ACCOUNTS smoke fixtures and run the metadata-only "
            "review workflow. This does not read secrets, call providers, or process media."
        )
    )
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--created-at-utc", required=True)
    parser.add_argument("--app-version", default="")
    parser.add_argument("--selected-provider-id", default="elevenlabs_scribe_v2")
    parser.add_argument("--provider-catalog-json")
    parser.add_argument("--credential-status-json")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a text summary instead of the full safe JSON result.",
    )
    return parser


def run_online_asr_keys_accounts_review_smoke_fixture_cli(
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
        provider_catalog = _load_safe_provider_catalog(args.provider_catalog_json)
        credential_statuses = _load_safe_credential_statuses(args.credential_status_json)
        result = build_online_asr_keys_accounts_review_smoke_fixture(
            args.output_directory,
            package_id=args.package_id,
            created_at_utc=args.created_at_utc,
            app_version=args.app_version,
            selected_provider_id=args.selected_provider_id,
            provider_catalog=provider_catalog,
            credential_statuses=credential_statuses,
            allow_overwrite=not args.no_overwrite,
        )
    except OnlineASRSmokeFixtureCLIError as exc:
        print(f"Online ASR KEYS/ACCOUNTS smoke fixture CLI error: {exc}", file=err)
        return 2
    except FileExistsError as exc:
        print(f"Online ASR KEYS/ACCOUNTS smoke fixture CLI error: {exc}", file=err)
        return 3
    except Exception as exc:  # pragma: no cover - CLI safety net for user-facing command failures.
        print(f"Online ASR KEYS/ACCOUNTS smoke fixture CLI unexpected error: {exc}", file=err)
        return 1

    if args.summary:
        print(result.to_summary_text(), file=out)
    else:
        print(online_asr_keys_accounts_review_smoke_fixture_result_to_json(result), end="", file=out)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_online_asr_keys_accounts_review_smoke_fixture_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
