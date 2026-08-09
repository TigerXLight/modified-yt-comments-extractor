from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_local_web_archive_actions import (
    REPLAYWEB_PAGE_COMPATIBLE,
    REPLAYWEB_PAGE_PACKAGE_READY,
    REPLAYWEB_PAGE_COMPATIBILITY_PROFILE,
    STRUCTURAL_WACZ_VALID,
    WACZ_12_COMPATIBILITY_PROFILE,
    WACZ_REPLAY_COMPATIBILITY_REPAIRED,
    build_static_page_view_input_for_wacz,
    build_static_replay_evidence_input_for_wacz,
    repair_local_web_archive_wacz,
    verify_local_web_archive_package,
)
from source_replay_static_snapshot import (
    write_static_page_view_standalone_outputs,
    write_static_replay_standalone_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a side-by-side ReplayWeb-compatible WACZ repair. The input WACZ is never "
            "overwritten and no live/network action is performed."
        )
    )
    parser.add_argument("--input-wacz", required=True, help="Existing WACZ to inspect and repair")
    parser.add_argument(
        "--output-wacz",
        default="",
        help="Optional output path; defaults to <input>.replayweb-fixed.wacz beside the original",
    )
    parser.add_argument(
        "--expected-source-url",
        default="",
        help="Optional source URL to require in the repaired WACZ; URL fragments are ignored for replay lookup",
    )
    parser.add_argument(
        "--compatibility-profile",
        choices=(REPLAYWEB_PAGE_COMPATIBILITY_PROFILE, WACZ_12_COMPATIBILITY_PROFILE),
        default=REPLAYWEB_PAGE_COMPATIBILITY_PROFILE,
        help=(
            "Output profile to create. Default 'replayweb-page' keeps the legacy data-package "
            "profile accepted by the hosted ReplayWeb.page browser app while fixing CDXJ lookup. "
            "Use 'wacz12' for the stricter published WACZ 1.2 profile."
        ),
    )
    parser.add_argument(
        "--add-static-evidence-page",
        "--static-replay-page",
        action="store_true",
        help=(
            "Add a derived no-JavaScript static evidence page as a separate synthetic WARC record "
            "and pages/pages.jsonl entry. The original source page entry is preserved."
        ),
    )
    parser.add_argument(
        "--static-evidence-url",
        default="",
        help="Optional stable synthetic URL for the static evidence page.",
    )
    parser.add_argument(
        "--static-evidence-title",
        default="",
        help="Optional title for the static evidence page.",
    )
    parser.add_argument(
        "--static-evidence-capture-timestamp",
        default="",
        help="Optional timestamp to record on the synthetic static evidence WARC records.",
    )
    parser.add_argument(
        "--runtime-limitation-note",
        action="append",
        default=[],
        help="Manual ReplayWeb runtime limitation note to include in the static evidence page.",
    )
    parser.add_argument(
        "--manifest-path",
        default="",
        help="Optional local evidence manifest used only to summarize comments evidence in the static page.",
    )
    parser.add_argument(
        "--expected-comment-count",
        type=int,
        default=0,
        help="Optional declared comment count for manifest-based comments evidence checks.",
    )
    parser.add_argument(
        "--static-output-dir",
        default="",
        help=(
            "Optional directory for standalone fallback files. Writes static-evidence.* and "
            "static-page-view.* outputs without relying on WACZ lookup."
        ),
    )
    parser.add_argument(
        "--write-static-html",
        default="",
        help="Optional explicit output path for a direct no-JavaScript static evidence HTML file.",
    )
    parser.add_argument(
        "--write-static-warc-gz",
        default="",
        help="Optional explicit output path for a raw ReplayWeb-loadable static-only WARC.GZ file.",
    )
    parser.add_argument(
        "--write-static-warc",
        default="",
        help="Optional explicit output path for an uncompressed static-only WARC file.",
    )
    parser.add_argument(
        "--static-page-view-url",
        default="",
        help="Optional stable synthetic URL for the static archived webpage view.",
    )
    parser.add_argument(
        "--write-static-page-html",
        default="",
        help="Optional explicit output path for a direct no-JavaScript static archived webpage HTML file.",
    )
    parser.add_argument(
        "--write-static-page-warc-gz",
        default="",
        help="Optional explicit output path for a raw ReplayWeb-loadable static page-view WARC.GZ file.",
    )
    parser.add_argument(
        "--write-static-page-warc",
        default="",
        help="Optional explicit output path for an uncompressed static page-view WARC file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = Path(args.output_wacz) if args.output_wacz else None
    repair = repair_local_web_archive_wacz(
        args.input_wacz,
        output_path=output_path,
        compatibility_profile=args.compatibility_profile,
        add_static_evidence_page=bool(args.add_static_evidence_page),
        static_evidence_url=args.static_evidence_url,
        static_evidence_source_url=args.expected_source_url,
        static_evidence_title=args.static_evidence_title,
        static_evidence_capture_timestamp=args.static_evidence_capture_timestamp,
        static_evidence_runtime_notes=tuple(args.runtime_limitation_note or ()),
        manifest_path=Path(args.manifest_path) if args.manifest_path else None,
        expected_comment_count=args.expected_comment_count,
    )
    payload: dict[str, object] = {"repair": repair.to_dict()}

    if repair.status == WACZ_REPLAY_COMPATIBILITY_REPAIRED:
        repaired_path = output_path or Path(args.input_wacz).with_name(
            Path(args.input_wacz).stem + ".replayweb-fixed.wacz"
        )
        verification = verify_local_web_archive_package(
            repaired_path,
            manifest_path=Path(args.manifest_path) if args.manifest_path else None,
            expected_source_url=args.expected_source_url,
            expected_comment_count=args.expected_comment_count,
            allow_replayweb_page_legacy_profile=(
                args.compatibility_profile == REPLAYWEB_PAGE_COMPATIBILITY_PROFILE
            ),
        )
        payload["verification"] = verification.to_dict()
        ok = verification.status in {
            STRUCTURAL_WACZ_VALID,
            REPLAYWEB_PAGE_COMPATIBLE,
            REPLAYWEB_PAGE_PACKAGE_READY,
        }
        static_output_dir = Path(args.static_output_dir) if args.static_output_dir else None
        html_path = Path(args.write_static_html) if args.write_static_html else None
        warc_gz_path = Path(args.write_static_warc_gz) if args.write_static_warc_gz else None
        warc_path = Path(args.write_static_warc) if args.write_static_warc else None
        page_html_path = Path(args.write_static_page_html) if args.write_static_page_html else None
        page_warc_gz_path = Path(args.write_static_page_warc_gz) if args.write_static_page_warc_gz else None
        page_warc_path = Path(args.write_static_page_warc) if args.write_static_page_warc else None
        if static_output_dir:
            html_path = html_path or static_output_dir / "static-evidence.html"
            warc_gz_path = warc_gz_path or static_output_dir / "static-evidence.warc.gz"
            warc_path = warc_path or static_output_dir / "static-evidence.warc"
            page_html_path = page_html_path or static_output_dir / "static-page-view.html"
            page_warc_gz_path = page_warc_gz_path or static_output_dir / "static-page-view.warc.gz"
            page_warc_path = page_warc_path or static_output_dir / "static-page-view.warc"
        if any((html_path, warc_gz_path, warc_path)):
            static_input = build_static_replay_evidence_input_for_wacz(
                args.input_wacz,
                manifest_path=Path(args.manifest_path) if args.manifest_path else None,
                expected_source_url=args.expected_source_url,
                expected_comment_count=args.expected_comment_count,
                static_evidence_url=args.static_evidence_url,
                static_evidence_title=args.static_evidence_title,
                static_evidence_capture_timestamp=args.static_evidence_capture_timestamp,
                static_evidence_runtime_notes=tuple(args.runtime_limitation_note or ()),
            )
            static_outputs = write_static_replay_standalone_outputs(
                static_input,
                html_path=html_path,
                warc_gz_path=warc_gz_path,
                warc_path=warc_path,
            )
            payload["static_outputs"] = static_outputs.to_dict()
            ok = ok and not static_outputs.errors
        if any((page_html_path, page_warc_gz_path, page_warc_path)):
            static_page_input = build_static_page_view_input_for_wacz(
                args.input_wacz,
                manifest_path=Path(args.manifest_path) if args.manifest_path else None,
                expected_source_url=args.expected_source_url,
                expected_comment_count=args.expected_comment_count,
                static_page_view_url=args.static_page_view_url,
                static_page_view_title=args.static_evidence_title,
                static_page_view_capture_timestamp=args.static_evidence_capture_timestamp,
                static_page_view_runtime_notes=tuple(args.runtime_limitation_note or ()),
                evidence_report_path=html_path if html_path else None,
                evidence_report_url=args.static_evidence_url,
            )
            static_page_outputs = write_static_page_view_standalone_outputs(
                static_page_input,
                html_path=page_html_path,
                warc_gz_path=page_warc_gz_path,
                warc_path=page_warc_path,
            )
            payload["static_page_view_outputs"] = static_page_outputs.to_dict()
            ok = ok and not static_page_outputs.errors
    else:
        ok = False

    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
