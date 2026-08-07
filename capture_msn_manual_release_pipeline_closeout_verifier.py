from __future__ import annotations

import re
from typing import Any, Mapping

from capture_msn_manual_release_pipeline_closeout import (
    PIPELINE_STATUS_CLOSED,
    SCHEMA_VERSION,
    inspect_msn_manual_release_pipeline_closeout_safety,
)

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def verify_msn_manual_release_pipeline_closeout(packet: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if packet.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema_version_mismatch")
    if packet.get("pipeline_status") != PIPELINE_STATUS_CLOSED:
        issues.append("pipeline_not_closed")
    for key in ("queue_item_id", "release_id", "pipeline_closeout_id"):
        if not packet.get(key):
            issues.append(f"missing_{key}")

    missing_stages = list(packet.get("missing_stages") or [])
    if missing_stages:
        issues.append("missing_stage_coverage")

    for item in packet.get("stored_files", []) or []:
        if not _SHA_RE.match(str(item.get("sha256", ""))):
            issues.append(f"invalid_sha256:{item.get('role', 'unknown')}")
        if int(item.get("byte_count", 0) or 0) <= 0:
            issues.append(f"invalid_byte_count:{item.get('role', 'unknown')}")

    safety = inspect_msn_manual_release_pipeline_closeout_safety(packet)
    issues.extend(safety.get("issues", []))

    return {
        "schema_version": "msn_manual_release_pipeline_closeout_verifier_v1",
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "pipeline_closeout_id": packet.get("pipeline_closeout_id"),
        "queue_item_id": packet.get("queue_item_id"),
        "release_id": packet.get("release_id"),
    }


if __name__ == "__main__":
    from capture_msn_manual_release_pipeline_closeout import build_msn_manual_release_pipeline_closeout

    packet = build_msn_manual_release_pipeline_closeout(
        {
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "stored_files": [{"filename": "a.json", "role": "r", "sha256": "1" * 64, "byte_count": 1}],
        }
    )
    assert verify_msn_manual_release_pipeline_closeout(packet)["verified"]
    print("MSN manual release pipeline closeout verifier self-test passed.")
