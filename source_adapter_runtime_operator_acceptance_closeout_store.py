from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_runtime_operator_acceptance_closeout_verifier import (
    verify_source_adapter_runtime_operator_acceptance_closeout,
)

SCHEMA_VERSION = "source_adapter_runtime_operator_acceptance_closeout_store_v1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(output_dir: Path, filename: str, value: Any) -> dict[str, Any]:
    data = _json_bytes(value)
    path = output_dir / filename
    path.write_bytes(data)
    import hashlib

    return {"filename": filename, "role": filename.rsplit(".", 1)[0].split(".", 1)[-1], "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_runtime_operator_acceptance_closeout(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    pkg = dict(package)
    bridge_id = str(pkg.get("source_adapter_runtime_operator_acceptance_closeout_id") or "source_adapter_runtime_operator_acceptance_closeout")
    outputs = {
        "source_adapter_runtime_operator_acceptance_closeout_package": pkg,
        "source_adapter_runtime_operator_acceptance_batch": pkg.get("source_adapter_runtime_operator_acceptance_batch", {}),
        "source_adapter_runtime_execution_contracts": pkg.get("source_adapter_runtime_execution_contracts", {}),
        "source_adapter_provider_execution_adapter_index": pkg.get("source_adapter_provider_execution_adapter_index", {}),
        "source_adapter_gui_controller_binding_manifest": pkg.get("source_adapter_gui_controller_binding_manifest", {}),
        "source_adapter_runtime_receipt_template_index": pkg.get("source_adapter_runtime_receipt_template_index", {}),
        "source_adapter_priority_fixture_pack_plan": pkg.get("source_adapter_priority_fixture_pack_plan", {}),
        "source_adapter_manual_live_smoke_acceptance_plan": pkg.get("source_adapter_manual_live_smoke_acceptance_plan", {}),
        "source_adapter_runtime_roadmap_closeout_index": pkg.get("source_adapter_runtime_roadmap_closeout_index", {}),
        "source_adapter_runtime_operator_acceptance_closeout_operator_summary": pkg.get("operator_summary", {}),
    }
    stored_files = []
    for role, value in outputs.items():
        stored_files.append(_write_json(output_path, f"{bridge_id}.{role}.json", value))
    verification = verify_source_adapter_runtime_operator_acceptance_closeout(pkg)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_runtime_operator_acceptance_closeout_id": bridge_id,
        "source_adapter_runtime_ui_provider_integration_bridge_id": pkg.get("source_adapter_runtime_ui_provider_integration_bridge_id", ""),
        "accepted_capability_count": pkg.get("accepted_capability_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
