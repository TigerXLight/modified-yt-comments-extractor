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

from source_adapter_live_provider_profile_runtime import example_live_provider_profile_runtime_package
from source_adapter_browser_capture_execution_backend import example_browser_capture_execution_backend_package
from source_adapter_archive_provider_submission_backend import example_archive_provider_submission_backend_package
from source_adapter_release_file_delivery_backend import example_release_file_delivery_backend_package
from source_adapter_keys_accounts_credential_reference_runtime import example_keys_accounts_credential_reference_runtime_package
from source_adapter_end_to_end_operator_execution_orchestrator import example_end_to_end_operator_execution_orchestrator_package
from source_adapter_gui_live_execution_panel_wiring import example_gui_live_execution_panel_wiring_package

SCHEMA_VERSION = "source_adapter_full_execution_integration_bundle_closeout_v1"
STATUS = "SOURCE_ADAPTER_FULL_EXECUTION_INTEGRATION_BUNDLE_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_FULL_EXECUTION_INTEGRATION_READY_FOR_PROVIDER_SPECIFIC_ADAPTERS_AND_GUI_INSTALLATION"

def build_source_adapter_full_execution_integration_bundle_closeout() -> dict[str, Any]:
    packages = {
        "live_provider_profiles": example_live_provider_profile_runtime_package(),
        "browser_capture_backend": example_browser_capture_execution_backend_package(),
        "archive_provider_submission_backend": example_archive_provider_submission_backend_package(),
        "release_file_delivery_backend": example_release_file_delivery_backend_package(),
        "keys_accounts_credential_reference_runtime": example_keys_accounts_credential_reference_runtime_package(),
        "end_to_end_operator_execution_orchestrator": example_end_to_end_operator_execution_orchestrator_package(),
        "gui_live_execution_panel_wiring": example_gui_live_execution_panel_wiring_package(),
    }
    issue_count = sum(int(pkg.get("issue_count", 0)) for pkg in packages.values())
    handoff = {"schema_version": "source_adapter_full_execution_integration_handoff_v1", "handoff_status": HANDOFF_STATUS, "implemented_package_count": len(packages), "provider_profile_count": packages["live_provider_profiles"]["provider_profile_count"], "browser_capture_row_count": packages["browser_capture_backend"]["browser_capture_row_count"], "archive_submission_row_count": packages["archive_provider_submission_backend"]["archive_submission_row_count"], "release_file_delivery_row_count": packages["release_file_delivery_backend"]["release_file_delivery_row_count"], "credential_reference_row_count": packages["keys_accounts_credential_reference_runtime"]["credential_reference_row_count"], "end_to_end_receipt_row_count": packages["end_to_end_operator_execution_orchestrator"]["end_to_end_receipt_row_count"], "gui_route_row_count": packages["gui_live_execution_panel_wiring"]["gui_route_row_count"], "keys_accounts_label": KEYS_ACCOUNTS_LABEL}
    return {"schema_version": SCHEMA_VERSION, "id": stable_id("source_adapter.full_execution_integration_closeout", handoff), "status": STATUS, "implemented_package_count": len(packages), "package_statuses": {key: pkg["status"] for key, pkg in packages.items()}, "handoff": handoff, "operator_summary": {"schema_version": "source_adapter_full_execution_integration_operator_summary_v1", "status": STATUS, "implemented_package_count": len(packages), "next_actions": ["install GUI live execution panel into the concrete application window", "bind provider-specific adapters for browser/archive/release/file-library providers", "run operator-selected named sites and collect receipts"], "keys_accounts_label": KEYS_ACCOUNTS_LABEL}, "issue_count": issue_count, "issues": []}

def example_full_execution_integration_bundle_closeout_package() -> dict[str, Any]:
    return build_source_adapter_full_execution_integration_bundle_closeout()
