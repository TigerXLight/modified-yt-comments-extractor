from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_regression_queue_runtime_wiring import (
    SCHEMA_VERSION,
    build_source_adapter_regression_queue_runtime_wiring,
)
from source_adapter_regression_queue_runtime_wiring_verifier import verify_source_adapter_regression_queue_runtime_wiring
from source_adapter_runtime_gui_provider_implementation import example_runtime_gui_provider_implementation_package

STORE_SCHEMA_VERSION = "source_adapter_regression_queue_runtime_wiring_store_v1"


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


def store_source_adapter_regression_queue_runtime_wiring(package_or_promotion: Mapping[str, Any], output_dir: str | Path, runtime_gui_provider_implementation_package: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if package_or_promotion.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_promotion)
    else:
        package = build_source_adapter_regression_queue_runtime_wiring(
            package_or_promotion,
            runtime_gui_provider_implementation_package or example_runtime_gui_provider_implementation_package(),
        ).as_dict()
    output_path = Path(output_dir)
    wiring_id = str(package["source_adapter_regression_queue_runtime_wiring_id"])
    artifacts = [
        ("source_adapter_regression_queue_runtime_wiring_package", package),
        ("source_adapter_local_regression_runner_queue_installation", package["source_adapter_local_regression_runner_queue_installation"]),
        ("source_adapter_runtime_controller_provider_expanded_binding_matrix", package["source_adapter_runtime_controller_provider_expanded_binding_matrix"]),
        ("source_adapter_gui_controller_call_site_runtime_wiring", package["source_adapter_gui_controller_call_site_runtime_wiring"]),
        ("source_adapter_local_regression_acceptance_receipt_batch", package["source_adapter_local_regression_acceptance_receipt_batch"]),
        ("source_adapter_named_site_smoke_gate_carry_forward", package["source_adapter_named_site_smoke_gate_carry_forward"]),
        ("source_adapter_regression_queue_runtime_wiring_handoff", package["source_adapter_regression_queue_runtime_wiring_handoff"]),
        ("source_adapter_regression_queue_runtime_wiring_operator_summary", package["operator_summary"]),
    ]
    stored_files = [_write_json(output_path / f"{wiring_id}.{role}.json", payload) for role, payload in artifacts]
    verification = verify_source_adapter_regression_queue_runtime_wiring(package)
    local_runner_queue = package["source_adapter_local_regression_runner_queue_installation"]
    expanded_bindings = package["source_adapter_runtime_controller_provider_expanded_binding_matrix"]
    gui_wiring = package["source_adapter_gui_controller_call_site_runtime_wiring"]
    acceptance_receipts = package["source_adapter_local_regression_acceptance_receipt_batch"]
    smoke_gate = package["source_adapter_named_site_smoke_gate_carry_forward"]
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_regression_queue_runtime_wiring_id": wiring_id,
        "regression_queue_runtime_wiring_status": package.get("regression_queue_runtime_wiring_status"),
        "local_runner_queue_row_count": local_runner_queue.get("local_runner_queue_row_count", 0),
        "expanded_binding_row_count": expanded_bindings.get("expanded_binding_row_count", 0),
        "call_site_wiring_row_count": gui_wiring.get("call_site_wiring_row_count", 0),
        "acceptance_receipt_row_count": acceptance_receipts.get("acceptance_receipt_row_count", 0),
        "named_site_smoke_gate_row_count": smoke_gate.get("named_site_smoke_gate_row_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
