from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_roadmap_audit_final_closeout_verifier import verify_source_adapter_roadmap_audit_final_closeout

STORE_SCHEMA_VERSION = "source_adapter_roadmap_audit_final_closeout_store_v1"


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    import hashlib

    data = _json_bytes(value)
    path.write_bytes(data)
    return {
        "filename": path.name,
        "role": path.name.split(".", 1)[1].removesuffix(".json") if "." in path.name else path.stem,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def store_source_adapter_roadmap_audit_final_closeout(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    closeout_id = str(package.get("source_adapter_roadmap_audit_final_closeout_id") or "source_adapter.roadmap_audit_final_closeout")
    artifacts = [
        ("source_adapter_roadmap_audit_final_closeout_package", dict(package)),
        ("source_adapter_roadmap_completion_index", package.get("source_adapter_roadmap_completion_index") or {}),
        ("source_adapter_regression_promotion_manifest", package.get("source_adapter_regression_promotion_manifest") or {}),
        ("source_adapter_live_execution_acceptance_manifest", package.get("source_adapter_live_execution_acceptance_manifest") or {}),
        ("source_adapter_final_release_handoff", package.get("source_adapter_final_release_handoff") or {}),
    ]
    stored = []
    for role, value in artifacts:
        stored.append(_write_json(out / f"{closeout_id}.{role}.json", value))
    verification = verify_source_adapter_roadmap_audit_final_closeout(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED" if verification["verified"] else "STORED_WITH_VERIFICATION_ISSUES",
        "source_adapter_roadmap_audit_final_closeout_id": closeout_id,
        "output_file_count": len(stored),
        "closed_section_count": verification.get("closed_section_count"),
        "promotion_row_count": verification.get("promotion_row_count"),
        "live_execution_row_count": verification.get("live_execution_row_count"),
        "stored_files": stored,
        "verification": verification,
    }


def main() -> None:
    import tempfile
    from source_adapter_roadmap_audit_final_closeout import example_roadmap_audit_final_closeout_package

    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_roadmap_audit_final_closeout(example_roadmap_audit_final_closeout_package(), tmp)
        assert result["output_file_count"] == 5
        assert result["verification"]["verified"], result
    print("Source Adapter Roadmap Audit Final Closeout store self-test passed.")


if __name__ == "__main__":
    main()
