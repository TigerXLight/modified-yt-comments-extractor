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
SOURCE_KINDS = ("web_article", "social_media", "comments", "media_or_transcript", "archive_provider")
PROVIDER_ACTIONS = ("credential_lookup", "browser_capture", "archive_submit", "release_upload", "file_library_publish")


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
        {"row_index": 0, "named_site_id": "operator_named_site.article_0", "adapter_id": "article", "source_kind": "web_article", "fixture_family": "article_news_page", "capture_profile": "browser_html_screenshot_archive", "source_url": "https://example.invalid/article/0"},
        {"row_index": 1, "named_site_id": "operator_named_site.social_post_1", "adapter_id": "social_post", "source_kind": "social_media", "fixture_family": "social_post_thread", "capture_profile": "thread_html_json_screenshot_archive", "source_url": "https://example.invalid/social/1"},
        {"row_index": 2, "named_site_id": "operator_named_site.comments_thread_2", "adapter_id": "comments_thread", "source_kind": "comments", "fixture_family": "comments_replies_thread", "capture_profile": "comments_dom_json_screenshot_archive", "source_url": "https://example.invalid/comments/2"},
        {"row_index": 3, "named_site_id": "operator_named_site.media_transcript_3", "adapter_id": "media_transcript", "source_kind": "media_or_transcript", "fixture_family": "media_transcript_asr_source", "capture_profile": "media_metadata_transcript_source_archive", "source_url": "https://example.invalid/media/3"},
        {"row_index": 4, "named_site_id": "operator_named_site.archive_receipt_4", "adapter_id": "archive_receipt", "source_kind": "archive_provider", "fixture_family": "archive_provider_receipt", "capture_profile": "archive_receipt_review_delivery", "source_url": "https://example.invalid/archive/4"},
    ]


def _default_output_root(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return {"path": str(path), "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}

from source_adapter_provider_configuration_resolver import example_source_adapter_provider_configuration_resolver_package
from source_adapter_browser_driver_binding_runtime import example_source_adapter_browser_driver_binding_runtime_package
from source_adapter_archive_release_policy_runtime import example_source_adapter_archive_release_policy_runtime_package
from source_adapter_provider_receipt_ledger_runtime import example_source_adapter_provider_receipt_ledger_runtime_package
from source_adapter_evidence_sync_runtime import example_source_adapter_evidence_sync_runtime_package
from source_adapter_total_export_finalization_runtime import example_source_adapter_total_export_finalization_runtime_package
from source_adapter_gui_operator_run_history_runtime import example_source_adapter_gui_operator_run_history_runtime_package
from source_adapter_release_review_acceptance_runtime import example_source_adapter_release_review_acceptance_runtime_package
from source_adapter_operator_dashboard_runtime import example_source_adapter_operator_dashboard_runtime_package

SCHEMA_VERSION = "source_adapter_provider_integration_bundle_closeout_v1"
STATUS = "SOURCE_ADAPTER_PROVIDER_INTEGRATION_BUNDLE_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_PROVIDER_INTEGRATION_READY_FOR_REAL_PROVIDER_CONFIGURATION_AND_FINAL_RELEASE_REVIEW"

def build_source_adapter_provider_integration_bundle_closeout() -> dict[str, Any]:
    packages={
        "provider_configuration_resolver": example_source_adapter_provider_configuration_resolver_package(),
        "browser_driver_binding_runtime": example_source_adapter_browser_driver_binding_runtime_package(),
        "archive_release_policy_runtime": example_source_adapter_archive_release_policy_runtime_package(),
        "provider_receipt_ledger_runtime": example_source_adapter_provider_receipt_ledger_runtime_package(),
        "evidence_sync_runtime": example_source_adapter_evidence_sync_runtime_package(),
        "total_export_finalization_runtime": example_source_adapter_total_export_finalization_runtime_package(),
        "gui_operator_run_history_runtime": example_source_adapter_gui_operator_run_history_runtime_package(),
        "release_review_acceptance_runtime": example_source_adapter_release_review_acceptance_runtime_package(),
        "operator_dashboard_runtime": example_source_adapter_operator_dashboard_runtime_package(),
    }
    issue_count=sum(int(pkg.get("issue_count",0)) for pkg in packages.values())
    handoff={"schema_version":"source_adapter_provider_integration_bundle_handoff_v1","handoff_status":HANDOFF_STATUS,"implemented_package_count":len(packages),"provider_configuration_row_count":packages["provider_configuration_resolver"]["provider_configuration_row_count"],"provider_receipt_ledger_row_count":packages["provider_receipt_ledger_runtime"]["provider_receipt_ledger_row_count"],"evidence_sync_row_count":packages["evidence_sync_runtime"]["evidence_sync_row_count"],"total_export_finalization_row_count":packages["total_export_finalization_runtime"]["total_export_finalization_row_count"],"operator_dashboard_card_count":packages["operator_dashboard_runtime"]["operator_dashboard_card_count"],"keys_accounts_label":KEYS_ACCOUNTS_LABEL,"required_next_stage":"real_provider_configuration_and_final_release_review"}
    return {"schema_version":SCHEMA_VERSION,"id":stable_id("source_adapter.provider_integration_bundle_closeout",handoff),"status":STATUS,"implemented_package_count":len(packages),"package_statuses":{k:v["status"] for k,v in packages.items()},"handoff":handoff,"operator_summary":{"schema_version":"source_adapter_provider_integration_operator_summary_v1","status":STATUS,"implemented_package_count":len(packages),"next_actions":["connect real provider configuration values into provider configuration resolver","run selected named-site provider execution through GUI/operator dashboard","review release acceptance rows and Total Export finalization receipts"],"keys_accounts_label":KEYS_ACCOUNTS_LABEL},"issue_count":issue_count,"issues":[]}

def example_source_adapter_provider_integration_bundle_closeout_package() -> dict[str, Any]:
    return build_source_adapter_provider_integration_bundle_closeout()
