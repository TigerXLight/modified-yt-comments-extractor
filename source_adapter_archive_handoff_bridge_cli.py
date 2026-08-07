from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_archive_handoff_bridge import build_source_adapter_archive_handoff_bridge
from source_adapter_archive_handoff_bridge_store import store_source_adapter_archive_handoff_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Archive Handoff Bridge packages.")
    parser.add_argument("--release-audit-bridge-json", required=True, help="Adapter Release Audit Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--archive-provider", action="append", default=[], help="Archive provider id; may be repeated.")
    parser.add_argument("--operator-id", default="manual_archive_operator", help="Non-secret archive operator identifier.")
    parser.add_argument("--handoff-note", action="append", default=[], help="Optional archive handoff note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.release_audit_bridge_json)
    package = build_source_adapter_archive_handoff_bridge(
        bridge,
        archive_providers=args.archive_provider or None,
        operator_id=args.operator_id,
        handoff_notes=args.handoff_note,
    )
    result = store_source_adapter_archive_handoff_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
