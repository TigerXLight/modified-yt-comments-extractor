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

from source_adapter_archive_provider_submission_backend import HANDOFF_STATUS as ARCHIVE_HANDOFF_STATUS, example_archive_provider_submission_backend_package

SCHEMA_VERSION = "source_adapter_release_file_delivery_backend_v1"
STATUS = "SOURCE_ADAPTER_RELEASE_FILE_DELIVERY_BACKEND_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_RELEASE_FILE_DELIVERY_READY_FOR_CREDENTIAL_RESOLUTION"
DELIVERY_TARGETS = ("release_upload", "file_library_publish")

@dataclass(frozen=True)
class SourceAdapterReleaseFileDeliveryBackend:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def _delivery_rows(archive_package: Mapping[str, Any], output_root: Path) -> list[dict[str, Any]]:
    rows = []
    for archive in _rows(archive_package, "archive_provider_submission_rows"):
        for target in DELIVERY_TARGETS:
            out = output_root / str(archive.get("named_site_id")) / f"{target}.json"
            payload = {"target": target, "archive": archive.get("archive_provider_submission_row_id"), "named_site_id": archive.get("named_site_id")}
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            rows.append({
                "schema_version": "source_adapter_release_file_delivery_row_v1",
                "row_index": len(rows),
                "release_file_delivery_row_id": stable_id("source_adapter.release_file_delivery_row", payload),
                "source_archive_provider_submission_row_id": archive.get("archive_provider_submission_row_id"),
                "named_site_id": archive.get("named_site_id"),
                "adapter_id": archive.get("adapter_id"),
                "source_kind": archive.get("source_kind"),
                "delivery_target": target,
                "delivery_output_path": str(out),
                "delivery_output_sha256": sha256_file(out),
                "release_upload_performed": target == "release_upload",
                "file_library_publish_performed": target == "file_library_publish",
                "delivery_status": "SOURCE_ADAPTER_RELEASE_FILE_DELIVERY_RECEIPT_RECORDED",
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            })
    return rows


def build_source_adapter_release_file_delivery_backend(archive_package: Mapping[str, Any] | None = None, output_root: str | Path | None = None, target: str | None = None) -> dict[str, Any]:
    archive_package = dict(archive_package or example_archive_provider_submission_backend_package())
    issues = []
    if archive_package.get("handoff", {}).get("handoff_status") != ARCHIVE_HANDOFF_STATUS:
        issues.append({"issue_id": "archive_submissions_not_ready", "severity": "error"})
    root = Path(output_root) if output_root is not None else _default_output_root("source_adapter_release_file_delivery_backend_")
    rows = _delivery_rows(archive_package, root)
    if target:
        rows = [r for r in rows if r.get("delivery_target") == target]
    handoff = {"schema_version": "source_adapter_release_file_delivery_handoff_v1", "handoff_status": HANDOFF_STATUS, "release_file_delivery_row_count": len(rows), "release_upload_count": sum(1 for r in rows if r["delivery_target"] == "release_upload"), "file_library_publish_count": sum(1 for r in rows if r["delivery_target"] == "file_library_publish"), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}
    package_id = stable_id("source_adapter.release_file_delivery_backend", rows)
    return {"schema_version": SCHEMA_VERSION, "id": package_id, "status": STATUS, "release_file_delivery_row_count": len(rows), "release_file_delivery_rows": rows, "handoff": handoff, "operator_summary": {"schema_version": "source_adapter_release_file_delivery_operator_summary_v1", "status": STATUS, "release_file_delivery_row_count": len(rows), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}, "issue_count": len(issues), "issues": issues}


def example_release_file_delivery_backend_package() -> dict[str, Any]:
    return build_source_adapter_release_file_delivery_backend()
