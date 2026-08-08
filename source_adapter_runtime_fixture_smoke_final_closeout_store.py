from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_runtime_fixture_smoke_final_closeout_verifier import verify_source_adapter_runtime_fixture_smoke_final_closeout

SCHEMA_VERSION = "source_adapter_runtime_fixture_smoke_final_closeout_store_v1"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _write_json(output_dir: Path, filename: str, role: str, value: Any) -> dict[str, Any]:
    data = _stable_json(value).encode("utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_bytes(data)
    return {"role": role, "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_runtime_fixture_smoke_final_closeout(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    verification = verify_source_adapter_runtime_fixture_smoke_final_closeout(package)
    if not verification["verified"]:
        raise ValueError(f"runtime fixture/smoke final closeout package failed verification: {verification['issues']}")
    out = Path(output_dir)
    closeout_id = str(package["source_adapter_runtime_fixture_smoke_final_closeout_id"])
    stored = [
        _write_json(out, f"{closeout_id}.source_adapter_runtime_fixture_smoke_final_closeout_package.json", "source_adapter_runtime_fixture_smoke_final_closeout_package", package),
        _write_json(out, f"{closeout_id}.source_adapter_runtime_dry_run_receipt_batch.json", "source_adapter_runtime_dry_run_receipt_batch", package["source_adapter_runtime_dry_run_receipt_batch"]),
        _write_json(out, f"{closeout_id}.source_adapter_priority_fixture_execution_matrix.json", "source_adapter_priority_fixture_execution_matrix", package["source_adapter_priority_fixture_execution_matrix"]),
        _write_json(out, f"{closeout_id}.source_adapter_manual_live_smoke_runbook.json", "source_adapter_manual_live_smoke_runbook", package["source_adapter_manual_live_smoke_runbook"]),
        _write_json(out, f"{closeout_id}.source_adapter_runtime_fixture_smoke_operator_summary.json", "source_adapter_runtime_fixture_smoke_operator_summary", package["operator_summary"]),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_runtime_fixture_smoke_final_closeout_id": closeout_id,
        "capability_count": package.get("capability_count", 0),
        "output_file_count": len(stored),
        "stored_files": stored,
        "verification": verification,
    }


def main() -> None:
    import tempfile
    from source_adapter_runtime_fixture_smoke_final_closeout import build_source_adapter_runtime_fixture_smoke_final_closeout
    from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
    from source_adapter_runtime_controller_provider_closeout_test import fixture_runtime_operator_acceptance_closeout

    controller = build_source_adapter_runtime_controller_provider_closeout(fixture_runtime_operator_acceptance_closeout())
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(controller)
    with tempfile.TemporaryDirectory() as td:
        result = store_source_adapter_runtime_fixture_smoke_final_closeout(package, td)
    if result["output_file_count"] != 5:
        raise SystemExit(result)
    print("Source Adapter Runtime Fixture Smoke Final Closeout store self-test passed.")


if __name__ == "__main__":
    main()
