from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_next_roadmap_section_selection_closeout import (
    SCHEMA_VERSION as PACKAGE_SCHEMA_VERSION,
    STATUS,
    build_source_adapter_next_roadmap_section_selection_closeout,
)
from source_adapter_next_roadmap_section_selection_closeout_verifier import verify_source_adapter_next_roadmap_section_selection_closeout

STORE_SCHEMA_VERSION = "source_adapter_next_roadmap_section_selection_closeout_store_v1"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(output_dir: Path, stem: str, role: str, value: Mapping[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{stem}.{role}.json"
    path = output_dir / filename
    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    data = text.encode("utf-8")
    path.write_bytes(data)
    return {
        "role": role,
        "filename": filename,
        "path": str(path),
        "byte_count": len(data),
        "sha256": sha256_text(text),
    }


def store_source_adapter_next_roadmap_section_selection_closeout(
    package: Mapping[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    if package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        raise ValueError("unexpected next roadmap section selection closeout package schema")
    output_path = Path(output_dir)
    closeout_id = str(package.get("source_adapter_next_roadmap_section_selection_closeout_id") or "source_adapter_next_roadmap_section_selection_closeout")
    stored_files = [
        _write_json(output_path, closeout_id, "source_adapter_next_roadmap_section_selection_closeout_package", package),
        _write_json(output_path, closeout_id, "source_adapter_next_roadmap_section_selection_index", package.get("source_adapter_next_roadmap_section_selection_index") or {}),
        _write_json(output_path, closeout_id, "source_adapter_next_roadmap_work_order_manifest", package.get("source_adapter_next_roadmap_work_order_manifest") or {}),
        _write_json(output_path, closeout_id, "source_adapter_next_roadmap_codex_prompt_queue", package.get("source_adapter_next_roadmap_codex_prompt_queue") or {}),
        _write_json(output_path, closeout_id, "source_adapter_next_roadmap_regression_command_manifest", package.get("source_adapter_next_roadmap_regression_command_manifest") or {}),
        _write_json(output_path, closeout_id, "source_adapter_next_roadmap_ready_handoff", package.get("source_adapter_next_roadmap_ready_handoff") or {}),
        _write_json(output_path, closeout_id, "source_adapter_next_roadmap_section_selection_operator_summary", package.get("operator_summary") or {}),
    ]
    verification = verify_source_adapter_next_roadmap_section_selection_closeout(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_next_roadmap_section_selection_closeout_id": closeout_id,
        "next_roadmap_section_selection_closeout_status": package.get("next_roadmap_section_selection_closeout_status"),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }


def main() -> None:
    from tempfile import TemporaryDirectory
    from source_adapter_release_regression_next_roadmap_closeout import example_release_regression_next_roadmap_closeout_package

    with TemporaryDirectory() as tmp:
        package = build_source_adapter_next_roadmap_section_selection_closeout(example_release_regression_next_roadmap_closeout_package()).as_dict()
        result = store_source_adapter_next_roadmap_section_selection_closeout(package, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 7
        assert result["verification"]["verified"] is True
        assert package["next_roadmap_section_selection_closeout_status"] == STATUS
    print("Source Adapter Next Roadmap Section Selection Closeout store self-test passed.")


if __name__ == "__main__":
    main()
