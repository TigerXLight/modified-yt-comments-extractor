from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_pipeline_closeout import build_source_pipeline_closeout, read_json
from source_pipeline_closeout_store import store_source_pipeline_closeout
from source_pipeline_closeout_verifier import verify_source_pipeline_closeout


def _print(data: dict[str, Any]) -> None:
    print(json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a shared source pipeline closeout package from archive review records.")
    parser.add_argument("--archive-review-package", required=True, help="Path to a source_archive_review_v1 package JSON.")
    parser.add_argument("--archive-review-decision", help="Optional source archive review decision JSON.")
    parser.add_argument("--archive-review-closeout", help="Optional source archive review closeout JSON.")
    parser.add_argument("--out-dir", help="Write deterministic closeout artifacts to this directory.")
    parser.add_argument("--store", action="store_true", help="Persist closeout artifacts instead of printing the in-memory bundle.")
    parser.add_argument("--verify", action="store_true", help="Verify the generated closeout bundle/store output.")
    args = parser.parse_args(argv)

    package = read_json(args.archive_review_package)
    decision = read_json(args.archive_review_decision) if args.archive_review_decision else None
    closeout = read_json(args.archive_review_closeout) if args.archive_review_closeout else None

    if args.store:
        if not args.out_dir:
            parser.error("--store requires --out-dir")
        result = store_source_pipeline_closeout(
            package,
            out_dir=Path(args.out_dir),
            archive_review_decision=decision,
            archive_review_closeout=closeout,
            verify=args.verify,
        )
    else:
        result = build_source_pipeline_closeout(
            package,
            archive_review_decision=decision,
            archive_review_closeout=closeout,
        )
        if args.verify:
            result = {**result, "verification": verify_source_pipeline_closeout(result)}
    _print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
