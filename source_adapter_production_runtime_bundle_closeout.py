from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

KEYS_ACCOUNTS_LABEL = "KEYS/ACCOUNTS"
SOURCE_KINDS = ("web_article", "social_media", "comments", "media_or_transcript", "archive_provider")
PROVIDER_ACTIONS = ("credential_lookup", "browser_capture", "archive_submit", "release_upload", "file_library_publish")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{sha256_text(value)[:12]}"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _named_sites() -> list[dict[str, Any]]:
    return [
        {"row_index": 0, "named_site_id": "operator_named_site.article_0", "adapter_id": "article", "source_kind": "web_article", "fixture_family": "article_news_page", "capture_profile": "browser_html_screenshot_archive", "source_url": "https://example.invalid/article/0"},
        {"row_index": 1, "named_site_id": "operator_named_site.social_post_1", "adapter_id": "social_post", "source_kind": "social_media", "fixture_family": "social_post_thread", "capture_profile": "thread_html_json_screenshot_archive", "source_url": "https://example.invalid/social/1"},
        {"row_index": 2, "named_site_id": "operator_named_site.comments_thread_2", "adapter_id": "comments_thread", "source_kind": "comments", "fixture_family": "comments_replies_thread", "capture_profile": "comments_dom_json_screenshot_archive", "source_url": "https://example.invalid/comments/2"},
        {"row_index": 3, "named_site_id": "operator_named_site.media_transcript_3", "adapter_id": "media_transcript", "source_kind": "media_or_transcript", "fixture_family": "media_transcript_asr_source", "capture_profile": "media_metadata_transcript_source_archive", "source_url": "https://example.invalid/media/3"},
        {"row_index": 4, "named_site_id": "operator_named_site.archive_receipt_4", "adapter_id": "archive_receipt", "source_kind": "archive_provider", "fixture_family": "archive_provider_receipt", "capture_profile": "archive_receipt_review_delivery", "source_url": "https://example.invalid/archive/4"},
    ]


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return {"path": str(path), "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}

from source_adapter_provider_secret_boundary_runtime import example_source_adapter_provider_secret_boundary_runtime_package
from source_adapter_live_run_permission_runtime import example_source_adapter_live_run_permission_runtime_package
from source_adapter_operator_session_execution_runtime import example_source_adapter_operator_session_execution_runtime_package
from source_adapter_provider_receipt_persistence_runtime import example_source_adapter_provider_receipt_persistence_runtime_package
from source_adapter_evidence_database_writeback_runtime import example_source_adapter_evidence_database_writeback_runtime_package
from source_adapter_total_export_handoff_commit_runtime import example_source_adapter_total_export_handoff_commit_runtime_package
from source_adapter_release_reconciliation_runtime import example_source_adapter_release_reconciliation_runtime_package
from source_adapter_operator_signoff_runtime import example_source_adapter_operator_signoff_runtime_package
from source_adapter_gui_completion_state_runtime import example_source_adapter_gui_completion_state_runtime_package
from source_adapter_release_lock_runtime import example_source_adapter_release_lock_runtime_package
from source_adapter_archive_closeout_runtime import example_source_adapter_archive_closeout_runtime_package

SCHEMA_VERSION = "source_adapter_production_runtime_bundle_closeout_v1"
STATUS = "SOURCE_ADAPTER_PRODUCTION_RUNTIME_BUNDLE_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_PRODUCTION_RUNTIME_BUNDLE_READY_FOR_GUI_AND_PROVIDER_BACKEND_SMOKE"


def build_source_adapter_production_runtime_bundle_closeout() -> dict[str, Any]:
    packages={
        "provider_secret_boundary_runtime": example_source_adapter_provider_secret_boundary_runtime_package(),
        "live_run_permission_runtime": example_source_adapter_live_run_permission_runtime_package(),
        "operator_session_execution_runtime": example_source_adapter_operator_session_execution_runtime_package(),
        "provider_receipt_persistence_runtime": example_source_adapter_provider_receipt_persistence_runtime_package(),
        "evidence_database_writeback_runtime": example_source_adapter_evidence_database_writeback_runtime_package(),
        "total_export_handoff_commit_runtime": example_source_adapter_total_export_handoff_commit_runtime_package(),
        "release_reconciliation_runtime": example_source_adapter_release_reconciliation_runtime_package(),
        "operator_signoff_runtime": example_source_adapter_operator_signoff_runtime_package(),
        "gui_completion_state_runtime": example_source_adapter_gui_completion_state_runtime_package(),
        "release_lock_runtime": example_source_adapter_release_lock_runtime_package(),
        "archive_closeout_runtime": example_source_adapter_archive_closeout_runtime_package(),
    }
    issue_count=sum(int(pkg.get("issue_count",0)) for pkg in packages.values())
    handoff={"schema_version":"source_adapter_production_runtime_bundle_handoff_v1","handoff_status":HANDOFF_STATUS,"implemented_package_count":len(packages),"operator_session_execution_row_count":packages["operator_session_execution_runtime"]["operator_session_execution_row_count"],"provider_receipt_persistence_row_count":packages["provider_receipt_persistence_runtime"]["provider_receipt_persistence_row_count"],"evidence_database_writeback_row_count":packages["evidence_database_writeback_runtime"]["evidence_database_writeback_row_count"],"archive_closeout_row_count":packages["archive_closeout_runtime"]["archive_closeout_row_count"],"keys_accounts_label":KEYS_ACCOUNTS_LABEL,"required_next_stage":"gui_backend_smoke_and_provider_specific_hardening"}
    return {"schema_version":SCHEMA_VERSION,"id":stable_id("source_adapter.production_runtime_bundle_closeout",handoff),"status":STATUS,"implemented_package_count":len(packages),"package_statuses":{k:v["status"] for k,v in packages.items()},"handoff":handoff,"operator_summary":{"schema_version":"source_adapter_production_runtime_bundle_operator_summary_v1","status":STATUS,"implemented_package_count":len(packages),"next_actions":["wire GUI button/action handlers directly to the operator session execution runtime","run provider-specific backends against selected named-site smoke inputs","use persisted provider receipts for evidence database writeback and Total Export handoff commit"],"keys_accounts_label":KEYS_ACCOUNTS_LABEL},"issue_count":issue_count,"issues":[]}


def example_source_adapter_production_runtime_bundle_closeout_package() -> dict[str, Any]:
    return build_source_adapter_production_runtime_bundle_closeout()
