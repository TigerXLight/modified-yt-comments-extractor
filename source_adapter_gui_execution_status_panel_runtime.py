from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

KEYS_ACCOUNTS_LABEL = "KEYS/ACCOUNTS"
PROVIDER_ACTIONS = ("credential_lookup", "browser_launch", "page_capture", "comment_capture", "media_transcript_capture", "archive_submit", "archive_poll", "archive_import", "evidence_write", "release_publish")
SOURCE_KINDS = ("web_article", "social_media", "comments", "media_or_transcript", "archive_provider")
RUNTIME_SURFACES = ("operator_cli", "gui_panel", "provider_backend", "evidence_database", "total_export_release", "archive_review", "file_library_publish")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{sha256_text(value)[:12]}"


def named_sites() -> list[dict[str, Any]]:
    return [
        {"row_index": 0, "named_site_id": "operator_named_site.article_0", "adapter_id": "article", "source_kind": "web_article", "source_url": "https://example.invalid/article/0", "capture_profile": "browser_html_screenshot_archive"},
        {"row_index": 1, "named_site_id": "operator_named_site.social_post_1", "adapter_id": "social_post", "source_kind": "social_media", "source_url": "https://example.invalid/social/1", "capture_profile": "thread_html_json_screenshot_archive"},
        {"row_index": 2, "named_site_id": "operator_named_site.comments_thread_2", "adapter_id": "comments_thread", "source_kind": "comments", "source_url": "https://example.invalid/comments/2", "capture_profile": "comments_dom_json_screenshot_archive"},
        {"row_index": 3, "named_site_id": "operator_named_site.media_transcript_3", "adapter_id": "media_transcript", "source_kind": "media_or_transcript", "source_url": "https://example.invalid/media/3", "capture_profile": "media_metadata_transcript_source_archive"},
        {"row_index": 4, "named_site_id": "operator_named_site.archive_receipt_4", "adapter_id": "archive_receipt", "source_kind": "archive_provider", "source_url": "https://example.invalid/archive/4", "capture_profile": "archive_receipt_review_delivery"},
    ]


def write_json(path: Path, value: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return {"path": str(path), "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


SCHEMA_VERSION = "source_adapter_gui_execution_status_panel_runtime_v1"
STATUS = "SOURCE_ADAPTER_GUI_EXECUTION_STATUS_PANEL_RUNTIME_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_GUI_EXECUTION_STATUS_PANEL_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE"
ROW_STATUS = "SOURCE_ADAPTER_GUI_EXECUTION_STATUS_PANEL_RUNTIME_ROWS_READY"
ROW_KEY = "gui_execution_status_panel_rows"
DESCRIPTION = "GUI execution status panel rows for live run state, provider health, receipts, retries, and completion visibility"


def build_gui_execution_status_panel_rows(operator_id: str = "operator") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for site in named_sites():
        for action_index, action in enumerate(PROVIDER_ACTIONS):
            seed = {"aspect": "gui_execution_status_panel", "site": site, "action": action, "operator_id": operator_id}
            rows.append({
                "schema_version": "source_adapter_gui_execution_status_panel_runtime_row_v1",
                "row_id": stable_id("source_adapter.gui_execution_status_panel.row", seed),
                "row_index": len(rows),
                "site_row_index": site["row_index"],
                "provider_action_index": action_index,
                "named_site_id": site["named_site_id"],
                "adapter_id": site["adapter_id"],
                "source_kind": site["source_kind"],
                "source_url": site["source_url"],
                "capture_profile": site["capture_profile"],
                "provider_action": action,
                "runtime_surfaces": list(RUNTIME_SURFACES),
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
                "credential_reference_required": action == "credential_lookup",
                "credential_secret_material_present": False,
                "redacted_reference_hash_required": action == "credential_lookup",
                "operator_approval_required": True,
                "receipt_required": True,
                "network_execution_requires_explicit_operator_run": action in {"browser_launch", "archive_submit", "archive_poll", "release_publish"},
                "local_dry_run_supported": True,
                "implemented_runtime_surface": True,
                "row_status": ROW_STATUS,
                "payload_sha256": sha256_text(seed),
            })
    return rows


def example_source_adapter_gui_execution_status_panel_runtime_package(operator_id: str = "operator") -> dict[str, Any]:
    rows = build_gui_execution_status_panel_rows(operator_id=operator_id)
    package = {
        "schema_version": SCHEMA_VERSION,
        "id": stable_id("source_adapter.gui_execution_status_panel.package", {"rows": rows, "operator_id": operator_id}),
        "status": STATUS,
        "description": DESCRIPTION,
        "row_key": ROW_KEY,
        "gui_execution_status_panel_rows_count": len(rows),
        ROW_KEY: rows,
        "operator_summary": {
            "schema_version": "source_adapter_gui_execution_status_panel_runtime_operator_summary_v1",
            "status": STATUS,
            "operator_id": operator_id,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "named_site_row_count": len(named_sites()),
            "provider_action_count": len(PROVIDER_ACTIONS),
            "runtime_surface_count": len(RUNTIME_SURFACES),
            "gui_execution_status_panel_rows_count": len(rows),
            "all_rows_receipt_required": all(row["receipt_required"] for row in rows),
            "secret_material_present": any(row["credential_secret_material_present"] for row in rows),
            "implemented_runtime_surface": all(row["implemented_runtime_surface"] for row in rows),
            "operator_approval_required": all(row["operator_approval_required"] for row in rows),
            "next_actions": [
                "Use this runtime surface in the continuing operator-approved execution path.",
                "Preserve KEYS/ACCOUNTS references and redacted hashes in receipts.",
                "Import provider/capture/archive/release receipts before completion claims.",
            ],
        },
        "handoff": {
            "schema_version": "source_adapter_gui_execution_status_panel_runtime_handoff_v1",
            "handoff_status": HANDOFF_STATUS,
            "input_checkpoint": "source_adapter.site_capture_mega_bundle_closeout",
            "ready_for_next_bundle": True,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "row_count": len(rows),
        },
        "issue_count": 0,
        "issues": [],
    }
    return package


def write_source_adapter_gui_execution_status_panel_runtime_receipts(output_dir: str | Path | None = None, operator_id: str = "operator") -> dict[str, Any]:
    package = example_source_adapter_gui_execution_status_panel_runtime_package(operator_id=operator_id)
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_gui_execution_status_panel_runtime_receipts_"))
    stored_files = []
    stored_files.append(write_json(output_root / f"{package['id']}.package.json", package))
    stored_files.append(write_json(output_root / f"{package['id']}.handoff.json", package["handoff"]))
    stored_files.append(write_json(output_root / f"{package['id']}.gui_execution_status_panel_rows.json", package[ROW_KEY]))
    for role, meta in zip(("package", "handoff", ROW_KEY), stored_files):
        meta["role"] = role
    return {
        "schema_version": "source_adapter_gui_execution_status_panel_runtime_receipt_writer_v1",
        "id": package["id"],
        "status": package["status"],
        "store_status": "STORED",
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "operator_summary": package["operator_summary"],
    }


if __name__ == "__main__":
    print(json.dumps(example_source_adapter_gui_execution_status_panel_runtime_package(), indent=2, sort_keys=True))
