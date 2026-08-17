from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_capture_live_output_closeout_v77c import (
    WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C,
    build_twitter_live_output_closeout,
    render_twitter_live_output_closeout_text,
    write_twitter_live_output_closeout,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline closeout for existing Twitter/X V74H/V74I output folders.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--profile-tab", default="replies")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--profile-media-records-jsonl", default="")
    parser.add_argument("--confirm-write", default="")
    parser.add_argument("--print-text", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        closeout, records = build_twitter_live_output_closeout(
            output_root=args.output_root,
            source_url=args.source_url,
            profile_tab=args.profile_tab,
        )
    except Exception as exc:
        print(f"Twitter/X live-output closeout failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.print_text:
        print(render_twitter_live_output_closeout_text(closeout))
    elif not args.output_json and not args.profile_media_records_jsonl:
        print(json.dumps({"closeout": closeout.to_dict(), "profile_media_records": list(records)}, ensure_ascii=False, indent=2))

    if args.output_json or args.profile_media_records_jsonl:
        write_result = write_twitter_live_output_closeout(
            closeout=closeout,
            profile_media_records=records,
            output_json=args.output_json,
            profile_media_records_jsonl=args.profile_media_records_jsonl,
            confirm_write=args.confirm_write,
        )
        if args.print_text:
            print("")
            print("Write result:")
            print(json.dumps(write_result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"closeout": closeout.to_dict(), "profile_media_records_count": len(records), "write_result": write_result}, ensure_ascii=False, indent=2))
        if write_result["status"] != "twitter_capture_live_output_closeout_written":
            print(f"Confirmation required: {WRITE_TWITTER_CAPTURE_LIVE_OUTPUT_CLOSEOUT_V77C}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
