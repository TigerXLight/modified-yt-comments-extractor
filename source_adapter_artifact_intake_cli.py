from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_artifact_intake import build_source_adapter_artifact_intake
from source_adapter_artifact_intake_store import store_source_adapter_artifact_intake


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a shared Adapter Artifact Intake package.")
    parser.add_argument("--capture-session-json", required=True, help="Adapter Capture Session package JSON.")
    parser.add_argument("--artifact-files-json", required=True, help="Explicit artifact file bindings JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for store artifacts.")
    parser.add_argument("--source-url", default="", help="Fallback source URL when receipts do not include one.")
    parser.add_argument("--operator-notes", default="", help="Optional notes copied into source artifact collections.")
    args = parser.parse_args(argv)

    capture_session = _load_json(args.capture_session_json)
    artifact_files = _load_json(args.artifact_files_json)
    package = build_source_adapter_artifact_intake(
        capture_session,
        artifact_files,
        source_url=args.source_url,
        operator_notes=args.operator_notes,
    )
    result = store_source_adapter_artifact_intake(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
