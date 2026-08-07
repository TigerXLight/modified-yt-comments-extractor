from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from source_adapter_capture_setup import build_source_adapter_capture_setup, load_json, write_json
from source_adapter_capture_setup_verifier import verify_source_adapter_capture_setup_package

STORE_SCHEMA_VERSION = "source_adapter_capture_setup_store_v1"


def _json_file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def store_source_adapter_capture_setup(
    source_selection_package: Mapping[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    package = build_source_adapter_capture_setup(source_selection_package)
    capture_setup_id = str(package["source_adapter_capture_setup_id"])
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    outputs: list[tuple[str, Mapping[str, Any]]] = [
        ("source_adapter_capture_setup_package", package),
        ("source_adapter_capture_setup_plan", package["capture_setup_plan"]),
        ("source_adapter_capture_artifact_intake_plan", package["artifact_intake_plan"]),
        ("source_adapter_lightweight_browser_capture_setup_handoff", package["lightweight_browser_capture_setup_handoff"]),
        ("source_adapter_capture_setup_operator_summary", package["operator_summary"]),
    ]
    stored_files: list[dict[str, Any]] = []
    for role, data in outputs:
        filename = f"{capture_setup_id}.{role}.json"
        target = root / filename
        write_json(target, data)
        stored_files.append(
            {
                "role": role,
                "filename": filename,
                "byte_count": target.stat().st_size,
                "sha256": _json_file_digest(target),
            }
        )

    verification = verify_source_adapter_capture_setup_package(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_capture_setup_id": capture_setup_id,
        "source_adapter_source_selection_id": package.get("source_adapter_source_selection_id", ""),
        "capture_setup_status": package.get("capture_setup_status", ""),
        "adapter_count": package.get("adapter_count", 0),
        "setup_count": package.get("setup_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }


def store_source_adapter_capture_setup_from_file(
    source_selection_package_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    return store_source_adapter_capture_setup(load_json(source_selection_package_path), output_dir)


if __name__ == "__main__":
    import tempfile

    from source_adapter_capture_setup import demo_source_selection_package

    with tempfile.TemporaryDirectory() as tmpdir:
        summary = store_source_adapter_capture_setup(demo_source_selection_package(), tmpdir)
        assert summary["store_status"] == "STORED", summary
        assert summary["output_file_count"] == 5, summary
        assert summary["verification"]["verified"] is True, summary
    print("Source Adapter Capture Setup store self-test passed.")
