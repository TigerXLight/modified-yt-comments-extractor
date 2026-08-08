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

SCHEMA_VERSION = "source_adapter_live_provider_profile_runtime_v1"
STATUS = "SOURCE_ADAPTER_LIVE_PROVIDER_PROFILE_RUNTIME_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_LIVE_PROVIDER_PROFILES_READY_FOR_BACKEND_EXECUTION"

@dataclass(frozen=True)
class SourceAdapterLiveProviderProfileRuntime:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def _profile_rows() -> list[dict[str, Any]]:
    rows = []
    for index, action in enumerate(PROVIDER_ACTIONS):
        command = {
            "credential_lookup": ["python", "-m", "source_adapter_keys_accounts_credential_reference_runtime", "--json"],
            "browser_capture": ["python", "-m", "source_adapter_browser_capture_execution_backend", "--json"],
            "archive_submit": ["python", "-m", "source_adapter_archive_provider_submission_backend", "--json"],
            "release_upload": ["python", "-m", "source_adapter_release_file_delivery_backend", "--json", "--target", "release_upload"],
            "file_library_publish": ["python", "-m", "source_adapter_release_file_delivery_backend", "--json", "--target", "file_library_publish"],
        }[action]
        rows.append({
            "schema_version": "source_adapter_live_provider_profile_row_v1",
            "row_index": index,
            "provider_action": action,
            "provider_profile_id": stable_id("source_adapter.live_provider_profile", action),
            "implementation_module": command[2],
            "command_template": command,
            "execution_mode": "operator_approved_provider_execution",
            "live_capable": True,
            "fake_capable": True,
            "requires_operator_inputs": True,
            "requires_receipt_capture": True,
            "credential_reference_only": action == "credential_lookup",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return rows


def build_source_adapter_live_provider_profile_runtime() -> dict[str, Any]:
    rows = _profile_rows()
    handoff = {
        "schema_version": "source_adapter_live_provider_profile_handoff_v1",
        "handoff_status": HANDOFF_STATUS,
        "provider_profile_count": len(rows),
        "provider_actions": list(PROVIDER_ACTIONS),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "required_next_stage": "browser_archive_release_and_credential_backend_execution",
    }
    package_id = stable_id("source_adapter.live_provider_profile_runtime", rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "id": package_id,
        "status": STATUS,
        "provider_profile_count": len(rows),
        "provider_profile_rows": rows,
        "handoff": handoff,
        "operator_summary": {
            "schema_version": "source_adapter_live_provider_profile_operator_summary_v1",
            "status": STATUS,
            "provider_profile_count": len(rows),
            "live_capable_profile_count": sum(1 for r in rows if r["live_capable"]),
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        },
        "issue_count": 0,
        "issues": [],
    }


def example_live_provider_profile_runtime_package() -> dict[str, Any]:
    return build_source_adapter_live_provider_profile_runtime()
