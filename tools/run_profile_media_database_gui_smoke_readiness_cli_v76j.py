from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database_gui_smoke_readiness import (
    build_gui_smoke_readiness_report,
    gui_smoke_readiness_payload,
    render_gui_smoke_readiness_text,
)
from profile_media_database_final_handoff import (
    build_profile_media_final_handoff,
    profile_media_final_handoff_payload,
    render_profile_media_final_handoff_text,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print V76J Profile/Media GUI smoke readiness and final handoff reports.")
    parser.add_argument("--manual-test-database-root", default="%TEMP%\\ytce_profile_media_manual_gui_smoke")
    parser.add_argument("--no-folder-operations", action="store_true")
    parser.add_argument("--no-reconciliation", action="store_true")
    parser.add_argument("--print-text", action="store_true")
    parser.add_argument("--print-handoff", action="store_true")
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_gui_smoke_readiness_report(
        manual_test_database_root=args.manual_test_database_root,
        include_folder_operations=not args.no_folder_operations,
        include_reconciliation=not args.no_reconciliation,
    )
    payload = gui_smoke_readiness_payload(report, include_text=not args.compact)
    if args.print_text:
        print(render_gui_smoke_readiness_text(report))
    elif args.print_handoff:
        handoff = build_profile_media_final_handoff()
        print(render_profile_media_final_handoff_text(handoff))
    else:
        print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    if args.print_handoff and not args.print_text:
        return 0
    if args.print_handoff and args.print_text:
        print("")
        print(render_profile_media_final_handoff_text(build_profile_media_final_handoff()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
