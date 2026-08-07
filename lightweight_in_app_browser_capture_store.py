from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from lightweight_in_app_browser_capture import verify_capture_package

STORE_SCHEMA_VERSION = "lightweight_in_app_browser_capture_store_v1"


def _safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", ".", str(value)).strip("._-")
    return text or "lightweight_browser_capture"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"


def _write_bytes(path: Path, data: bytes, role: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "role": role,
        "filename": path.name,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def store_capture_package(package: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    verification = verify_capture_package(package)
    if not verification["verified"]:
        raise ValueError("capture package failed verification: " + "; ".join(verification["issues"]))
    out = Path(output_dir)
    base = _safe_name(package["package_id"])
    files = []
    files.append(_write_bytes(out / f"{base}.capture_package.json", _json_bytes(package), "lightweight_browser_capture_package"))
    files.append(_write_bytes(out / f"{base}.launch_approved_capture.cmd", package["windows_launch_script"].encode("utf-8"), "lightweight_browser_launch_script"))
    files.append(_write_bytes(out / f"{base}.artifact_manifest_template.json", _json_bytes(package["artifact_manifest_template"]), "lightweight_browser_artifact_manifest_template"))
    snippets = package.get("devtools_snippets") or {}
    for name, source in sorted(snippets.items()):
        files.append(_write_bytes(out / f"{base}.{_safe_name(name)}", str(source).encode("utf-8"), f"lightweight_browser_{_safe_name(name)}"))
    receipt = {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "package_id": package["package_id"],
        "browser_job_id": package["browser_job_id"],
        "adapter_id": package["adapter_id"],
        "output_file_count": len(files),
        "stored_files": files,
        "verification": verification,
    }
    receipt_bytes = _json_bytes(receipt)
    receipt_file = _write_bytes(out / f"{base}.store_receipt.json", receipt_bytes, "lightweight_browser_capture_store_receipt")
    receipt["output_file_count"] += 1
    receipt["stored_files"].append(receipt_file)
    # Rewrite receipt so the on-disk copy includes its own entry.
    (out / f"{base}.store_receipt.json").write_bytes(_json_bytes(receipt))
    return receipt
