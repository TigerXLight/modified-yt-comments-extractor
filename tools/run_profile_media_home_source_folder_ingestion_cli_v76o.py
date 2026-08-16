from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_home_source_folder_ingestion import (
    WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW,
    build_home_source_folder_evaluation_preview,
    render_home_source_folder_evaluation_text,
    write_home_source_folder_evaluation_preview,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a guarded Profile/Media HOME source-folder evaluation preview.")
    parser.add_argument("--source-folder", required=True, help="Explicit single source folder to inspect.")
    parser.add_argument("--print-text", action="store_true", help="Print a readable preview summary.")
    parser.add_argument("--output-json", default="", help="Optional preview JSON path.")
    parser.add_argument("--confirm-write", default="", help=f"Required token for --output-json: {WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        preview = build_home_source_folder_evaluation_preview(args.source_folder)
    except Exception as exc:
        print(f"HOME source folder ingestion failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.print_text:
        print(render_home_source_folder_evaluation_text(preview))
    elif not args.output_json:
        print(json.dumps(preview.to_dict(), ensure_ascii=False, indent=2))

    if args.output_json:
        write_result = write_home_source_folder_evaluation_preview(
            preview,
            args.output_json,
            confirm_write=args.confirm_write,
        )
        if args.print_text:
            print("")
            print("Write result:")
            print(json.dumps(write_result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"preview": preview.to_dict(), "write_result": write_result}, ensure_ascii=False, indent=2))
        if write_result["status"] != "home_source_folder_evaluation_preview_written":
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
