from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_operator_named_site_smoke_execution_closeout_verifier import verify_source_adapter_operator_named_site_smoke_execution_closeout

STORE_SCHEMA_VERSION = "source_adapter_operator_named_site_smoke_execution_closeout_store_v1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(output_dir: Path, closeout_id: str, role: str, value: Any) -> dict[str, Any]:
    filename = f"{closeout_id}.{role}.json"
    path = output_dir / filename
    payload = _canonical_bytes(value)
    path.write_bytes(payload)
    return {
        "role": role,
        "filename": filename,
        "path": str(path),
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def store_source_adapter_operator_named_site_smoke_execution_closeout(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    closeout_id = str(package.get("source_adapter_operator_named_site_smoke_execution_closeout_id") or "source_adapter_operator_named_site_smoke_execution_closeout")
    values = {
        "source_adapter_operator_named_site_smoke_execution_closeout_package": dict(package),
        "source_adapter_operator_named_site_local_fixture_execution_batch": package.get("source_adapter_operator_named_site_local_fixture_execution_batch") or {},
        "source_adapter_operator_named_site_manual_smoke_execution_batch": package.get("source_adapter_operator_named_site_manual_smoke_execution_batch") or {},
        "source_adapter_operator_named_site_receipt_acceptance_index": package.get("source_adapter_operator_named_site_receipt_acceptance_index") or {},
        "source_adapter_operator_named_site_roadmap_final_closeout": package.get("source_adapter_operator_named_site_roadmap_final_closeout") or {},
        "source_adapter_operator_named_site_smoke_execution_handoff": package.get("source_adapter_operator_named_site_smoke_execution_handoff") or {},
        "source_adapter_operator_named_site_smoke_execution_operator_summary": package.get("operator_summary") or {},
    }
    stored_files = [_write_json(output_path, closeout_id, role, value) for role, value in values.items()]
    verification = verify_source_adapter_operator_named_site_smoke_execution_closeout(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_operator_named_site_smoke_execution_closeout_id": closeout_id,
        "output_file_count": len(stored_files),
        "priority_site_pack_count": package.get("priority_site_pack_count"),
        "manual_smoke_execution_count": package.get("manual_smoke_execution_count"),
        "stored_files": stored_files,
        "verification": verification,
    }


def main() -> None:
    import tempfile
    from source_adapter_operator_named_site_smoke_execution_closeout import example_operator_named_site_smoke_execution_closeout_package

    with tempfile.TemporaryDirectory() as temp_dir:
        result = store_source_adapter_operator_named_site_smoke_execution_closeout(example_operator_named_site_smoke_execution_closeout_package(), temp_dir)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 7
        assert result["verification"]["verified"], result
    print("Source Adapter Operator Named Site Smoke Execution Closeout store self-test passed.")


if __name__ == "__main__":
    main()
