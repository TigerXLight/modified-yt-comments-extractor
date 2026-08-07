from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

STORE_SCHEMA_VERSION = "source_content_extraction_store_v1"


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_id(value: str, fallback: str) -> str:
    import re

    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9_.-]+", ".", value).strip("._-")
    return value[:96] or fallback


def write_source_content_extraction_store(extraction: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    content_id = _safe_id(str(extraction.get("content_id") or "content"), "content")
    handoff = extraction.get("extraction_handoff") if isinstance(extraction.get("extraction_handoff"), dict) else {}
    summary = {
        "schema_version": "source_content_extraction_summary_v1",
        "content_id": content_id,
        "adapter_id": extraction.get("adapter_id"),
        "source_url": extraction.get("source_url"),
        "title": extraction.get("title"),
        "body_paragraph_count": extraction.get("body_paragraph_count"),
        "body_sha256": extraction.get("body_sha256"),
        "warnings": extraction.get("warnings", []),
    }
    outputs = [
        ("source_content_extraction", f"{content_id}.content_extraction.json", extraction),
        ("source_content_extraction_handoff", f"{content_id}.content_extraction_handoff.json", handoff),
        ("source_content_extraction_summary", f"{content_id}.content_extraction_summary.json", summary),
    ]
    stored_files = []
    for role, filename, payload in outputs:
        data = _json_bytes(payload)
        (output / filename).write_bytes(data)
        stored_files.append(
            {
                "role": role,
                "filename": filename,
                "byte_count": len(data),
                "sha256": _sha256_bytes(data),
            }
        )
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "content_id": content_id,
        "adapter_id": extraction.get("adapter_id"),
        "source_url": extraction.get("source_url"),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }
