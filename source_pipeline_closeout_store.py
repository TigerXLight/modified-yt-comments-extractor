from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_pipeline_closeout import build_source_pipeline_closeout
from source_pipeline_closeout_verifier import verify_source_pipeline_closeout

SCHEMA_VERSION = "source_pipeline_closeout_store_v1"


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_bytes(data)
    path.write_bytes(payload)
    return {
        "filename": path.name,
        "role": data.get("artifact_role", path.stem),
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def store_source_pipeline_closeout(
    archive_review_package: Mapping[str, Any],
    *,
    out_dir: str | Path,
    archive_review_decision: Mapping[str, Any] | None = None,
    archive_review_closeout: Mapping[str, Any] | None = None,
    verify: bool = True,
) -> dict[str, Any]:
    built = build_source_pipeline_closeout(
        archive_review_package,
        archive_review_decision=archive_review_decision,
        archive_review_closeout=archive_review_closeout,
    )
    closeout = built["closeout_report"]
    closeout_id = closeout["source_pipeline_closeout_id"]
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = [
        ("source_pipeline_closeout_report", f"{closeout_id}.source_pipeline_closeout_report.json", built["closeout_report"]),
        ("source_pipeline_stage_inventory", f"{closeout_id}.source_pipeline_stage_inventory.json", built["stage_inventory"]),
        ("source_pipeline_roadmap_closeout_handoff", f"{closeout_id}.source_pipeline_roadmap_closeout_handoff.json", built["roadmap_closeout_handoff"]),
        ("source_pipeline_closeout_operator_summary", f"{closeout_id}.source_pipeline_closeout_operator_summary.json", built["operator_summary"]),
    ]

    stored_files: list[dict[str, Any]] = []
    for role, filename, data in files:
        payload = dict(data)
        payload["artifact_role"] = role
        stored_files.append(_write_json(output_dir / filename, payload))

    verification = verify_source_pipeline_closeout(built) if verify else {"verified": None, "issues": []}
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "source_pipeline_closeout_id": closeout_id,
        "adapter_id": closeout["adapter_id"],
        "source_url": closeout["source_url"],
        "final_status": closeout["final_status"],
        "archive_decision": closeout["archive_decision"],
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
