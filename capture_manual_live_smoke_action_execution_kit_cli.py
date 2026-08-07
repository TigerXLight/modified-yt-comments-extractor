from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from capture_manual_live_smoke_action_execution_kit import (
    build_manual_live_smoke_action_execution_kit,
)
from capture_manual_live_smoke_action_execution_kit_store import (
    manual_live_smoke_action_execution_kit_store_result_to_json,
    store_manual_live_smoke_action_execution_kit,
)


MANUAL_LIVE_SMOKE_ACTION_EXECUTION_KIT_CLI_SCHEMA_VERSION = "manual_live_smoke_action_execution_kit_cli_v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a runnable manual-live-smoke action execution kit.")
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--operator-intent", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--file-prefix", default="manual_live_smoke_action")
    parser.add_argument("--no-overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kit = build_manual_live_smoke_action_execution_kit(
        site_id=args.site_id,
        action_id=args.action_id,
        source_url=args.source_url,
        operator_intent=args.operator_intent,
        file_prefix=args.file_prefix,
    )
    result = store_manual_live_smoke_action_execution_kit(
        output_directory=args.output_directory,
        kit=kit,
        allow_overwrite=not args.no_overwrite,
    )
    response: dict[str, Any] = {
        "schema_version": MANUAL_LIVE_SMOKE_ACTION_EXECUTION_KIT_CLI_SCHEMA_VERSION,
        "kit": kit.to_dict(),
        "store_result": json.loads(manual_live_smoke_action_execution_kit_store_result_to_json(result)),
        "implementation_bundle": True,
        "local_only": True,
        "operator_approved_execution_supported": True,
        "full_local_path_serialized": False,
        "raw_media_payload_included": False,
        "credential_value_read": False,
        "completed_capture_claimed": False,
        "verified_capture_claimed": False,
    }
    sys.stdout.write(json.dumps(response, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
