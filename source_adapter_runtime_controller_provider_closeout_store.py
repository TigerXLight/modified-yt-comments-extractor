from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_runtime_controller_provider_closeout_verifier import verify_source_adapter_runtime_controller_provider_closeout

SCHEMA_VERSION = "source_adapter_runtime_controller_provider_closeout_store_v1"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _write_json(output_dir: Path, filename: str, role: str, value: Any) -> dict[str, Any]:
    data = _stable_json(value).encode("utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_bytes(data)
    return {"role": role, "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_runtime_controller_provider_closeout(
    package: Mapping[str, Any], output_dir: str | Path
) -> dict[str, Any]:
    verification = verify_source_adapter_runtime_controller_provider_closeout(package)
    if not verification["verified"]:
        raise ValueError(f"runtime controller/provider closeout package failed verification: {verification['issues']}")
    out = Path(output_dir)
    closeout_id = str(package["source_adapter_runtime_controller_provider_closeout_id"])
    stored = [
        _write_json(out, f"{closeout_id}.source_adapter_runtime_controller_provider_closeout_package.json", "source_adapter_runtime_controller_provider_closeout_package", package),
        _write_json(out, f"{closeout_id}.source_adapter_runtime_controller_install_manifest.json", "source_adapter_runtime_controller_install_manifest", package["source_adapter_runtime_controller_install_manifest"]),
        _write_json(out, f"{closeout_id}.source_adapter_runtime_provider_execution_registry.json", "source_adapter_runtime_provider_execution_registry", package["source_adapter_runtime_provider_execution_registry"]),
        _write_json(out, f"{closeout_id}.source_adapter_runtime_dispatch_table.json", "source_adapter_runtime_dispatch_table", package["source_adapter_runtime_dispatch_table"]),
        _write_json(out, f"{closeout_id}.source_adapter_runtime_controller_provider_operator_summary.json", "source_adapter_runtime_controller_provider_operator_summary", package["operator_summary"]),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_runtime_controller_provider_closeout_id": closeout_id,
        "capability_count": package.get("capability_count", 0),
        "output_file_count": len(stored),
        "stored_files": stored,
        "verification": verification,
    }


def main() -> None:
    import tempfile
    from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
    from source_adapter_runtime_operator_acceptance_closeout import build_source_adapter_runtime_operator_acceptance_closeout
    from source_adapter_runtime_operator_acceptance_closeout_test import fixture_runtime_ui_provider_integration_bridge

    accepted = build_source_adapter_runtime_operator_acceptance_closeout(fixture_runtime_ui_provider_integration_bridge())
    package = build_source_adapter_runtime_controller_provider_closeout(accepted)
    with tempfile.TemporaryDirectory() as td:
        result = store_source_adapter_runtime_controller_provider_closeout(package, td)
    if result["output_file_count"] != 5:
        raise SystemExit(result)
    print("Source Adapter Runtime Controller Provider Closeout store self-test passed.")


if __name__ == "__main__":
    main()
