from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database_regression import (  # noqa: E402
    run_full_profile_media_regression,
    write_integration_batch_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the V76B Profile/Media Database full integration readiness regression.")
    parser.add_argument("--batch-json", action="append", default=[], help="Explicit case batch JSON file. May be repeated.")
    parser.add_argument("--write-demo-batch", default="", help="Write the large V76B integration fixture to this path and use it when no --batch-json is supplied.")
    parser.add_argument("--database-root", default="Demo Database", help="Database root label/path used inside the regression.")
    parser.add_argument("--case-title", default="V76B Integration Demo Case", help="Case title used when writing the V76B demo fixture.")
    parser.add_argument("--print-report", action="store_true", help="Include human-readable regression, safety, and readiness text.")
    parser.add_argument("--compact", action="store_true", help="Omit detailed nested payloads from the JSON output.")
    args = parser.parse_args()

    batch_paths = list(args.batch_json)
    if args.write_demo_batch:
        written = write_integration_batch_json(args.write_demo_batch, database_root=args.database_root, case_title=args.case_title)
        if not batch_paths:
            batch_paths.append(written)
    if not batch_paths:
        parser.error("provide --batch-json or --write-demo-batch")

    result = run_full_profile_media_regression(batch_paths, database_root=args.database_root, include_text=args.print_report)
    print(json.dumps(result.to_dict(include_text=args.print_report, include_payloads=not args.compact), indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.status == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())
