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


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return {"path": str(path), "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def named_sites() -> list[dict[str, Any]]:
    return [
        {"row_index": 0, "named_site_id": "operator_named_site.article_0", "adapter_id": "article", "source_kind": "web_article", "source_url": "https://example.invalid/article/0", "capture_profile": "browser_html_screenshot_archive"},
        {"row_index": 1, "named_site_id": "operator_named_site.social_post_1", "adapter_id": "social_post", "source_kind": "social_media", "source_url": "https://example.invalid/social/1", "capture_profile": "thread_html_json_screenshot_archive"},
        {"row_index": 2, "named_site_id": "operator_named_site.comments_thread_2", "adapter_id": "comments_thread", "source_kind": "comments", "source_url": "https://example.invalid/comments/2", "capture_profile": "comments_dom_json_screenshot_archive"},
        {"row_index": 3, "named_site_id": "operator_named_site.media_transcript_3", "adapter_id": "media_transcript", "source_kind": "media_or_transcript", "source_url": "https://example.invalid/media/3", "capture_profile": "media_metadata_transcript_source_archive"},
        {"row_index": 4, "named_site_id": "operator_named_site.archive_receipt_4", "adapter_id": "archive_receipt", "source_kind": "archive_provider", "source_url": "https://example.invalid/archive/4", "capture_profile": "archive_receipt_review_delivery"},
    ]

SCHEMA_VERSION = "source_adapter_release_manifest_signing_runtime_v1"
STATUS = "SOURCE_ADAPTER_RELEASE_MANIFEST_SIGNING_RUNTIME_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_RELEASE_MANIFEST_SIGNING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE"
ROW_STATUS = "SOURCE_ADAPTER_RELEASE_MANIFEST_SIGNING_READY"
ROW_KEY = "manifest_signing_rows"


def build_source_adapter_release_manifest_signing_runtime_rows(operator_id: str = "operator") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for site in named_sites():
        for action_index, action in enumerate(PROVIDER_ACTIONS):
            seed = {"site": site["named_site_id"], "action": action, "row_key": ROW_KEY, "operator_id": operator_id}
            rows.append({
                "schema_version": f"{ROW_KEY}_row_v1",
                "row_id": stable_id(f"source_adapter.{ROW_KEY}", seed),
                "row_index": len(rows),
                "site_row_index": site["row_index"],
                "named_site_id": site["named_site_id"],
                "adapter_id": site["adapter_id"],
                "source_kind": site["source_kind"],
                "source_url": site["source_url"],
                "capture_profile": site["capture_profile"],
                "provider_action": action,
                "operator_id": operator_id,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                "credential_secret_material_present": False,
                "redacted_reference_hash": sha256_text({"provider_action": action, "named_site_id": site["named_site_id"]})[:24],
                "receipt_required": True,
                "operator_review_required": action in ("archive_submit", "release_upload", "file_library_publish"),
                "execution_policy_status": ROW_STATUS,
                "ready_for_runtime_dispatch": True,
            })
    return rows


def example_source_adapter_release_manifest_signing_runtime_package(operator_id: str = "operator") -> dict[str, Any]:
    rows = build_source_adapter_release_manifest_signing_runtime_rows(operator_id=operator_id)
    package = {
        "schema_version": SCHEMA_VERSION,
        "id": stable_id("source_adapter.source_adapter_release_manifest_signing_runtime", {"rows": rows, "operator_id": operator_id}),
        "status": STATUS,
        "row_key": ROW_KEY,
        "manifest_signing_rows_row_count": len(rows),
        "manifest_signing_rows": rows,
        "operator_summary": {
            "schema_version": "source_adapter_release_manifest_signing_runtime_operator_summary_v1",
            "status": STATUS,
            "operator_id": operator_id,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "named_site_row_count": len(named_sites()),
            "provider_action_count": len(PROVIDER_ACTIONS),
            "manifest_signing_rows_row_count": len(rows),
            "all_rows_require_receipts": all(row["receipt_required"] for row in rows),
            "secret_material_present": any(row["credential_secret_material_present"] for row in rows),
            "next_actions": [
                "Use these runtime rows as the next implementation handoff.",
                "Preserve KEYS/ACCOUNTS credential-reference selection with redacted hashes.",
                "Record provider receipts before evidence/release completion claims.",
            ],
        },
        "handoff": {
            "schema_version": "source_adapter_release_manifest_signing_runtime_handoff_v1",
            "handoff_status": HANDOFF_STATUS,
            "input_checkpoint": "source_adapter.production_runtime_bundle_closeout",
            "ready_for_next_bundle": True,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "row_count": len(rows),
        },
        "issue_count": 0,
        "issues": [],
    }
    return package


def write_source_adapter_release_manifest_signing_runtime_receipts(output_dir: str | Path | None = None, operator_id: str = "operator") -> dict[str, Any]:
    package = example_source_adapter_release_manifest_signing_runtime_package(operator_id=operator_id)
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_release_manifest_signing_runtime_receipts_"))
    stored_files = []
    stored_files.append(_write_json(output_root / f"{package['id']}.package.json", package))
    stored_files.append(_write_json(output_root / f"{package['id']}.handoff.json", package["handoff"]))
    stored_files.append(_write_json(output_root / f"{package['id']}.manifest_signing_rows.json", package["manifest_signing_rows"]))
    for role, meta in zip(("package", "handoff", "manifest_signing_rows"), stored_files):
        meta["role"] = role
    return {
        "schema_version": "source_adapter_release_manifest_signing_runtime_receipt_writer_v1",
        "id": package["id"],
        "status": package["status"],
        "store_status": "STORED",
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }


if __name__ == "__main__":
    print(json.dumps(example_source_adapter_release_manifest_signing_runtime_package(), indent=2, sort_keys=True))
