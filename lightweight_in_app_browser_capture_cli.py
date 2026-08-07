from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from lightweight_in_app_browser_capture import build_capture_package, load_json_file
from lightweight_in_app_browser_capture_store import store_capture_package


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared lightweight in-app browser capture package.")
    parser.add_argument("--adapter-json", required=True, help="Path to adapter binding/spec JSON.")
    parser.add_argument("--source-url", required=True, help="Explicit operator-supplied source URL.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated package/scripts/templates.")
    parser.add_argument("--job-label", default="operator_capture")
    parser.add_argument("--artifact", action="append", default=None, help="Requested artifact role. Repeatable.")
    parser.add_argument("--render-wait-ms", type=int, default=3000)
    parser.add_argument("--viewport", default="1365x768")
    parser.add_argument("--approve-token", default=None, help="Optional exact approval token for pre-approved package status.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    adapter = load_json_file(args.adapter_json)
    package = build_capture_package(
        adapter,
        args.source_url,
        job_label=args.job_label,
        requested_artifacts=args.artifact,
        render_wait_ms=args.render_wait_ms,
        viewport=args.viewport,
        approval_token=args.approve_token,
    )
    receipt = store_capture_package(package, Path(args.output_dir))
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
