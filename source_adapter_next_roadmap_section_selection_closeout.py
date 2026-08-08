from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_release_regression_next_roadmap_closeout import (
    HANDOFF_STATUS as RELEASE_NEXT_HANDOFF_STATUS,
    STATUS as RELEASE_NEXT_STATUS,
    example_release_regression_next_roadmap_closeout_package,
)

SCHEMA_VERSION = "source_adapter_next_roadmap_section_selection_closeout_v1"
SECTION_INDEX_SCHEMA_VERSION = "source_adapter_next_roadmap_section_selection_index_v1"
WORK_ORDER_SCHEMA_VERSION = "source_adapter_next_roadmap_work_order_manifest_v1"
CODEX_QUEUE_SCHEMA_VERSION = "source_adapter_next_roadmap_codex_prompt_queue_v1"
REGRESSION_COMMAND_SCHEMA_VERSION = "source_adapter_next_roadmap_regression_command_manifest_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_next_roadmap_ready_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_next_roadmap_section_selection_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_NEXT_ROADMAP_SECTION_SELECTION_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_NEXT_ROADMAP_SECTION_WORK_ORDERS_READY"
BLOCKED_STATUS = "SOURCE_ADAPTER_NEXT_ROADMAP_SECTION_SELECTION_BLOCKED"

DEFAULT_SECTION_DEFINITIONS = [
    {
        "section_id": "runtime_gui_controller_hardening",
        "display_name": "Runtime GUI/controller hardening",
        "selection_reason": "Connect accepted runtime routes and provider bindings into stable controller/UI surfaces.",
        "implementation_scope": [
            "surface runtime action route IDs in controller-facing manifests",
            "map shared provider execution adapters onto GUI-selectable actions",
            "preserve KEYS/ACCOUNTS credential-reference selection without exposing secret values",
            "add regression coverage for route-manifest roundtrips",
        ],
        "command_group": "runtime_gui_controller_hardening_regression",
        "operator_gate": "local_regression_only_until_named_live_smoke_approval",
    },
    {
        "section_id": "provider_execution_adapter_activation",
        "display_name": "Provider execution adapter activation",
        "selection_reason": "Prepare archive/upload/library/provider execution rows for operator-approved receipts.",
        "implementation_scope": [
            "install provider adapter registry rows for archive submit and library publication",
            "model dry-run and operator-approved execution modes from the same contract",
            "require provider receipts for live rows before release acceptance",
            "carry redacted credential-reference hashes into receipt records",
        ],
        "command_group": "provider_execution_adapter_activation_regression",
        "operator_gate": "operator_approval_required_for_live_provider_execution",
    },
    {
        "section_id": "priority_site_fixture_pack_authoring",
        "display_name": "Priority site fixture pack authoring",
        "selection_reason": "Turn article, social, comments, media/transcript, and archive-receipt families into named local fixture packs.",
        "implementation_scope": [
            "author named fixture pack manifests for each priority source family",
            "bind fixture artifacts to the shared artifact/extraction/capture/total-export/release pipeline",
            "emit fixture execution receipts for local regression promotion",
            "track adapter-specific code only where shared mappings cannot express the surface",
        ],
        "command_group": "priority_site_fixture_pack_regression",
        "operator_gate": "local_fixture_data_only_by_default",
    },
    {
        "section_id": "operator_live_smoke_receipt_capture",
        "display_name": "Operator-approved live smoke receipt capture",
        "selection_reason": "Use named site/operator approvals to capture real provider receipts without automatic live actions.",
        "implementation_scope": [
            "build named live smoke rows from accepted runbook entries",
            "require explicit operator inputs and approval IDs for each live execution row",
            "preserve archive provider receipts and KEYS/ACCOUNTS lookup receipts",
            "keep local tests on deterministic fixture receipts",
        ],
        "command_group": "operator_live_smoke_receipt_capture_regression",
        "operator_gate": "explicit_named_site_and_action_approval_required",
    },
    {
        "section_id": "regular_regression_promotion",
        "display_name": "Regular regression promotion",
        "selection_reason": "Promote accepted source-adapter rows into regular regression command groups.",
        "implementation_scope": [
            "convert accepted fixture rows into recurring regression queue entries",
            "preserve py_compile coverage for ASR test files without executing asr_tools_test.py",
            "include session, manifest, main export state, and runtime bridge regression tails",
            "record command groups in a release-readable manifest",
        ],
        "command_group": "regular_source_adapter_regression_tail",
        "operator_gate": "safe_local_regression",
    },
    {
        "section_id": "documentation_handoff_refresh",
        "display_name": "Documentation and handoff refresh",
        "selection_reason": "Keep roadmap, audit, handoff, and operator instructions aligned with the closed source-adapter section.",
        "implementation_scope": [
            "summarise closed shared adapter stages and next action rows",
            "preserve sidebar label KEYS/ACCOUNTS in operator-facing docs",
            "document runtime receipt expectations and live smoke approval flows",
            "write a compact handoff for the next session and Codex mega-prompt workflow",
        ],
        "command_group": "documentation_handoff_refresh_regression",
        "operator_gate": "documentation_only",
    },
]

DEFAULT_NEXT_ACTIONS = [
    "Implement the selected next-roadmap work orders in the listed order unless a dependency forces a split.",
    "Keep local regression and fixture paths deterministic; reserve live actions for named operator-approved rows.",
    "Promote accepted regression command rows into the regular test tail after the fixture packs are authored.",
    "Preserve KEYS/ACCOUNTS credential references and redacted hashes in every provider or smoke receipt.",
]


@dataclass(frozen=True)
class SourceAdapterNextRoadmapSectionSelectionCloseout:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def short_hash(value: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def as_list(value: Any, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{label} must be a list")
    return list(value)


def _strings(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in output:
            output.append(text)
    return output


def _validate_input(release_regression_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if release_regression_closeout.get("schema_version") != "source_adapter_release_regression_next_roadmap_closeout_v1":
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "release regression next roadmap closeout schema was not recognised"})
    if release_regression_closeout.get("release_regression_next_roadmap_closeout_status") != RELEASE_NEXT_STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "release regression next roadmap closeout is not built"})
    handoff = release_regression_closeout.get("source_adapter_next_roadmap_handoff") or {}
    if handoff.get("handoff_status") != RELEASE_NEXT_HANDOFF_STATUS:
        issues.append({"issue_id": "next_roadmap_handoff_not_ready", "severity": "error", "message": "release regression next roadmap handoff is not ready"})
    for flag in (
        "ready_for_release_notes_publication",
        "ready_for_regular_regression_queue_integration",
        "ready_for_operator_monitored_live_execution",
        "ready_for_next_source_evidence_roadmap_section",
    ):
        if handoff.get(flag) is not True:
            issues.append({"issue_id": f"{flag}_not_ready", "severity": "error", "message": f"handoff flag {flag} is not ready"})
    return issues


def _selected_definitions(selected_sections: Sequence[str] | None) -> list[dict[str, Any]]:
    requested = _strings(selected_sections or [])
    if not requested:
        return [dict(row) for row in DEFAULT_SECTION_DEFINITIONS]
    available = {row["section_id"]: row for row in DEFAULT_SECTION_DEFINITIONS}
    selected: list[dict[str, Any]] = []
    for section_id in requested:
        if section_id not in available:
            raise ValueError(f"unknown next roadmap section: {section_id}")
        selected.append(dict(available[section_id]))
    return selected


def _build_section_selection_index(
    release_regression_closeout: Mapping[str, Any],
    selected_sections: Sequence[str] | None,
    issues: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    definitions = _selected_definitions(selected_sections)
    release_handoff = release_regression_closeout.get("source_adapter_next_roadmap_handoff") or {}
    rows: list[dict[str, Any]] = []
    for index, definition in enumerate(definitions):
        seed = {"section_id": definition["section_id"], "index": index, "release_handoff": release_handoff.get("handoff_status")}
        rows.append(
            {
                "schema_version": "source_adapter_next_roadmap_section_selection_row_v1",
                "row_index": index,
                "selection_row_id": stable_id("source_adapter.next_roadmap_section_selection", seed),
                "section_id": definition["section_id"],
                "display_name": definition["display_name"],
                "selection_reason": definition["selection_reason"],
                "implementation_scope": list(definition["implementation_scope"]),
                "command_group": definition["command_group"],
                "operator_gate": definition["operator_gate"],
                "selection_status": "SELECTED_FOR_NEXT_ROADMAP_WORK_ORDER" if not issues else "BLOCKED_BY_RELEASE_HANDOFF_REVIEW",
            }
        )
    selected_count = sum(1 for row in rows if row["selection_status"] == "SELECTED_FOR_NEXT_ROADMAP_WORK_ORDER")
    return {
        "schema_version": SECTION_INDEX_SCHEMA_VERSION,
        "section_selection_status": "SOURCE_ADAPTER_NEXT_ROADMAP_SECTIONS_SELECTED" if rows and selected_count == len(rows) else "SOURCE_ADAPTER_NEXT_ROADMAP_SECTION_SELECTION_NEEDS_REVIEW",
        "selected_section_count": selected_count,
        "section_count": len(rows),
        "source_adapter_release_regression_next_roadmap_closeout_id": release_regression_closeout.get("source_adapter_release_regression_next_roadmap_closeout_id"),
        "selection_rows": rows,
    }


def _build_work_order_manifest(section_index: Mapping[str, Any], operator_id: str, issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in as_list(section_index.get("selection_rows"), "selection_rows") if isinstance(row, Mapping)]
    work_orders: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        ready = row.get("selection_status") == "SELECTED_FOR_NEXT_ROADMAP_WORK_ORDER" and not issues
        seed = {"selection_row_id": row.get("selection_row_id"), "operator_id": operator_id, "index": index}
        work_orders.append(
            {
                "schema_version": "source_adapter_next_roadmap_work_order_row_v1",
                "row_index": index,
                "work_order_row_id": stable_id("source_adapter.next_roadmap_work_order", seed),
                "selection_row_id": row.get("selection_row_id"),
                "section_id": row.get("section_id"),
                "display_name": row.get("display_name"),
                "implementation_scope": list(row.get("implementation_scope") or []),
                "command_group": row.get("command_group"),
                "operator_gate": row.get("operator_gate"),
                "required_patch_mode": "largest_stable_mega_patch",
                "codex_prompt_mode": "single_section_mega_prompt_or_combined_when_safe",
                "work_order_status": "READY_FOR_IMPLEMENTATION" if ready else "NEEDS_HANDOFF_REVIEW",
            }
        )
    ready_count = sum(1 for row in work_orders if row["work_order_status"] == "READY_FOR_IMPLEMENTATION")
    return {
        "schema_version": WORK_ORDER_SCHEMA_VERSION,
        "work_order_manifest_status": "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDERS_READY" if work_orders and ready_count == len(work_orders) else "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDERS_NEED_REVIEW",
        "work_order_count": len(work_orders),
        "ready_work_order_count": ready_count,
        "operator_id": str(operator_id),
        "work_order_rows": work_orders,
    }


def _build_codex_prompt_queue(work_order_manifest: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in as_list(work_order_manifest.get("work_order_rows"), "work_order_rows") if isinstance(row, Mapping)]
    prompt_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        ready = row.get("work_order_status") == "READY_FOR_IMPLEMENTATION" and not issues
        scope = [str(item) for item in row.get("implementation_scope") or []]
        prompt_rows.append(
            {
                "schema_version": "source_adapter_next_roadmap_codex_prompt_queue_row_v1",
                "row_index": index,
                "codex_prompt_queue_row_id": stable_id("source_adapter.codex_prompt_queue", {"work_order": row.get("work_order_row_id"), "index": index}),
                "work_order_row_id": row.get("work_order_row_id"),
                "section_id": row.get("section_id"),
                "prompt_title": f"Implement {row.get('display_name')} as a largest-stable patch",
                "prompt_scope": scope,
                "prompt_constraints": [
                    "use exact Windows commands with Python 3.11 path",
                    "compile asr_tools_test.py but do not execute it",
                    "keep live/provider actions behind explicit operator approval rows",
                    "use git diff --check before commit",
                ],
                "prompt_status": "READY_FOR_CODEX_MEGA_PROMPT" if ready else "NEEDS_WORK_ORDER_REVIEW",
            }
        )
    ready_count = sum(1 for row in prompt_rows if row["prompt_status"] == "READY_FOR_CODEX_MEGA_PROMPT")
    return {
        "schema_version": CODEX_QUEUE_SCHEMA_VERSION,
        "codex_prompt_queue_status": "SOURCE_ADAPTER_CODEX_PROMPT_QUEUE_READY" if prompt_rows and ready_count == len(prompt_rows) else "SOURCE_ADAPTER_CODEX_PROMPT_QUEUE_NEEDS_REVIEW",
        "prompt_row_count": len(prompt_rows),
        "ready_prompt_row_count": ready_count,
        "prompt_rows": prompt_rows,
    }


def _build_regression_command_manifest(work_order_manifest: Mapping[str, Any], release_regression_closeout: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    work_orders = [dict(row) for row in as_list(work_order_manifest.get("work_order_rows"), "work_order_rows") if isinstance(row, Mapping)]
    release_queue = release_regression_closeout.get("source_adapter_regular_regression_promotion_queue") or {}
    release_queue_rows = as_list(release_queue.get("queue_rows"), "queue_rows")
    command_rows: list[dict[str, Any]] = []
    for index, row in enumerate(work_orders):
        command_rows.append(
            {
                "schema_version": "source_adapter_next_roadmap_regression_command_row_v1",
                "row_index": index,
                "regression_command_row_id": stable_id("source_adapter.next_roadmap_regression_command", {"section": row.get("section_id"), "index": index}),
                "section_id": row.get("section_id"),
                "command_group": row.get("command_group"),
                "includes_release_queue_rows": bool(release_queue_rows),
                "safe_execution_mode": "local_fixture_or_dry_run_regression",
                "status": "READY_FOR_REGRESSION_COMMAND_AUTHORING" if not issues else "NEEDS_HANDOFF_REVIEW",
            }
        )
    return {
        "schema_version": REGRESSION_COMMAND_SCHEMA_VERSION,
        "regression_command_manifest_status": "SOURCE_ADAPTER_NEXT_ROADMAP_REGRESSION_COMMANDS_READY" if command_rows and not issues else "SOURCE_ADAPTER_NEXT_ROADMAP_REGRESSION_COMMANDS_NEED_REVIEW",
        "command_row_count": len(command_rows),
        "release_regression_queue_row_count": len(release_queue_rows),
        "command_rows": command_rows,
    }


def _build_ready_handoff(closeout_id: str, section_index: Mapping[str, Any], work_orders: Mapping[str, Any], prompt_queue: Mapping[str, Any], regression_manifest: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = (
        not issues
        and section_index.get("section_selection_status") == "SOURCE_ADAPTER_NEXT_ROADMAP_SECTIONS_SELECTED"
        and work_orders.get("work_order_manifest_status") == "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDERS_READY"
        and prompt_queue.get("codex_prompt_queue_status") == "SOURCE_ADAPTER_CODEX_PROMPT_QUEUE_READY"
        and regression_manifest.get("regression_command_manifest_status") == "SOURCE_ADAPTER_NEXT_ROADMAP_REGRESSION_COMMANDS_READY"
    )
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_next_roadmap_section_selection_closeout_id": closeout_id,
        "ready_for_next_largest_stable_patch": ready,
        "ready_for_codex_mega_prompt_queue": ready,
        "ready_for_regression_command_authoring": ready,
        "ready_for_operator_gated_live_rows_when_selected": ready,
        "required_next_stage": "selected_next_roadmap_work_order_implementation" if ready else "next_roadmap_selection_review",
        "selected_section_count": section_index.get("selected_section_count", 0),
        "work_order_count": work_orders.get("work_order_count", 0),
        "prompt_row_count": prompt_queue.get("prompt_row_count", 0),
        "regression_command_row_count": regression_manifest.get("command_row_count", 0),
    }


def build_source_adapter_next_roadmap_section_selection_closeout(
    release_regression_next_roadmap_closeout_package: Mapping[str, Any],
    *,
    selected_sections: Sequence[str] | None = None,
    operator_id: str = "operator",
    closeout_notes: Sequence[str] | None = None,
) -> SourceAdapterNextRoadmapSectionSelectionCloseout:
    release_closeout = as_mapping(release_regression_next_roadmap_closeout_package, "release_regression_next_roadmap_closeout_package")
    issues = _validate_input(release_closeout)
    section_index = _build_section_selection_index(release_closeout, selected_sections, issues)
    work_orders = _build_work_order_manifest(section_index, operator_id, issues)
    prompt_queue = _build_codex_prompt_queue(work_orders, issues)
    regression_manifest = _build_regression_command_manifest(work_orders, release_closeout, issues)
    seed = {
        "release_closeout_id": release_closeout.get("source_adapter_release_regression_next_roadmap_closeout_id"),
        "operator_id": operator_id,
        "section_count": section_index.get("section_count"),
        "work_order_count": work_orders.get("work_order_count"),
    }
    closeout_id = stable_id("source_adapter.next_roadmap_section_selection_closeout", seed)
    handoff = _build_ready_handoff(closeout_id, section_index, work_orders, prompt_queue, regression_manifest, issues)
    ready = handoff.get("handoff_status") == HANDOFF_STATUS
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "selected_section_count": section_index.get("selected_section_count", 0),
        "work_order_count": work_orders.get("work_order_count", 0),
        "prompt_row_count": prompt_queue.get("prompt_row_count", 0),
        "regression_command_row_count": regression_manifest.get("command_row_count", 0),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "next_actions": list(DEFAULT_NEXT_ACTIONS),
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "next_roadmap_section_selection_closeout_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_next_roadmap_section_selection_closeout_id": closeout_id,
        "source_adapter_release_regression_next_roadmap_closeout_id": release_closeout.get("source_adapter_release_regression_next_roadmap_closeout_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": issues,
        "closeout_notes": _strings(closeout_notes or []),
        "implementation_logic": {
            "input_source": "source_adapter_release_regression_next_roadmap_closeout",
            "section_selection_index_built": True,
            "work_order_manifest_built": True,
            "codex_prompt_queue_built": True,
            "regression_command_manifest_built": True,
            "next_roadmap_ready_handoff_built": True,
            "largest_stable_patch_mode_preserved": True,
            "keys_accounts_label_preserved": True,
        },
        "source_adapter_next_roadmap_section_selection_index": section_index,
        "source_adapter_next_roadmap_work_order_manifest": work_orders,
        "source_adapter_next_roadmap_codex_prompt_queue": prompt_queue,
        "source_adapter_next_roadmap_regression_command_manifest": regression_manifest,
        "source_adapter_next_roadmap_ready_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterNextRoadmapSectionSelectionCloseout(package)


def example_next_roadmap_section_selection_closeout_package() -> dict[str, Any]:
    return build_source_adapter_next_roadmap_section_selection_closeout(
        example_release_regression_next_roadmap_closeout_package(),
        operator_id="example_operator",
    ).as_dict()


def main() -> None:
    package = example_next_roadmap_section_selection_closeout_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["next_roadmap_section_selection_closeout_status"] == STATUS
    assert package["source_adapter_next_roadmap_ready_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    assert package["source_adapter_next_roadmap_work_order_manifest"]["ready_work_order_count"] >= 1
    print("Source Adapter Next Roadmap Section Selection Closeout self-test passed.")


if __name__ == "__main__":
    main()
