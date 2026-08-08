from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_priority_site_pack_execution_closeout_verifier import verify_source_adapter_priority_site_pack_execution_closeout

STORE_SCHEMA_VERSION = "source_adapter_priority_site_pack_execution_closeout_store_v1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(output_dir: Path, filename: str, role: str, value: Any) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(value)
    path = output_dir / filename
    path.write_bytes(data)
    return {
        "role": role,
        "filename": filename,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def store_source_adapter_priority_site_pack_execution_closeout(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    closeout_id = str(package.get("source_adapter_priority_site_pack_execution_closeout_id") or "source_adapter_priority_site_pack_execution_closeout")
    stored_files = [
        _write_json(output_path, f"{closeout_id}.source_adapter_priority_site_pack_execution_closeout_package.json", "source_adapter_priority_site_pack_execution_closeout_package", package),
        _write_json(output_path, f"{closeout_id}.source_adapter_priority_site_fixture_pack_matrix.json", "source_adapter_priority_site_fixture_pack_matrix", package.get("source_adapter_priority_site_fixture_pack_matrix", {})),
        _write_json(output_path, f"{closeout_id}.source_adapter_priority_site_local_fixture_run_plan.json", "source_adapter_priority_site_local_fixture_run_plan", package.get("source_adapter_priority_site_local_fixture_run_plan", {})),
        _write_json(output_path, f"{closeout_id}.source_adapter_priority_site_manual_smoke_plan.json", "source_adapter_priority_site_manual_smoke_plan", package.get("source_adapter_priority_site_manual_smoke_plan", {})),
        _write_json(output_path, f"{closeout_id}.source_adapter_priority_site_pack_execution_operator_summary.json", "source_adapter_priority_site_pack_execution_operator_summary", package.get("operator_summary", {})),
    ]
    verification = verify_source_adapter_priority_site_pack_execution_closeout(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_priority_site_pack_execution_closeout_id": closeout_id,
        "priority_site_pack_count": package.get("priority_site_pack_count", 0),
        "manual_smoke_row_count": package.get("manual_smoke_row_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }


def main() -> None:
    import tempfile
    from source_adapter_priority_site_pack_execution_closeout import example_priority_site_pack_execution_closeout_package

    with tempfile.TemporaryDirectory() as temp_dir:
        result = store_source_adapter_priority_site_pack_execution_closeout(example_priority_site_pack_execution_closeout_package(), temp_dir)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"]
    print("Source Adapter Priority Site Pack Execution Closeout store self-test passed.")


if __name__ == "__main__":
    main()
