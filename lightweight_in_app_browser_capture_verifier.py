from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lightweight_in_app_browser_capture import verify_capture_package


def verify_capture_package_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return verify_capture_package(data)


def verify_store_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if receipt.get("schema_version") != "lightweight_in_app_browser_capture_store_v1":
        issues.append("unexpected store schema_version")
    if receipt.get("store_status") != "STORED":
        issues.append("store_status must be STORED")
    if not receipt.get("package_id"):
        issues.append("package_id is required")
    roles = {item.get("role") for item in receipt.get("stored_files") or []}
    required = {
        "lightweight_browser_capture_package",
        "lightweight_browser_launch_script",
        "lightweight_browser_artifact_manifest_template",
        "lightweight_browser_capture_store_receipt",
    }
    missing = sorted(required - roles)
    if missing:
        issues.append("missing stored roles: " + ", ".join(missing))
    if (receipt.get("verification") or {}).get("verified") is not True:
        issues.append("embedded package verification must be true")
    return {
        "schema_version": "lightweight_in_app_browser_capture_store_verifier_v1",
        "package_id": receipt.get("package_id"),
        "browser_job_id": receipt.get("browser_job_id"),
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def verify_store_receipt_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return verify_store_receipt(data)
