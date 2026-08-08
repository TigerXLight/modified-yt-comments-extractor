from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_priority_fixture_regression_promotion import (
    SCHEMA_VERSION,
    build_source_adapter_priority_fixture_regression_promotion,
)
from source_adapter_priority_fixture_regression_promotion_verifier import verify_source_adapter_priority_fixture_regression_promotion

STORE_SCHEMA_VERSION = "source_adapter_priority_fixture_regression_promotion_store_v1"


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


def store_source_adapter_priority_fixture_regression_promotion(package_or_priority_fixture_pack_implementation: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    if package_or_priority_fixture_pack_implementation.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_priority_fixture_pack_implementation)
    else:
        package = build_source_adapter_priority_fixture_regression_promotion(package_or_priority_fixture_pack_implementation).as_dict()
    output_path = Path(output_dir)
    promotion_id = str(package["source_adapter_priority_fixture_regression_promotion_id"])
    artifacts = [
        ("source_adapter_priority_fixture_regression_promotion_package", package),
        ("source_adapter_priority_fixture_regression_queue", package["source_adapter_priority_fixture_regression_queue"]),
        ("source_adapter_gui_controller_call_site_installation_plan", package["source_adapter_gui_controller_call_site_installation_plan"]),
        ("source_adapter_named_site_smoke_operator_approval_gate", package["source_adapter_named_site_smoke_operator_approval_gate"]),
        ("source_adapter_priority_fixture_regression_promotion_handoff", package["source_adapter_priority_fixture_regression_promotion_handoff"]),
        ("source_adapter_priority_fixture_regression_promotion_operator_summary", package["operator_summary"]),
    ]
    stored_files = [_write_json(output_path / f"{promotion_id}.{role}.json", payload) for role, payload in artifacts]
    verification = verify_source_adapter_priority_fixture_regression_promotion(package)
    regression_queue = package["source_adapter_priority_fixture_regression_queue"]
    gui_plan = package["source_adapter_gui_controller_call_site_installation_plan"]
    smoke_gate = package["source_adapter_named_site_smoke_operator_approval_gate"]
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_priority_fixture_regression_promotion_id": promotion_id,
        "priority_fixture_regression_promotion_status": package.get("priority_fixture_regression_promotion_status"),
        "fixture_pack_count": regression_queue.get("fixture_pack_count", 0),
        "promoted_regression_queue_row_count": regression_queue.get("promoted_regression_queue_row_count", 0),
        "call_site_installation_row_count": gui_plan.get("call_site_installation_row_count", 0),
        "named_site_smoke_gate_row_count": smoke_gate.get("named_site_smoke_gate_row_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
