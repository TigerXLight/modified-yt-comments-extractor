from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_browser_capture_inspector import inspect_twitter_browser_capture_output, write_twitter_browser_capture_inspection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a Twitter/X browser capture output directory.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--write-json", default="")
    args = parser.parse_args(argv)
    inspection = inspect_twitter_browser_capture_output(args.output_dir)
    if args.write_json:
        write_twitter_browser_capture_inspection(args.write_json, inspection)
        print(f"WROTE {args.write_json}")
    print(json.dumps(inspection.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if inspection.status != "missing_manifest" else 1


if __name__ == "__main__":
    raise SystemExit(main())
