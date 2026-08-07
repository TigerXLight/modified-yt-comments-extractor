from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_release_index_bridge import build_source_adapter_release_index_bridge
from source_adapter_release_index_bridge_store import store_source_adapter_release_index_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Release Index Bridge packages.")
    parser.add_argument("--approved-release-bridge-json", required=True, help="Adapter Approved Release Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--indexer-id", default="manual_indexer", help="Non-secret release indexer/operator identifier.")
    parser.add_argument("--release-index-profile", default="source_adapter_shared_release_index_v1", help="Deterministic shared release-index profile.")
    parser.add_argument("--release-note", action="append", default=[], help="Optional release-index note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.approved_release_bridge_json)
    package = build_source_adapter_release_index_bridge(
        bridge,
        indexer_id=args.indexer_id,
        release_index_profile=args.release_index_profile,
        release_notes=args.release_note,
    )
    result = store_source_adapter_release_index_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
