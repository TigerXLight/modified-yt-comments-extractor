from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from source_adapter_coverage import SourceAdapterCoverageReport, coverage_report_to_json

SCHEMA_VERSION = "source_adapter_coverage_store_v1"
_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _safe_filename(value: str, fallback: str = "source_adapter_coverage") -> str:
    cleaned = _SAFE_FILENAME_RE.sub("_", str(value or "")).strip("._-")
    return cleaned or fallback


def _write_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return {"filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_coverage(report: SourceAdapterCoverageReport, output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = _safe_filename(report.coverage_id)
    report_payload = report.to_dict()
    matrix_payload = {
        "schema_version": "source_adapter_coverage_matrix_v1",
        "coverage_id": report.coverage_id,
        "coverage_strategy": "one_framework_many_adapters",
        "stage_matrix": report_payload["stage_matrix"],
    }
    plan_payload = {
        "schema_version": "source_adapter_shared_implementation_plan_v1",
        "coverage_id": report.coverage_id,
        "shared_implementation_plan": report_payload["shared_implementation_plan"],
        "adapter_work_items": report_payload["adapter_work_items"],
    }
    browser_payload = report_payload["lightweight_browser_plan"]

    stored = []
    for role, suffix, payload in (
        ("source_adapter_coverage_report", "coverage_report", report_payload),
        ("source_adapter_coverage_matrix", "coverage_matrix", matrix_payload),
        ("source_adapter_shared_implementation_plan", "shared_implementation_plan", plan_payload),
        ("source_adapter_lightweight_browser_plan", "lightweight_browser_plan", browser_payload),
    ):
        path = out / f"{base}.{suffix}.json"
        meta = _write_json(path, payload)
        meta["role"] = role
        stored.append(meta)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "coverage_id": report.coverage_id,
        "adapter_count": len(report.adapters),
        "output_file_count": len(stored),
        "stored_files": stored,
    }


def store_source_adapter_coverage_json(report: SourceAdapterCoverageReport, output_dir: str | Path) -> str:
    return json.dumps(store_source_adapter_coverage(report, output_dir), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
