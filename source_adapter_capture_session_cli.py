from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_capture_session import build_source_adapter_capture_session
from source_adapter_capture_session_store import store_source_adapter_capture_session


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a shared Adapter Capture Session package.")
    parser.add_argument("--action-kit-json", required=True, help="Adapter Capture Action Kit package JSON.")
    parser.add_argument("--artifact-receipts-json", required=True, help="Explicit operator artifact receipt metadata JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for store artifacts.")
    parser.add_argument("--operator-approval-id", default="", help="Optional approval identifier recorded in the session.")
    parser.add_argument("--session-notes", default="", help="Optional local notes for the session record.")
    args = parser.parse_args(argv)

    action_kit = _load_json(args.action_kit_json)
    receipts = _load_json(args.artifact_receipts_json)
    package = build_source_adapter_capture_session(
        action_kit,
        receipts,
        operator_approval_id=args.operator_approval_id,
        session_notes=args.session_notes,
    )
    result = store_source_adapter_capture_session(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
