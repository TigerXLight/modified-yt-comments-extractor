from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_next_roadmap_work_order_execution_closeout import (
    SCHEMA_VERSION,
    STATUS,
    build_source_adapter_next_roadmap_work_order_execution_closeout,
)
from source_adapter_next_roadmap_work_order_execution_closeout_verifier import verify_source_adapter_next_roadmap_work_order_execution_closeout

STORE_SCHEMA_VERSION = "source_adapter_next_roadmap_work_order_execution_closeout_store_v1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    data = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "role": path.stem.split(".")[-1],
        "filename": path.name,
        "path": str(path),
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def store_source_adapter_next_roadmap_work_order_execution_closeout(package_or_selection_closeout: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    if package_or_selection_closeout.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_selection_closeout)
    else:
        package = build_source_adapter_next_roadmap_work_order_execution_closeout(package_or_selection_closeout).as_dict()
    output_path = Path(output_dir)
    closeout_id = str(package["source_adapter_next_roadmap_work_order_execution_closeout_id"])
    artifacts = [
        ("source_adapter_next_roadmap_work_order_execution_closeout_package", package),
        ("source_adapter_next_roadmap_work_order_execution_index", package["source_adapter_next_roadmap_work_order_execution_index"]),
        ("source_adapter_runtime_gui_controller_hardening_manifest", package["source_adapter_runtime_gui_controller_hardening_manifest"]),
        ("source_adapter_provider_execution_activation_manifest", package["source_adapter_provider_execution_activation_manifest"]),
        ("source_adapter_priority_fixture_pack_authoring_manifest", package["source_adapter_priority_fixture_pack_authoring_manifest"]),
        ("source_adapter_live_smoke_receipt_capture_manifest", package["source_adapter_live_smoke_receipt_capture_manifest"]),
        ("source_adapter_regular_regression_promotion_manifest", package["source_adapter_regular_regression_promotion_manifest"]),
        ("source_adapter_documentation_handoff_refresh_manifest", package["source_adapter_documentation_handoff_refresh_manifest"]),
        ("source_adapter_next_roadmap_execution_ready_handoff", package["source_adapter_next_roadmap_execution_ready_handoff"]),
        ("source_adapter_next_roadmap_work_order_execution_operator_summary", package["operator_summary"]),
    ]
    stored_files = []
    for role, payload in artifacts:
        stored_files.append(_write_json(output_path / f"{closeout_id}.{role}.json", payload))
    verification = verify_source_adapter_next_roadmap_work_order_execution_closeout(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_next_roadmap_work_order_execution_closeout_id": closeout_id,
        "next_roadmap_work_order_execution_closeout_status": package.get("next_roadmap_work_order_execution_closeout_status"),
        "output_file_count": len(stored_files),
        "work_order_execution_count": package["source_adapter_next_roadmap_work_order_execution_index"].get("work_order_execution_count", 0),
        "provider_activation_count": package["source_adapter_provider_execution_activation_manifest"].get("provider_activation_count", 0),
        "fixture_pack_count": package["source_adapter_priority_fixture_pack_authoring_manifest"].get("fixture_pack_count", 0),
        "stored_files": stored_files,
        "verification": verification,
    }
