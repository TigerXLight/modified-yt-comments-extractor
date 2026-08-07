from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_capture_action_kit import output_documents
from source_adapter_capture_action_kit_verifier import verify_source_adapter_capture_action_kit

STORE_SCHEMA_VERSION = "source_adapter_capture_action_kit_store_v1"
_ROLE_SUFFIXES = {
    "source_adapter_capture_action_kit_package": "source_adapter_capture_action_kit_package.json",
    "source_adapter_capture_action_index": "source_adapter_capture_action_index.json",
    "source_adapter_capture_artifact_intake_templates": "source_adapter_capture_artifact_intake_templates.json",
    "source_adapter_capture_session_handoff": "source_adapter_capture_session_handoff.json",
    "source_adapter_capture_action_operator_summary": "source_adapter_capture_action_operator_summary.json",
}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def store_source_adapter_capture_action_kit(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    action_kit_id = str(package.get("source_adapter_capture_action_kit_id") or "source_adapter_capture_action_kit")
    stored_files: list[dict[str, Any]] = []
    for role, document in output_documents(package).items():
        filename = f"{action_kit_id}.{_ROLE_SUFFIXES[role]}"
        data = _json_bytes(document)
        path = out / filename
        path.write_bytes(data)
        stored_files.append(
            {
                "role": role,
                "filename": filename,
                "byte_count": len(data),
                "sha256": _sha256(data),
            }
        )
    verification = verify_source_adapter_capture_action_kit(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_capture_action_kit_id": action_kit_id,
        "source_adapter_capture_setup_id": package.get("source_adapter_capture_setup_id", ""),
        "adapter_count": package.get("adapter_count", 0),
        "action_kit_status": package.get("action_kit_status", ""),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
