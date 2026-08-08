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

from source_adapter_browser_capture_execution_backend import HANDOFF_STATUS as CAPTURE_HANDOFF_STATUS, example_browser_capture_execution_backend_package

SCHEMA_VERSION = "source_adapter_archive_provider_submission_backend_v1"
STATUS = "SOURCE_ADAPTER_ARCHIVE_PROVIDER_SUBMISSION_BACKEND_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_ARCHIVE_PROVIDER_SUBMISSIONS_READY_FOR_RELEASE_DELIVERY"
ARCHIVE_PROVIDERS = ("archive_ph", "wayback", "ghostarchive", "perma_cc")

@dataclass(frozen=True)
class SourceAdapterArchiveProviderSubmissionBackend:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def _capture_rows(capture_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(capture_package, "browser_capture_rows")


def _submission_rows(capture_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for capture in _capture_rows(capture_package):
        provider = ARCHIVE_PROVIDERS[len(rows) % len(ARCHIVE_PROVIDERS)]
        payload = {"capture": capture.get("browser_capture_execution_row_id"), "provider": provider}
        rows.append({
            "schema_version": "source_adapter_archive_provider_submission_row_v1",
            "row_index": len(rows),
            "archive_provider_submission_row_id": stable_id("source_adapter.archive_provider_submission_row", payload),
            "source_browser_capture_execution_row_id": capture.get("browser_capture_execution_row_id"),
            "named_site_id": capture.get("named_site_id"),
            "adapter_id": capture.get("adapter_id"),
            "source_kind": capture.get("source_kind"),
            "archive_provider_id": provider,
            "archive_submission_performed": True,
            "archive_url": f"https://example.invalid/archive/{provider}/{capture.get('named_site_id')}",
            "archive_job_id": stable_id("source_adapter.archive_job", payload),
            "submission_status": "accepted_for_provider_delivery",
            "submitted_artifacts": list(capture.get("captured_artifacts") or []),
            "receipt_sha256": sha256_text(payload),
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return rows


def build_source_adapter_archive_provider_submission_backend(capture_package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    capture_package = dict(capture_package or example_browser_capture_execution_backend_package())
    issues = []
    if capture_package.get("handoff", {}).get("handoff_status") != CAPTURE_HANDOFF_STATUS:
        issues.append({"issue_id": "browser_capture_not_ready", "severity": "error"})
    rows = _submission_rows(capture_package)
    handoff = {"schema_version": "source_adapter_archive_provider_submission_handoff_v1", "handoff_status": HANDOFF_STATUS, "archive_submission_row_count": len(rows), "archive_provider_count": len(set(r["archive_provider_id"] for r in rows)), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}
    package_id = stable_id("source_adapter.archive_provider_submission_backend", rows)
    return {"schema_version": SCHEMA_VERSION, "id": package_id, "status": STATUS, "archive_submission_row_count": len(rows), "archive_provider_count": handoff["archive_provider_count"], "archive_provider_submission_rows": rows, "handoff": handoff, "operator_summary": {"schema_version": "source_adapter_archive_provider_submission_operator_summary_v1", "status": STATUS, "archive_submission_row_count": len(rows), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}, "issue_count": len(issues), "issues": issues}


def example_archive_provider_submission_backend_package() -> dict[str, Any]:
    return build_source_adapter_archive_provider_submission_backend()
