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

from source_adapter_browser_capture_execution_backend import example_browser_capture_execution_backend_package
from source_adapter_archive_provider_submission_backend import example_archive_provider_submission_backend_package
from source_adapter_release_file_delivery_backend import example_release_file_delivery_backend_package
from source_adapter_keys_accounts_credential_reference_runtime import HANDOFF_STATUS as CREDENTIAL_HANDOFF_STATUS, example_keys_accounts_credential_reference_runtime_package

SCHEMA_VERSION = "source_adapter_end_to_end_operator_execution_orchestrator_v1"
STATUS = "SOURCE_ADAPTER_END_TO_END_OPERATOR_EXECUTION_ORCHESTRATOR_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_END_TO_END_OPERATOR_EXECUTION_READY_FOR_GUI_LIVE_PANEL_WIRING"

@dataclass(frozen=True)
class SourceAdapterEndToEndOperatorExecutionOrchestrator:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def _receipt_rows(browser: Mapping[str, Any], archive: Mapping[str, Any], delivery: Mapping[str, Any], credentials: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    by_site = {str(row.get("named_site_id")): row for row in _rows(credentials, "credential_reference_rows")}
    grouped_delivery: dict[str, list[dict[str, Any]]] = {}
    for row in _rows(delivery, "release_file_delivery_rows"):
        grouped_delivery.setdefault(str(row.get("named_site_id")), []).append(row)
    for capture in _rows(browser, "browser_capture_rows"):
        site_id = str(capture.get("named_site_id"))
        archive_row = next((row for row in _rows(archive, "archive_provider_submission_rows") if str(row.get("named_site_id")) == site_id), {})
        credential_row = by_site.get(site_id, {})
        payload = {"site_id": site_id, "capture": capture.get("browser_capture_execution_row_id"), "archive": archive_row.get("archive_provider_submission_row_id")}
        rows.append({
            "schema_version": "source_adapter_end_to_end_operator_execution_receipt_row_v1",
            "row_index": len(rows),
            "end_to_end_operator_execution_receipt_row_id": stable_id("source_adapter.end_to_end_operator_execution_receipt", payload),
            "named_site_id": site_id,
            "adapter_id": capture.get("adapter_id"),
            "source_kind": capture.get("source_kind"),
            "browser_capture_receipt_id": capture.get("browser_capture_execution_row_id"),
            "archive_submission_receipt_id": archive_row.get("archive_provider_submission_row_id"),
            "delivery_receipt_count": len(grouped_delivery.get(site_id, [])),
            "credential_reference_runtime_row_id": credential_row.get("credential_reference_runtime_row_id"),
            "redacted_reference_hash": credential_row.get("redacted_reference_hash"),
            "provider_action_count": 5,
            "end_to_end_execution_status": "SOURCE_ADAPTER_OPERATOR_APPROVED_E2E_EXECUTION_RECEIPT_RECORDED",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return rows


def build_source_adapter_end_to_end_operator_execution_orchestrator() -> dict[str, Any]:
    browser = example_browser_capture_execution_backend_package()
    archive = example_archive_provider_submission_backend_package()
    delivery = example_release_file_delivery_backend_package()
    credentials = example_keys_accounts_credential_reference_runtime_package()
    issues = []
    if credentials.get("handoff", {}).get("handoff_status") != CREDENTIAL_HANDOFF_STATUS:
        issues.append({"issue_id": "credential_runtime_not_ready", "severity": "error"})
    rows = _receipt_rows(browser, archive, delivery, credentials)
    handoff = {"schema_version": "source_adapter_end_to_end_operator_execution_handoff_v1", "handoff_status": HANDOFF_STATUS, "end_to_end_receipt_row_count": len(rows), "provider_action_receipt_count": len(rows) * 5, "delivery_receipt_count": sum(r["delivery_receipt_count"] for r in rows), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}
    package_id = stable_id("source_adapter.end_to_end_operator_execution_orchestrator", rows)
    return {"schema_version": SCHEMA_VERSION, "id": package_id, "status": STATUS, "end_to_end_receipt_row_count": len(rows), "provider_action_receipt_count": handoff["provider_action_receipt_count"], "delivery_receipt_count": handoff["delivery_receipt_count"], "end_to_end_execution_receipt_rows": rows, "source_packages": {"browser_capture": browser["id"], "archive_submission": archive["id"], "release_file_delivery": delivery["id"], "credential_reference": credentials["id"]}, "handoff": handoff, "operator_summary": {"schema_version": "source_adapter_end_to_end_operator_execution_operator_summary_v1", "status": STATUS, "end_to_end_receipt_row_count": len(rows), "provider_action_receipt_count": handoff["provider_action_receipt_count"], "keys_accounts_label": KEYS_ACCOUNTS_LABEL}, "issue_count": len(issues), "issues": issues}


def example_end_to_end_operator_execution_orchestrator_package() -> dict[str, Any]:
    return build_source_adapter_end_to_end_operator_execution_orchestrator()
