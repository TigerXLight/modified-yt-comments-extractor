from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from capture_manual_live_smoke_observation_packet import (
    build_capture_manual_live_smoke_observation_packet,
)
from capture_manual_live_smoke_observation_packet_store import (
    capture_manual_live_smoke_observation_packet_store_result_to_json,
    write_capture_manual_live_smoke_observation_packet,
)


CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_STORE_CLI_SCHEMA_VERSION = (
    "capture_manual_live_smoke_observation_packet_store_cli_v1"
)


def _load_json_file(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _observations_from_json(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        observations = value
    elif isinstance(value, dict) and isinstance(value.get("observations"), list):
        observations = value["observations"]
    elif isinstance(value, dict):
        observations = [value]
    else:
        raise ValueError("observations JSON must be an object, an object with observations, or a list")
    safe: list[dict[str, Any]] = []
    for index, item in enumerate(observations, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"observation {index} must be a JSON object")
        safe.append(item)
    return safe


def run_capture_manual_live_smoke_observation_packet_store_cli(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Build and persist a metadata-only manual live smoke observation packet."
    )
    parser.add_argument("--observations-json", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--packet-id", default="manual-live-smoke-observation-packet")
    parser.add_argument("--no-overwrite", action="store_true")
    args = parser.parse_args(argv)
    observations = _observations_from_json(_load_json_file(args.observations_json))
    packet = build_capture_manual_live_smoke_observation_packet(
        observations,
        packet_id=args.packet_id,
    )
    store_result = write_capture_manual_live_smoke_observation_packet(
        packet,
        args.output_directory,
        allow_overwrite=not args.no_overwrite,
    )
    payload = {
        "schema_version": CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_STORE_CLI_SCHEMA_VERSION,
        "packet": packet.to_dict(),
        "store_result": store_result.to_dict(),
        "metadata_only": True,
        "local_only": True,
        "output_directory_selected_by_user": True,
        "live_network_request_performed_by_tool": False,
        "browser_automation_performed_by_tool": False,
        "archive_submission_performed_by_tool": False,
        "media_download_performed_by_tool": False,
        "credential_value_read": False,
        "secret_value_recorded": False,
        "raw_media_payload_included": False,
        "full_local_path_serialized": False,
        "completed_capture_claimed": False,
        "verified_capture_claimed": False,
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_capture_manual_live_smoke_observation_packet_store_cli())
