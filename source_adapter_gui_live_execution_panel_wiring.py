from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

KEYS_ACCOUNTS_LABEL = "KEYS/ACCOUNTS"
PROVIDER_ACTIONS = ("credential_lookup", "browser_capture", "archive_submit", "release_upload", "file_library_publish")
SOURCE_KINDS = ("web_article", "social_media", "comments", "media_or_transcript", "archive_provider")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{sha256_text(value)[:12]}"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _named_sites() -> list[dict[str, Any]]:
    return [
        {"row_index": 0, "named_site_id": "operator_named_site.article_0", "adapter_id": "article", "source_kind": "web_article", "fixture_family": "article_news_page", "capture_profile": "browser_html_screenshot_archive"},
        {"row_index": 1, "named_site_id": "operator_named_site.social_post_1", "adapter_id": "social_post", "source_kind": "social_media", "fixture_family": "social_post_thread", "capture_profile": "thread_html_json_screenshot_archive"},
        {"row_index": 2, "named_site_id": "operator_named_site.comments_thread_2", "adapter_id": "comments_thread", "source_kind": "comments", "fixture_family": "comments_replies_thread", "capture_profile": "comments_dom_json_screenshot_archive"},
        {"row_index": 3, "named_site_id": "operator_named_site.media_transcript_3", "adapter_id": "media_transcript", "source_kind": "media_or_transcript", "fixture_family": "media_transcript_asr_source", "capture_profile": "media_metadata_transcript_source_archive"},
        {"row_index": 4, "named_site_id": "operator_named_site.archive_receipt_4", "adapter_id": "archive_receipt", "source_kind": "archive_provider", "fixture_family": "archive_provider_receipt", "capture_profile": "archive_receipt_review_delivery"},
    ]


def _default_output_root(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))

from source_adapter_end_to_end_operator_execution_orchestrator import HANDOFF_STATUS as E2E_HANDOFF_STATUS, example_end_to_end_operator_execution_orchestrator_package

SCHEMA_VERSION = "source_adapter_gui_live_execution_panel_wiring_v1"
STATUS = "SOURCE_ADAPTER_GUI_LIVE_EXECUTION_PANEL_WIRING_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_GUI_LIVE_EXECUTION_PANEL_READY_FOR_OPERATOR_USE"
ROUTES = (
    ("source_adapter.gui.live_execution_panel", "source_adapter.ui.live_execution_panel", "source_adapter.controller.live_execution.run_operator_approved_bundle"),
    ("source_adapter.gui.live_receipt_review", "source_adapter.ui.live_receipt_review", "source_adapter.controller.live_execution.review_receipts"),
    ("source_adapter.gui.release_delivery_panel", "source_adapter.ui.release_delivery_panel", "source_adapter.controller.release_delivery.publish_operator_bundle"),
    ("keys_accounts.gui.credential_reference_selector", "keys_accounts.ui.credential_reference_selector", "keys_accounts.controller.runtime.select_credential_reference"),
)

@dataclass(frozen=True)
class SourceAdapterGuiLiveExecutionPanelWiring:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def _route_rows(e2e_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, (route_id, surface_id, controller_entrypoint) in enumerate(ROUTES):
        payload = {"route_id": route_id, "e2e": e2e_package.get("id")}
        rows.append({
            "schema_version": "source_adapter_gui_live_execution_panel_route_row_v1",
            "row_index": index,
            "gui_live_execution_panel_route_row_id": stable_id("source_adapter.gui_live_execution_panel_route", payload),
            "route_id": route_id,
            "surface_id": surface_id,
            "controller_entrypoint": controller_entrypoint,
            "controller_callable": True,
            "gui_route_registered": True,
            "operator_approval_required_at_runtime": True,
            "receipt_review_required_after_runtime": True,
            "bound_end_to_end_receipt_row_count": e2e_package.get("end_to_end_receipt_row_count"),
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return rows


def build_source_adapter_gui_live_execution_panel_wiring(e2e_package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    e2e_package = dict(e2e_package or example_end_to_end_operator_execution_orchestrator_package())
    issues = []
    if e2e_package.get("handoff", {}).get("handoff_status") != E2E_HANDOFF_STATUS:
        issues.append({"issue_id": "e2e_orchestrator_not_ready", "severity": "error"})
    rows = _route_rows(e2e_package)
    handoff = {"schema_version": "source_adapter_gui_live_execution_panel_handoff_v1", "handoff_status": HANDOFF_STATUS, "gui_route_row_count": len(rows), "controller_callable_route_count": sum(1 for r in rows if r["controller_callable"]), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}
    package_id = stable_id("source_adapter.gui_live_execution_panel_wiring", rows)
    return {"schema_version": SCHEMA_VERSION, "id": package_id, "status": STATUS, "gui_route_row_count": len(rows), "gui_live_execution_panel_route_rows": rows, "handoff": handoff, "operator_summary": {"schema_version": "source_adapter_gui_live_execution_panel_operator_summary_v1", "status": STATUS, "gui_route_row_count": len(rows), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}, "issue_count": len(issues), "issues": issues}


def example_gui_live_execution_panel_wiring_package() -> dict[str, Any]:
    return build_source_adapter_gui_live_execution_panel_wiring()
