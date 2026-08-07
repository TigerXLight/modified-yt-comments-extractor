from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from capture_manual_live_smoke_action_artifact_collect import (
    collect_manual_live_smoke_action_observation_draft,
    manual_live_smoke_action_observation_draft_to_json,
)
from capture_manual_live_smoke_observation_packet import (
    build_capture_manual_live_smoke_observation_packet,
)
from capture_manual_live_smoke_observation_packet_store import (
    write_capture_manual_live_smoke_observation_packet,
)


MANUAL_LIVE_SMOKE_ACTION_ARTIFACT_COLLECT_CLI_SCHEMA_VERSION = "manual_live_smoke_action_artifact_collect_cli_v1"


def _write_json(path: str | Path, text: str, *, allow_overwrite: bool) -> dict[str, Any]:
    destination = Path(path)
    if destination.exists() and not allow_overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {destination.name}")
    payload = text.encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return {
        "file_name": destination.name,
        "role": "manual_live_smoke_action_observation_draft",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_count": len(payload),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect explicit operator-supplied manual-live-smoke artifacts into safe observation metadata."
    )
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--display-name", default="")
    parser.add_argument("--operator-summary", required=True)
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Explicit artifact mapping in role=file form. Repeat for multiple artifacts.",
    )
    parser.add_argument("--output-json", default="")
    parser.add_argument("--packet-output-dir", default="")
    parser.add_argument("--packet-id", default="manual-live-smoke-action-observation-packet")
    parser.add_argument("--no-overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.artifact:
        print("at least one --artifact role=file argument is required", file=sys.stderr)
        return 2
    draft = collect_manual_live_smoke_action_observation_draft(
        site_id=args.site_id,
        action_id=args.action_id,
        display_name=args.display_name or None,
        operator_summary=args.operator_summary,
        artifacts=args.artifact,
    )
    draft_json = manual_live_smoke_action_observation_draft_to_json(draft)
    response: dict[str, Any] = {
        "schema_version": MANUAL_LIVE_SMOKE_ACTION_ARTIFACT_COLLECT_CLI_SCHEMA_VERSION,
        "draft": draft.to_dict(),
        "metadata_only": True,
        "local_only": True,
        "operator_supplied_files_read": True,
        "file_movement_performed_by_tool": False,
        "user_folder_scan_performed_by_tool": False,
        "full_local_path_serialized": False,
        "raw_media_payload_included": False,
        "completed_capture_claimed": False,
        "verified_capture_claimed": False,
    }
    if args.output_json:
        response["draft_store_result"] = _write_json(
            args.output_json,
            draft_json,
            allow_overwrite=not args.no_overwrite,
        )
    if args.packet_output_dir:
        packet = build_capture_manual_live_smoke_observation_packet(
            [draft.to_observation_dict()],
            packet_id=args.packet_id,
        )
        store_result = write_capture_manual_live_smoke_observation_packet(
            packet,
            args.packet_output_dir,
            allow_overwrite=not args.no_overwrite,
        )
        response["observation_packet"] = packet.to_dict()
        response["packet_store_result"] = store_result.to_dict()
    sys.stdout.write(json.dumps(response, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
