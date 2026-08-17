from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rendered_citation_recording_metadata_v77d import (  # noqa: E402
    WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D,
    build_rendered_citation_recording_metadata,
    render_rendered_citation_recording_summary,
    write_rendered_citation_recording_metadata,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a local rendered citation/source-preservation metadata JSON manifest.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--page-url", default="")
    parser.add_argument("--media-url", default="")
    parser.add_argument("--capture-kind", required=True)
    parser.add_argument("--capture-method", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--media-position-start", default="")
    parser.add_argument("--media-position-end", default="")
    parser.add_argument("--local-file", default="")
    parser.add_argument("--source-unit-path", default="")
    parser.add_argument("--capture-blocked", action="store_true")
    parser.add_argument("--blocked-reason", default="")
    parser.add_argument("--human-mediated-access-required", action="store_true")
    parser.add_argument("--human-mediated-access-completed-by-user", action="store_true")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--confirm-write", default="")
    parser.add_argument("--print-text", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        metadata = build_rendered_citation_recording_metadata(
            source_url=args.source_url,
            page_url=args.page_url,
            media_url=args.media_url,
            capture_kind=args.capture_kind,
            capture_method=args.capture_method,
            user_declared_purpose=args.purpose,
            media_position_start=args.media_position_start,
            media_position_end=args.media_position_end,
            local_file_path=args.local_file,
            source_unit_path=args.source_unit_path,
            capture_blocked=args.capture_blocked,
            blocked_reason=args.blocked_reason,
            human_mediated_access_required=args.human_mediated_access_required,
            human_mediated_access_completed_by_user=args.human_mediated_access_completed_by_user,
        )
    except Exception as exc:
        print(f"rendered citation metadata failed: {exc}", file=sys.stderr)
        return 2

    if args.print_text or not args.output_json:
        print(render_rendered_citation_recording_summary(metadata))

    if args.output_json:
        if args.confirm_write != WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D:
            print("confirmation required: WRITE_RENDERED_CITATION_RECORDING_METADATA_V77D", file=sys.stderr)
            return 2
        try:
            output = write_rendered_citation_recording_metadata(metadata, args.output_json, confirm_write=args.confirm_write)
        except Exception as exc:
            print(f"write failed: {exc}", file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "status": "rendered_citation_recording_metadata_written",
                    "output_json": str(output),
                    "schema_version": metadata.schema_version,
                    "file_write_performed": True,
                    "browser_launch_performed": False,
                    "web_download_performed": False,
                    "media_download_performed": False,
                    "recording_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
