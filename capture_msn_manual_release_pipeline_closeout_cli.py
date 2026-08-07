from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from capture_msn_manual_release_pipeline_closeout import build_msn_manual_release_pipeline_closeout
from capture_msn_manual_release_pipeline_closeout_store import store_msn_manual_release_pipeline_closeout
from capture_msn_manual_release_pipeline_closeout_verifier import verify_msn_manual_release_pipeline_closeout


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MSN manual release pipeline closeout packet.")
    parser.add_argument("--release-section-closeout-json", required=True)
    parser.add_argument("--release-export-bundle-store-json")
    parser.add_argument("--release-index-store-json")
    parser.add_argument("--approved-release-package-store-json")
    parser.add_argument("--operator-label", default="manual_operator")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    packet = build_msn_manual_release_pipeline_closeout(
        _read_json(args.release_section_closeout_json),
        release_export_bundle_store_report=_read_json(args.release_export_bundle_store_json)
        if args.release_export_bundle_store_json
        else None,
        release_index_store_report=_read_json(args.release_index_store_json) if args.release_index_store_json else None,
        approved_release_package_store_report=_read_json(args.approved_release_package_store_json)
        if args.approved_release_package_store_json
        else None,
        operator_label=args.operator_label,
    )
    verification = verify_msn_manual_release_pipeline_closeout(packet)
    result = store_msn_manual_release_pipeline_closeout(packet, args.out_dir)
    result["verification"] = verification
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if verification["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
