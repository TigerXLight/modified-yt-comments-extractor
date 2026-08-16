from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database import (
    ClaimBasis,
    CurrentnessStatus,
    MediaBucket,
    ProfileCollectionLevel,
    ProfileSourceRole,
    build_case_local_profile_from_text,
    build_case_record,
    build_database_tree_rows,
    build_global_profile_from_case_profile,
    build_manifest,
    build_media_source_record,
    render_database_tree_text,
    write_database_tree_text,
    write_manifest_json,
)


SAMPLE_PROFILE_TEXT = """
Name: Example Person
Date: 2026-06-05
Text: Source-authored or source-attributed text relevant to this case-local profile.
Identifiers:
Description: example description from source text
Religion: source-stated only, not inferred
Address: Example Case\\Sources\\Articles\\article.txt
Source: Example Article
""".strip()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a dry-run Profile/Media Database manifest and tree preview. No case folders are moved or renamed."
    )
    parser.add_argument("--database-root", required=True, help="Local Database root path for planning, e.g. T:\\Database")
    parser.add_argument("--case-title", default="Example Case", help="Case title for the dry-run manifest.")
    parser.add_argument("--case-root", default="", help="Existing/proposed case root. Defaults to database-root/Cases/case-title.")
    parser.add_argument("--profile-text-file", default="", help="Optional profile text file using Name/Date/Text/Identifiers/Address/Source blocks.")
    parser.add_argument("--manifest-out", default="", help="Optional JSON manifest output path.")
    parser.add_argument("--tree-out", default="", help="Optional text tree output path.")
    parser.add_argument("--create-parent", action="store_true", help="Allow parent folder creation for output manifest/tree files only.")
    parser.add_argument("--print-tree", action="store_true", help="Print the Database-mode tree preview.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.profile_text_file:
        profile_text = Path(args.profile_text_file).read_text(encoding="utf-8")
    else:
        profile_text = SAMPLE_PROFILE_TEXT

    case_profile = build_case_local_profile_from_text(
        case_id="case_cli_preview",
        text=profile_text,
        default_source_bucket=MediaBucket.ARTICLES,
        default_source_role=ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
        default_claim_basis=ClaimBasis.UNKNOWN_CLAIM_BASIS,
        default_currentness_status=CurrentnessStatus.UNKNOWN,
    )
    global_profile = build_global_profile_from_case_profile(case_profile)
    media_source = build_media_source_record(
        source_page="Example Article",
        source_bucket=MediaBucket.ARTICLES,
        local_address=str(Path(args.case_root or Path(args.database_root) / "Cases" / args.case_title) / "Sources" / "Articles" / "article.txt"),
        title="Example Article",
    )
    case = build_case_record(
        database_root=args.database_root,
        case_title=args.case_title,
        case_id="case_cli_preview",
        case_root=args.case_root,
        profiles=(case_profile,),
        media_sources=(media_source,),
    )
    manifest = build_manifest(
        database_root=args.database_root,
        cases=(case,),
        global_profiles=(global_profile,),
    )
    rows = build_database_tree_rows(manifest)

    output: dict[str, object] = {
        "schema_version": "profile_media_database_cli.v75g",
        "status": "success",
        "case_count": len(manifest.cases),
        "global_profile_count": len(manifest.global_profiles),
        "tree_row_count": len(rows),
        "folder_creation_performed": False,
        "file_move_performed": False,
        "sensitive_identifier_inference_performed": False,
    }
    if args.manifest_out:
        output["manifest_write"] = write_manifest_json(manifest, args.manifest_out, create_parent=args.create_parent)
    if args.tree_out:
        output["tree_write"] = write_database_tree_text(manifest, args.tree_out, create_parent=args.create_parent)
    if args.print_tree:
        output["tree_preview"] = render_database_tree_text(rows)
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
