from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_evidence_queue_bridge import build_source_adapter_evidence_queue_bridge
from source_adapter_evidence_queue_bridge_store import store_source_adapter_evidence_queue_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Evidence Queue Bridge packages.")
    parser.add_argument("--total-export-bridge-json", required=True, help="Adapter Total Export Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--queue-profile", default="source_adapter_shared_v1", help="Deterministic shared evidence queue profile.")
    parser.add_argument("--queue-note", action="append", default=[], help="Optional queue note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.total_export_bridge_json)
    package = build_source_adapter_evidence_queue_bridge(bridge, queue_profile=args.queue_profile, queue_notes=args.queue_note)
    result = store_source_adapter_evidence_queue_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
