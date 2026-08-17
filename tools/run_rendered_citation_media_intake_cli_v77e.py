from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rendered_citation_media_intake_v77e import (  # noqa: E402
    WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E,
    build_rendered_citation_media_intake_manifest,
    render_rendered_citation_media_intake_summary,
    write_rendered_citation_media_intake_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a local rendered citation media-intake manifest.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--page-url", default="")
    parser.add_argument("--media-url", default="")
    parser.add_argument("--source-unit-path", default="")
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--capture-kind", required=True)
    parser.add_argument("--capture-method", required=True)
    parser.add_argument("--media-position-start", default="")
    parser.add_argument("--media-position-end", default="")
    parser.add_argument("--local-file", default="")
    parser.add_argument("--local-file-role", default="review_required")
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
        manifest = build_rendered_citation_media_intake_manifest(
            source_url=args.source_url,
            page_url=args.page_url,
            media_url=args.media_url,
            source_unit_path=args.source_unit_path,
            user_declared_purpose=args.purpose,
            capture_kind=args.capture_kind,
            capture_method=args.capture_method,
            media_position_start=args.media_position_start,
            media_position_end=args.media_position_end,
            local_file_path=args.local_file,
            local_file_role=args.local_file_role,
            capture_blocked=args.capture_blocked,
            blocked_reason=args.blocked_reason,
            human_mediated_access_required=args.human_mediated_access_required,
            human_mediated_access_completed_by_user=args.human_mediated_access_completed_by_user,
        )
    except Exception as exc:
        print(f"rendered citation media intake failed: {exc}", file=sys.stderr)
        return 2

    if args.print_text or not args.output_json:
        print(render_rendered_citation_media_intake_summary(manifest))

    if args.output_json:
        if args.confirm_write != WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E:
            print("confirmation required: WRITE_RENDERED_CITATION_MEDIA_INTAKE_V77E", file=sys.stderr)
            return 2
        try:
            output = write_rendered_citation_media_intake_manifest(manifest, args.output_json, confirm_write=args.confirm_write)
        except Exception as exc:
            print(f"write failed: {exc}", file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "status": "rendered_citation_media_intake_written",
                    "output_json": str(output),
                    "schema_version": manifest.schema_version,
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
