from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_release_audit_bridge import build_source_adapter_release_audit_bridge
from source_adapter_release_audit_bridge_store import store_source_adapter_release_audit_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Release Audit Bridge packages.")
    parser.add_argument("--release-index-bridge-json", required=True, help="Adapter Release Index Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--auditor-id", default="manual_auditor", help="Non-secret release auditor/operator identifier.")
    parser.add_argument("--audit-profile", default="source_adapter_shared_release_audit_v1", help="Deterministic shared release-audit profile.")
    parser.add_argument("--audit-note", action="append", default=[], help="Optional release-audit note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.release_index_bridge_json)
    package = build_source_adapter_release_audit_bridge(
        bridge,
        auditor_id=args.auditor_id,
        audit_profile=args.audit_profile,
        audit_notes=args.audit_note,
    )
    result = store_source_adapter_release_audit_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
