from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from capture_manual_live_smoke_observation_section_closeout import (
    build_capture_manual_live_smoke_observation_section_closeout_report,
)
from capture_manual_live_smoke_observation_section_closeout_store import (
    capture_manual_live_smoke_observation_section_closeout_store_result_to_json,
    write_capture_manual_live_smoke_observation_section_closeout_report,
)


CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_SECTION_CLOSEOUT_STORE_CLI_SCHEMA_VERSION = (
    "capture_manual_live_smoke_observation_section_closeout_store_cli_v1"
)


def _load_json_file(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_capture_manual_live_smoke_observation_section_closeout_store_cli(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Build and persist a metadata-only manual live smoke observation section closeout report."
    )
    parser.add_argument("--artifact-json", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--no-overwrite", action="store_true")
    args = parser.parse_args(argv)
    artifact = _load_json_file(args.artifact_json)
    report = build_capture_manual_live_smoke_observation_section_closeout_report(artifact)
    store_result = write_capture_manual_live_smoke_observation_section_closeout_report(
        report,
        args.output_directory,
        allow_overwrite=not args.no_overwrite,
    )
    payload = {
        "schema_version": CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_SECTION_CLOSEOUT_STORE_CLI_SCHEMA_VERSION,
        "closeout_report": report.to_dict(),
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
    raise SystemExit(run_capture_manual_live_smoke_observation_section_closeout_store_cli())
