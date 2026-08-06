from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from online_asr_keys_accounts_review_workflow import (
    OnlineASRKeysAccountsReviewWorkflowResult,
    build_online_asr_keys_accounts_review_workflow,
    online_asr_keys_accounts_review_workflow_result_to_json,
)
from online_asr_provider_catalog import (
    ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED,
    ONLINE_ASR_CREDENTIAL_STATE_MISSING,
    ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE,
)


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_WORKFLOW_CLI_SCHEMA_VERSION = "online_asr_keys_accounts_review_workflow_cli_v1"
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
_SAFE_CREDENTIAL_STATES = frozenset(
    {
        ONLINE_ASR_CREDENTIAL_STATE_CONFIGURED,
        ONLINE_ASR_CREDENTIAL_STATE_MISSING,
        ONLINE_ASR_CREDENTIAL_STATE_UNAVAILABLE,
    }
)


@dataclass(frozen=True)
class OnlineASRWorkflowCLIProviderOption:
    provider_id: str
    display_name: str
    provider_family: str
    model_id: str
    credential_entry_id: str
    supports_keyterms: bool = False
    tags: tuple[str, ...] = ()
    recommended_for: tuple[str, ...] = ()


class OnlineASRWorkflowCLIError(ValueError):
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
                raise OnlineASRWorkflowCLIError(
                    f"Refusing {source}: secret-like field '{key}' must not be provided to metadata CLI"
                )
            _reject_unsafe_secret_keys(item, source=source)
    elif isinstance(value, list):
        for item in value:
            _reject_unsafe_secret_keys(item, source=source)


def _as_string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (_safe_text(value),) if _safe_text(value) else ()
    if isinstance(value, (list, tuple)):
        return tuple(_safe_text(item) for item in value if _safe_text(item))
    return (_safe_text(value),) if _safe_text(value) else ()


def _provider_options_from_json(data: Any) -> tuple[OnlineASRWorkflowCLIProviderOption, ...]:
    _reject_unsafe_secret_keys(data, source="provider catalogue JSON")
    if not isinstance(data, list):
        raise OnlineASRWorkflowCLIError("Provider catalogue JSON must be a list of provider objects")
    options: list[OnlineASRWorkflowCLIProviderOption] = []
    for index, item in enumerate(data):
        if not isinstance(item, Mapping):
            raise OnlineASRWorkflowCLIError(f"Provider entry {index} must be an object")
        provider_id = _safe_text(item.get("provider_id"))
        credential_entry_id = _safe_text(item.get("credential_entry_id"))
        if not provider_id or not credential_entry_id:
            raise OnlineASRWorkflowCLIError(
                f"Provider entry {index} must include provider_id and credential_entry_id"
            )
        options.append(
            OnlineASRWorkflowCLIProviderOption(
                provider_id=provider_id,
                display_name=_safe_text(item.get("display_name") or provider_id),
                provider_family=_safe_text(item.get("provider_family") or provider_id),
                model_id=_safe_text(item.get("model_id")),
                credential_entry_id=credential_entry_id,
                supports_keyterms=bool(item.get("supports_keyterms", False)),
                tags=_as_string_tuple(item.get("tags")),
                recommended_for=_as_string_tuple(item.get("recommended_for")),
            )
        )
    return tuple(options)


def _credential_statuses_from_json(data: Any | None) -> dict[str, str]:
    if data is None:
        return {}
    _reject_unsafe_secret_keys(data, source="credential status JSON")
    if not isinstance(data, Mapping):
        raise OnlineASRWorkflowCLIError("Credential status JSON must be an object keyed by credential_entry_id")
    statuses: dict[str, str] = {}
    for key, value in data.items():
        credential_entry_id = _safe_text(key)
        if isinstance(value, Mapping):
            state = _safe_text(value.get("state")).upper()
        else:
            state = _safe_text(value).upper()
        if state not in _SAFE_CREDENTIAL_STATES:
            raise OnlineASRWorkflowCLIError(
                f"Credential status for '{credential_entry_id}' must be CONFIGURED, MISSING, or UNAVAILABLE"
            )
        statuses[credential_entry_id] = state
    return statuses


def _load_gate_summary(path: str | None) -> Mapping[str, Any] | None:
    if not path:
        return None
    data = _load_json_file(path)
    _reject_unsafe_secret_keys(data, source="Online ASR gate summary JSON")
    if not isinstance(data, Mapping):
        raise OnlineASRWorkflowCLIError("Online ASR gate summary JSON must be an object")
    return dict(data)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a metadata-only Online ASR KEYS/ACCOUNTS review workflow. "
            "This writes safe JSON sidecars only; it does not read secrets or call providers."
        )
    )
    parser.add_argument("--provider-catalog-json", required=True)
    parser.add_argument("--credential-status-json")
    parser.add_argument("--online-asr-gate-summary-json")
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--created-at-utc", required=True)
    parser.add_argument("--app-version", default="")
    parser.add_argument("--added-provider-id", action="append", default=[])
    parser.add_argument("--selected-provider-id", default="")
    parser.add_argument("--keys-accounts-query", default="")
    parser.add_argument("--add-provider-query", default="")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a text summary instead of the full safe JSON result.",
    )
    return parser


def run_online_asr_keys_accounts_review_workflow_cli(
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
        providers = _provider_options_from_json(_load_json_file(args.provider_catalog_json))
        statuses = _credential_statuses_from_json(
            _load_json_file(args.credential_status_json) if args.credential_status_json else None
        )
        gate_summary = _load_gate_summary(args.online_asr_gate_summary_json)
        result = build_online_asr_keys_accounts_review_workflow(
            provider_options=providers,
            credential_statuses=statuses,
            output_directory=args.output_directory,
            package_id=args.package_id,
            created_at_utc=args.created_at_utc,
            added_provider_ids=args.added_provider_id,
            selected_provider_id=args.selected_provider_id,
            keys_accounts_query=args.keys_accounts_query,
            add_provider_query=args.add_provider_query,
            app_version=args.app_version,
            online_asr_gate_summary=gate_summary,
            allow_overwrite=not args.no_overwrite,
        )
    except OnlineASRWorkflowCLIError as exc:
        print(f"Online ASR KEYS/ACCOUNTS review workflow CLI error: {exc}", file=err)
        return 2
    except FileExistsError as exc:
        print(f"Online ASR KEYS/ACCOUNTS review workflow CLI error: {exc}", file=err)
        return 3
    except Exception as exc:  # pragma: no cover - CLI safety net for user-facing command failures.
        print(f"Online ASR KEYS/ACCOUNTS review workflow CLI unexpected error: {exc}", file=err)
        return 1

    if args.summary:
        print(result.to_summary_text(), file=out)
    else:
        print(online_asr_keys_accounts_review_workflow_result_to_json(result), end="", file=out)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_online_asr_keys_accounts_review_workflow_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
