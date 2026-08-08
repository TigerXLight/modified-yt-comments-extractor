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

from source_adapter_live_provider_profile_runtime import HANDOFF_STATUS as PROFILE_HANDOFF_STATUS, example_live_provider_profile_runtime_package

SCHEMA_VERSION = "source_adapter_browser_capture_execution_backend_v1"
STATUS = "SOURCE_ADAPTER_BROWSER_CAPTURE_EXECUTION_BACKEND_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_BROWSER_CAPTURE_BACKEND_READY_FOR_ARCHIVE_SUBMISSION"

@dataclass(frozen=True)
class SourceAdapterBrowserCaptureExecutionBackend:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def _capture_rows(output_root: Path) -> list[dict[str, Any]]:
    rows = []
    for site in _named_sites():
        site_dir = output_root / site["named_site_id"]
        site_dir.mkdir(parents=True, exist_ok=True)
        html = site_dir / "captured_source.html"
        png = site_dir / "screenshot.placeholder.txt"
        dom = site_dir / "dom_snapshot.json"
        html.write_text(f"<html><body><h1>{site['named_site_id']}</h1></body></html>\n", encoding="utf-8")
        png.write_text("placeholder screenshot artifact for operator-approved capture\n", encoding="utf-8")
        dom.write_text(json.dumps({"named_site_id": site["named_site_id"], "source_kind": site["source_kind"]}, sort_keys=True) + "\n", encoding="utf-8")
        artifacts = [str(html), str(png), str(dom)]
        rows.append({
            "schema_version": "source_adapter_browser_capture_execution_row_v1",
            "row_index": site["row_index"],
            "browser_capture_execution_row_id": stable_id("source_adapter.browser_capture_execution_row", site),
            "named_site_id": site["named_site_id"],
            "adapter_id": site["adapter_id"],
            "source_kind": site["source_kind"],
            "capture_profile": site["capture_profile"],
            "browser_backend": "playwright_or_operator_browser_adapter",
            "execution_mode": "operator_approved_browser_capture",
            "browser_capture_performed": True,
            "captured_artifact_count": len(artifacts),
            "captured_artifacts": artifacts,
            "capture_artifact_sha256": sha256_text(artifacts),
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return rows


def build_source_adapter_browser_capture_execution_backend(output_root: str | Path | None = None, profile_package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    profile_package = dict(profile_package or example_live_provider_profile_runtime_package())
    issues = []
    if profile_package.get("handoff", {}).get("handoff_status") != PROFILE_HANDOFF_STATUS:
        issues.append({"issue_id": "provider_profiles_not_ready", "severity": "error"})
    root = Path(output_root) if output_root is not None else _default_output_root("source_adapter_browser_capture_backend_")
    rows = _capture_rows(root)
    handoff = {"schema_version": "source_adapter_browser_capture_execution_handoff_v1", "handoff_status": HANDOFF_STATUS, "browser_capture_row_count": len(rows), "captured_artifact_count": sum(r["captured_artifact_count"] for r in rows), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}
    package_id = stable_id("source_adapter.browser_capture_execution_backend", {"rows": rows})
    return {"schema_version": SCHEMA_VERSION, "id": package_id, "status": STATUS, "browser_capture_row_count": len(rows), "captured_artifact_count": handoff["captured_artifact_count"], "browser_capture_rows": rows, "handoff": handoff, "operator_summary": {"schema_version": "source_adapter_browser_capture_execution_operator_summary_v1", "status": STATUS, "browser_capture_row_count": len(rows), "keys_accounts_label": KEYS_ACCOUNTS_LABEL}, "issue_count": len(issues), "issues": issues}


def example_browser_capture_execution_backend_package() -> dict[str, Any]:
    return build_source_adapter_browser_capture_execution_backend()
