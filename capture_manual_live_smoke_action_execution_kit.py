from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping

from capture_manual_live_smoke_action_implementation import (
    MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN,
    build_manual_live_smoke_action_plan,
    manual_live_smoke_action_plan_to_dict,
)


MANUAL_LIVE_SMOKE_ACTION_EXECUTION_KIT_SCHEMA_VERSION = "manual_live_smoke_action_execution_kit_v1"

_SAFE_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    return value


def _quote_cmd(value: str) -> str:
    return '"' + str(value).replace('"', "'") + '"'


def _safe_prefix(value: str) -> str:
    text = str(value or "manual_live_smoke_action").strip()
    if not _SAFE_PREFIX_RE.match(text):
        raise ValueError("file_prefix must be a safe identifier")
    return text


def _host_hint(source_url: str) -> str:
    host = re.sub(r"^https?://", "", source_url, flags=re.I).split("/", 1)[0].lower()
    return host[:80] or "unknown-host"


@dataclass(frozen=True)
class ManualLiveSmokeActionExecutionKitFile:
    file_name: str
    role: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"file_name": self.file_name, "role": self.role, "byte_count": len(self.text.encode("utf-8"))}


@dataclass(frozen=True)
class ManualLiveSmokeActionExecutionKit:
    site_id: str
    action_id: str
    source_url_host_hint: str
    file_prefix: str
    files: tuple[ManualLiveSmokeActionExecutionKitFile, ...]
    schema_version: str = MANUAL_LIVE_SMOKE_ACTION_EXECUTION_KIT_SCHEMA_VERSION
    implementation_bundle: bool = True
    local_only: bool = True
    operator_approved_execution_supported: bool = True
    metadata_only_until_operator_runs_generated_command: bool = True
    full_local_path_serialized: bool = False
    raw_media_payload_included: bool = False
    credential_value_read: bool = False
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = _value_for_dict(self)
        payload["file_count"] = len(self.files)
        return payload


def _action_specific_snippets(action_id: str, prefix: str) -> list[ManualLiveSmokeActionExecutionKitFile]:
    files: list[ManualLiveSmokeActionExecutionKitFile] = []
    if action_id == "msn_comments_shadow_root_capture":
        files.append(
            ManualLiveSmokeActionExecutionKitFile(
                file_name=f"{prefix}_msn_comments_shadow_root_snippet.js",
                role="operator_devtools_snippet",
                text=(
                    "// Manual MSN comments helper. Paste into DevTools only after selecting the approved page/frame.\n"
                    "// It does not fetch remote data; it only expands visible page containers in the operator browser.\n"
                    "for (const selector of ['social-comment-wc', '.overlay-container']) {\n"
                    "  for (const element of document.querySelectorAll(selector)) {\n"
                    "    element.style.setProperty('height', 'auto', 'important');\n"
                    "    element.style.setProperty('max-height', 'none', 'important');\n"
                    "    element.style.setProperty('overflow', 'visible', 'important');\n"
                    "  }\n"
                    "}\n"
                ),
            )
        )
        files.append(
            ManualLiveSmokeActionExecutionKitFile(
                file_name=f"{prefix}_msn_comments_capture_notes_template.md",
                role="operator_notes_template",
                text=(
                    "# MSN comments manual capture notes\n\n"
                    "- Named URL reviewed: <paste source URL>\n"
                    "- Browser/profile used: <Firefox/RDM/other>\n"
                    "- Comments frame selected: <yes/no/details>\n"
                    "- Shadow-root host observed: social-comment-wc / other\n"
                    "- Scroll strategy used: real scroll / resize / CSS expansion\n"
                    "- Known missing content or limits: <notes>\n"
                    "- Output artifact file names: <safe file names only>\n"
                ),
            )
        )
    if action_id == "archive_submission_prepare":
        files.append(
            ManualLiveSmokeActionExecutionKitFile(
                file_name=f"{prefix}_archive_result_template.json",
                role="archive_result_template",
                text=json.dumps(
                    {
                        "archive_service": "archive.ph | wayback | ghostarchive | perms.cc",
                        "source_url_reviewed": "<source URL>",
                        "archive_result_url": "<archive result URL>",
                        "operator_notes": "<safe notes only>",
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
            )
        )
    return files


def build_manual_live_smoke_action_execution_kit(
    *,
    site_id: str,
    action_id: str,
    source_url: str,
    operator_intent: str,
    file_prefix: str = "manual_live_smoke_action",
) -> ManualLiveSmokeActionExecutionKit:
    prefix = _safe_prefix(file_prefix)
    dry_plan = build_manual_live_smoke_action_plan(
        site_id=site_id,
        action_id=action_id,
        source_url=source_url,
        operator_intent=operator_intent,
        dry_run=True,
    )
    approved_plan = build_manual_live_smoke_action_plan(
        site_id=site_id,
        action_id=action_id,
        source_url=source_url,
        operator_intent=operator_intent,
        approval_token=MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN,
        dry_run=False,
    )
    dry_cmd = " ".join(
        [
            '"%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe"',
            "capture_manual_live_smoke_action_run_cli.py",
            "--site-id",
            _quote_cmd(dry_plan.site_id),
            "--action-id",
            _quote_cmd(dry_plan.action_id),
            "--source-url",
            _quote_cmd(dry_plan.source_url),
            "--operator-intent",
            _quote_cmd(dry_plan.operator_intent),
            "--output-dir",
            _quote_cmd("."),
            "--file-prefix",
            _quote_cmd(prefix),
        ]
    )
    approved_cmd = " ".join(
        [
            '"%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe"',
            "capture_manual_live_smoke_action_run_cli.py",
            "--site-id",
            _quote_cmd(approved_plan.site_id),
            "--action-id",
            _quote_cmd(approved_plan.action_id),
            "--source-url",
            _quote_cmd(approved_plan.source_url),
            "--operator-intent",
            _quote_cmd(approved_plan.operator_intent),
            "--approval-token",
            _quote_cmd(MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN),
            "--execute-approved",
            "--output-dir",
            _quote_cmd("."),
            "--file-prefix",
            _quote_cmd(prefix),
        ]
    )
    collect_cmd = " ".join(
        [
            '"%LOCALAPPDATA%\\Programs\\Python\\Python311\\python.exe"',
            "capture_manual_live_smoke_action_artifact_collect_cli.py",
            "--site-id",
            _quote_cmd(dry_plan.site_id),
            "--action-id",
            _quote_cmd(dry_plan.action_id),
            "--operator-summary",
            _quote_cmd("<safe operator summary>"),
            "--artifact",
            _quote_cmd("<role>=<artifact_file>"),
            "--output-json",
            _quote_cmd(f"{prefix}_observation_draft.json"),
            "--packet-output-dir",
            _quote_cmd("."),
        ]
    )
    artifact_roles = [contract.role for contract in approved_plan.artifact_contracts]
    operator_steps = [f"{index}. {step.title}: {step.instruction}" for index, step in enumerate(approved_plan.steps, start=1)]
    files = [
        ManualLiveSmokeActionExecutionKitFile(
            file_name=f"{prefix}_dry_run_action.cmd",
            role="dry_run_command",
            text=f"@echo off\r\nsetlocal\r\n{dry_cmd}\r\nendlocal\r\n",
        ),
        ManualLiveSmokeActionExecutionKitFile(
            file_name=f"{prefix}_run_approved_action.cmd",
            role="approved_action_command",
            text=f"@echo off\r\nsetlocal\r\n{approved_cmd}\r\nendlocal\r\n",
        ),
        ManualLiveSmokeActionExecutionKitFile(
            file_name=f"{prefix}_collect_artifacts_template.cmd",
            role="artifact_collect_command_template",
            text=f"@echo off\r\nsetlocal\r\nREM Replace <role>=<artifact_file> with one or more explicit role=file arguments.\r\n{collect_cmd}\r\nendlocal\r\n",
        ),
        ManualLiveSmokeActionExecutionKitFile(
            file_name=f"{prefix}_action_plan.json",
            role="action_plan_json",
            text=json.dumps(manual_live_smoke_action_plan_to_dict(approved_plan), indent=2, sort_keys=True) + "\n",
        ),
        ManualLiveSmokeActionExecutionKitFile(
            file_name=f"{prefix}_operator_steps.md",
            role="operator_steps",
            text=(
                f"# Manual live smoke action kit\n\n"
                f"Site: {approved_plan.site_label}\n\n"
                f"Action: {approved_plan.action_label}\n\n"
                f"Host hint: {_host_hint(approved_plan.source_url)}\n\n"
                "## Steps\n\n"
                + "\n".join(operator_steps)
                + "\n\n## Artifact roles\n\n"
                + "\n".join(f"- {role}" for role in artifact_roles)
                + "\n\nReview remains required before any capture is accepted.\n"
            ),
        ),
        ManualLiveSmokeActionExecutionKitFile(
            file_name=f"{prefix}_observation_artifact_template.json",
            role="observation_artifact_template",
            text=json.dumps(
                {
                    "site_id": approved_plan.site_id,
                    "requested_action": approved_plan.action_id,
                    "operator_summary": "<safe summary>",
                    "observed_artifacts": [
                        {
                            "role": role,
                            "file_name": "<safe-file-name>",
                            "sha256": "<64-character sha256>",
                            "byte_count": 0,
                        }
                        for role in artifact_roles
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        ),
    ]
    files.extend(_action_specific_snippets(approved_plan.action_id, prefix))
    return ManualLiveSmokeActionExecutionKit(
        site_id=approved_plan.site_id,
        action_id=approved_plan.action_id,
        source_url_host_hint=_host_hint(approved_plan.source_url),
        file_prefix=prefix,
        files=tuple(files),
    )


def manual_live_smoke_action_execution_kit_to_json(kit: ManualLiveSmokeActionExecutionKit) -> str:
    return json.dumps(kit.to_dict(), indent=2, sort_keys=True) + "\n"
