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

from source_adapter_provider_receipt_persistence_runtime import HANDOFF_STATUS as RECEIPT_HANDOFF_STATUS, example_source_adapter_provider_receipt_persistence_runtime_package

SCHEMA_VERSION = "source_adapter_evidence_database_writeback_runtime_v1"
STATUS = "SOURCE_ADAPTER_EVIDENCE_DATABASE_WRITEBACK_RUNTIME_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_EVIDENCE_DATABASE_WRITEBACK_READY_FOR_TOTAL_EXPORT_HANDOFF"


def _writeback_rows(receipt_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_site: dict[str, list[dict[str, Any]]] = {}
    for receipt in _rows(receipt_package,"provider_receipt_persistence_rows"):
        by_site.setdefault(str(receipt.get("named_site_id")), []).append(receipt)
    rows=[]
    for site, receipts in sorted(by_site.items()):
        payload={"site":site,"receipt_ids":[r.get("provider_receipt_persistence_row_id") for r in receipts]}
        rows.append({"schema_version":"source_adapter_evidence_database_writeback_row_v1","row_index":len(rows),"evidence_database_writeback_row_id":stable_id("source_adapter.evidence_database_writeback",payload),"named_site_id":site,"provider_receipt_count":len(receipts),"evidence_item_id":stable_id("source.evidence_item",payload),"evidence_database_mutation_prepared":True,"evidence_database_mutation_receipt_required":True,"writeback_status":"READY_FOR_EVIDENCE_DATABASE_COMMIT","keys_accounts_label":KEYS_ACCOUNTS_LABEL})
    return rows


def build_source_adapter_evidence_database_writeback_runtime(receipt_package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    receipt_package=dict(receipt_package or example_source_adapter_provider_receipt_persistence_runtime_package())
    issues=[]
    if receipt_package.get("handoff",{}).get("handoff_status") != RECEIPT_HANDOFF_STATUS:
        issues.append({"issue_id":"provider_receipts_not_ready","severity":"error"})
    rows=_writeback_rows(receipt_package)
    handoff={"schema_version":"source_adapter_evidence_database_writeback_handoff_v1","handoff_status":HANDOFF_STATUS,"evidence_database_writeback_row_count":len(rows),"keys_accounts_label":KEYS_ACCOUNTS_LABEL,"required_next_stage":"total_export_handoff_commit_runtime"}
    return {"schema_version":SCHEMA_VERSION,"id":stable_id("source_adapter.evidence_database_writeback_runtime",rows),"status":STATUS,"evidence_database_writeback_row_count":len(rows),"evidence_database_writeback_rows":rows,"handoff":handoff,"operator_summary":{"schema_version":"source_adapter_evidence_database_writeback_operator_summary_v1","status":STATUS,"evidence_database_writeback_row_count":len(rows),"keys_accounts_label":KEYS_ACCOUNTS_LABEL},"issue_count":len(issues),"issues":issues}


def example_source_adapter_evidence_database_writeback_runtime_package() -> dict[str, Any]:
    return build_source_adapter_evidence_database_writeback_runtime()
