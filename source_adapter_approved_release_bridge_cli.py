from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_approved_release_bridge import build_source_adapter_approved_release_bridge
from source_adapter_approved_release_bridge_store import store_source_adapter_approved_release_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Approved Release Bridge packages.")
    parser.add_argument("--evidence-review-bridge-json", required=True, help="Adapter Evidence Review Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--releaser-id", default="manual_releaser", help="Non-secret releaser/operator identifier.")
    parser.add_argument("--release-profile", default="source_adapter_shared_approved_release_v1", help="Deterministic shared approved-release profile.")
    parser.add_argument("--release-note", action="append", default=[], help="Optional release note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.evidence_review_bridge_json)
    package = build_source_adapter_approved_release_bridge(
        bridge,
        releaser_id=args.releaser_id,
        release_profile=args.release_profile,
        release_notes=args.release_note,
    )
    result = store_source_adapter_approved_release_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
