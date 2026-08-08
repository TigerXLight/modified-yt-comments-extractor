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

from source_adapter_release_file_delivery_backend import HANDOFF_STATUS as DELIVERY_HANDOFF_STATUS, example_release_file_delivery_backend_package

SCHEMA_VERSION = "source_adapter_keys_accounts_credential_reference_runtime_v1"
STATUS = "SOURCE_ADAPTER_KEYS_ACCOUNTS_CREDENTIAL_REFERENCE_RUNTIME_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_KEYS_ACCOUNTS_CREDENTIAL_REFERENCES_READY_FOR_E2E_ORCHESTRATION"

@dataclass(frozen=True)
class SourceAdapterKeysAccountsCredentialReferenceRuntime:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def _credential_rows(delivery_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    site_ids = sorted({str(row.get("named_site_id")) for row in _rows(delivery_package, "release_file_delivery_rows")})
    rows = []
    for index, site_id in enumerate(site_ids):
        ref = f"keys_accounts://operator-approved/{site_id}/provider-suite"
        rows.append({
            "schema_version": "source_adapter_keys_accounts_credential_reference_row_v1",
            "row_index": index,
            "credential_reference_runtime_row_id": stable_id("source_adapter.keys_accounts_credential_reference_row", ref),
            "named_site_id": site_id,
            "credential_reference_id": ref,
            "provider_ids": ["browser_capture", "archive_submit", "release_upload", "file_library_publish"],
            "lookup_status": "resolved_to_redacted_reference",
            "redacted_reference_hash": sha256_text(ref),
            "secret_material_returned": False,
            "secret_material_stored": False,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return rows


def resolve_credential_reference(reference_id: str, credential_map: Mapping[str, str] | None = None) -> dict[str, Any]:
    present = credential_map is not None and reference_id in credential_map
    return {"credential_reference_id": reference_id, "lookup_status": "operator_secret_available" if present else "redacted_reference_only", "redacted_reference_hash": sha256_text(reference_id), "secret_material_returned": False, "keys_accounts_label": KEYS_ACCOUNTS_LABEL}


def build_source_adapter_keys_accounts_credential_reference_runtime(delivery_package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    delivery_package = dict(delivery_package or example_release_file_delivery_backend_package())
    issues = []
    if delivery_package.get("handoff", {}).get("handoff_status") != DELIVERY_HANDOFF_STATUS:
        issues.append({"issue_id": "delivery_backend_not_ready", "severity": "error"})
    rows = _credential_rows(delivery_package)
    handoff = {"schema_version": "source_adapter_keys_accounts_credential_reference_handoff_v1", "handoff_status": HANDOFF_STATUS, "credential_reference_row_count": len(rows), "secret_material_returned": False, "keys_accounts_label": KEYS_ACCOUNTS_LABEL}
    package_id = stable_id("source_adapter.keys_accounts_credential_reference_runtime", rows)
    return {"schema_version": SCHEMA_VERSION, "id": package_id, "status": STATUS, "credential_reference_row_count": len(rows), "credential_reference_rows": rows, "handoff": handoff, "operator_summary": {"schema_version": "source_adapter_keys_accounts_credential_reference_operator_summary_v1", "status": STATUS, "credential_reference_row_count": len(rows), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}, "issue_count": len(issues), "issues": issues}


def example_keys_accounts_credential_reference_runtime_package() -> dict[str, Any]:
    return build_source_adapter_keys_accounts_credential_reference_runtime()
