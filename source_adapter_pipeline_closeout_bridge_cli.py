from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_pipeline_closeout_bridge import build_source_adapter_pipeline_closeout_bridge
from source_adapter_pipeline_closeout_bridge_store import store_source_adapter_pipeline_closeout_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Pipeline Closeout Bridge packages.")
    parser.add_argument("--archive-review-bridge-json", required=True, help="Adapter Archive Review Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--operator-note", action="append", default=[], help="Optional closeout note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.archive_review_bridge_json)
    package = build_source_adapter_pipeline_closeout_bridge(bridge, operator_notes=args.operator_note)
    result = store_source_adapter_pipeline_closeout_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
