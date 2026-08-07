from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "source_comment_extraction_store_v1"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def _safe_filename(value: str) -> str:
    value = _safe_text(value)
    value = "".join(ch if ch.isalnum() or ch in "._-" else "." for ch in value)
    value = value.strip("._-")
    return value[:120] or "source_comments"


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    data = _json_bytes(payload)
    path.write_bytes(data)
    return {
        "role": payload.get("store_role") or payload.get("role") or path.stem,
        "filename": path.name,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def build_comment_index(extraction: dict[str, Any]) -> dict[str, Any]:
    comments = extraction.get("comments") if isinstance(extraction.get("comments"), list) else []
    return {
        "schema_version": "source_comment_index_v1",
        "store_role": "source_comment_index",
        "comment_extraction_id": extraction.get("comment_extraction_id"),
        "adapter_id": extraction.get("adapter_id"),
        "source_url": extraction.get("source_url"),
        "comment_count": len(comments),
        "comments": [
            {
                "comment_id": item.get("comment_id"),
                "author": item.get("author"),
                "parent_id": item.get("parent_id", ""),
                "depth": item.get("depth", 0),
                "text_sha256": hashlib.sha256(_safe_text(item.get("text")).encode("utf-8")).hexdigest(),
            }
            for item in comments
            if isinstance(item, dict)
        ],
    }


def build_capture_bundle_handoff(extraction: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "source_comment_capture_bundle_handoff_v1",
        "store_role": "source_comment_capture_bundle_handoff",
        "comment_extraction_id": extraction.get("comment_extraction_id"),
        "adapter_id": extraction.get("adapter_id"),
        "source_url": extraction.get("source_url"),
        "comment_count": extraction.get("comment_count", 0),
        "comment_sha256": extraction.get("comment_sha256"),
        "selected_artifact": extraction.get("selected_artifact", {}),
        "next_stage": "source_capture_bundle",
        "required_next_inputs": [
            "source_content_extraction_json when article/content is available",
            "source_comment_extraction_json",
            "source_artifact_collection_manifest_json",
        ],
    }


def store_source_comment_extraction(extraction: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    extraction_id = _safe_filename(_safe_text(extraction.get("comment_extraction_id")) or "source.comments")
    extraction_payload = dict(extraction)
    extraction_payload["store_role"] = "source_comment_extraction"
    index_payload = build_comment_index(extraction)
    handoff_payload = build_capture_bundle_handoff(extraction)
    stored_files = [
        _write_json(out / f"{extraction_id}.comment_extraction.json", extraction_payload),
        _write_json(out / f"{extraction_id}.comment_index.json", index_payload),
        _write_json(out / f"{extraction_id}.capture_bundle_handoff.json", handoff_payload),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "comment_extraction_id": extraction.get("comment_extraction_id"),
        "adapter_id": extraction.get("adapter_id"),
        "source_url": extraction.get("source_url"),
        "comment_count": extraction.get("comment_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }
