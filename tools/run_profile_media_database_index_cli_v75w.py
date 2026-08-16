from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_case_batch import write_demo_case_batch_json  # noqa: E402
from profile_media_database_index import (  # noqa: E402
    build_database_index_from_batch_json_files,
    result_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only Profile/Media Database index from explicit case batch JSON files.")
    parser.add_argument("--batch-json", action="append", default=[], help="Explicit case batch JSON file. May be repeated.")
    parser.add_argument("--write-demo-batch", default="", help="Write a demo batch JSON file to this path.")
    parser.add_argument("--database-root", default="", help="Database root used when writing a demo batch.")
    parser.add_argument("--case-title", default="Example Case", help="Case title used when writing a demo batch.")
    parser.add_argument("--print-index", action="store_true", help="Include a human-readable index summary.")
    args = parser.parse_args()

    batch_paths = list(args.batch_json)
    if args.write_demo_batch:
        written = write_demo_case_batch_json(args.write_demo_batch, database_root=args.database_root, case_title=args.case_title)
        if not batch_paths:
            batch_paths.append(written)

    if not batch_paths:
        parser.error("at least one --batch-json is required, or use --write-demo-batch")

    index = build_database_index_from_batch_json_files(batch_paths)
    output = result_payload(index, include_text=args.print_index)
    output["batch_json_files"] = batch_paths
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
