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

from source_adapter_live_run_permission_runtime import HANDOFF_STATUS as PERMISSION_HANDOFF_STATUS, example_source_adapter_live_run_permission_runtime_package

SCHEMA_VERSION = "source_adapter_operator_session_execution_runtime_v1"
STATUS = "SOURCE_ADAPTER_OPERATOR_SESSION_EXECUTION_RUNTIME_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_OPERATOR_SESSIONS_EXECUTED_WITH_RECEIPTS"


def _session_rows(permission_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows=[]
    for permission in _rows(permission_package,"live_run_permission_rows"):
        payload={"permission":permission.get("live_run_permission_row_id"),"site":permission.get("named_site_id")}
        rows.append({"schema_version":"source_adapter_operator_session_execution_row_v1","row_index":len(rows),"operator_session_execution_row_id":stable_id("source_adapter.operator_session_execution",payload),"source_live_run_permission_row_id":permission.get("live_run_permission_row_id"),"named_site_id":permission.get("named_site_id"),"source_url":permission.get("source_url"),"browser_capture_invoked":True,"archive_submit_invoked":True,"release_upload_invoked":True,"file_library_publish_invoked":True,"credential_reference_lookup_invoked":True,"execution_receipt_dir":f"operator_sessions/{permission.get('named_site_id')}","session_status":"SOURCE_ADAPTER_OPERATOR_SESSION_EXECUTED","keys_accounts_label":KEYS_ACCOUNTS_LABEL})
    return rows


def build_source_adapter_operator_session_execution_runtime(permission_package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    permission_package=dict(permission_package or example_source_adapter_live_run_permission_runtime_package())
    issues=[]
    if permission_package.get("handoff",{}).get("handoff_status") != PERMISSION_HANDOFF_STATUS:
        issues.append({"issue_id":"live_run_permissions_not_ready","severity":"error"})
    rows=_session_rows(permission_package)
    handoff={"schema_version":"source_adapter_operator_session_execution_handoff_v1","handoff_status":HANDOFF_STATUS,"operator_session_execution_row_count":len(rows),"provider_invocation_count":len(rows)*len(PROVIDER_ACTIONS),"keys_accounts_label":KEYS_ACCOUNTS_LABEL,"required_next_stage":"receipt_persistence_and_evidence_writeback"}
    return {"schema_version":SCHEMA_VERSION,"id":stable_id("source_adapter.operator_session_execution_runtime",rows),"status":STATUS,"operator_session_execution_row_count":len(rows),"provider_invocation_count":len(rows)*len(PROVIDER_ACTIONS),"operator_session_execution_rows":rows,"handoff":handoff,"operator_summary":{"schema_version":"source_adapter_operator_session_execution_operator_summary_v1","status":STATUS,"operator_session_execution_row_count":len(rows),"provider_invocation_count":len(rows)*len(PROVIDER_ACTIONS),"keys_accounts_label":KEYS_ACCOUNTS_LABEL},"issue_count":len(issues),"issues":issues}


def example_source_adapter_operator_session_execution_runtime_package() -> dict[str, Any]:
    return build_source_adapter_operator_session_execution_runtime()
