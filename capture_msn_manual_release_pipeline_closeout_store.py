from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from capture_msn_manual_release_pipeline_closeout import (
    msn_manual_release_pipeline_closeout_to_json,
)

SCHEMA_VERSION = "msn_manual_release_pipeline_closeout_store_v1"


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return {
        "filename": path.name,
        "role": str(payload.get("role") or path.stem.rsplit(".", 1)[-1]),
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
    }


def store_msn_manual_release_pipeline_closeout(
    packet: Mapping[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    packet_id = str(packet.get("pipeline_closeout_id") or "msn_manual_release.pipeline_closeout")
    closeout_path = out_dir / f"{packet_id}.release_pipeline_closeout.json"
    transition_path = out_dir / f"{packet_id}.release_pipeline_transition_map.json"
    summary_path = out_dir / f"{packet_id}.release_pipeline_operator_summary.json"

    closeout_data = msn_manual_release_pipeline_closeout_to_json(packet).encode("utf-8")
    closeout_path.write_bytes(closeout_data)
    closeout_file = {
        "filename": closeout_path.name,
        "role": "msn_manual_release_pipeline_closeout",
        "sha256": hashlib.sha256(closeout_data).hexdigest(),
        "byte_count": len(closeout_data),
    }

    transition_file = _write_json(
        transition_path,
        {
            "role": "msn_manual_release_pipeline_transition_map",
            "schema_version": "msn_manual_release_pipeline_transition_map_v1",
            **dict(packet.get("transition_map") or {}),
        },
    )
    summary_file = _write_json(
        summary_path,
        {
            "role": "msn_manual_release_pipeline_operator_summary",
            "schema_version": "msn_manual_release_pipeline_operator_summary_v1",
            "pipeline_closeout_id": packet.get("pipeline_closeout_id"),
            "pipeline_status": packet.get("pipeline_status"),
            "queue_item_id": packet.get("queue_item_id"),
            "release_id": packet.get("release_id"),
            "operator_next_actions": packet.get("operator_next_actions", []),
        },
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "pipeline_closeout_id": packet.get("pipeline_closeout_id"),
        "queue_item_id": packet.get("queue_item_id"),
        "release_id": packet.get("release_id"),
        "output_file_count": 3,
        "stored_files": [closeout_file, transition_file, summary_file],
    }


if __name__ == "__main__":
    import tempfile
    from capture_msn_manual_release_pipeline_closeout import build_msn_manual_release_pipeline_closeout

    packet = build_msn_manual_release_pipeline_closeout(
        {"queue_item_id": "msn.queue", "release_id": "msn.queue.release.1234", "stored_files": []}
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = store_msn_manual_release_pipeline_closeout(packet, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 3
    print("MSN manual release pipeline closeout store self-test passed.")
