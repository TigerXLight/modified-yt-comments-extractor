from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_source_intake import (
    PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION,
    apply_source_intake_plan,
    build_source_intake_plan,
    result_payload,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan or explicitly create a Profile/Media source-intake record. Default is dry-run."
    )
    parser.add_argument("--database-root", required=True, help="Database root, for example T:\\Database")
    parser.add_argument("--case-title", required=True, help="Case title used under database-root\\Cases.")
    parser.add_argument("--case-root", default="", help="Optional exact case root. Defaults to database-root\\Cases\\case-title.")
    parser.add_argument("--source-page", required=True, help="Source page/name, e.g. BelfastLive, X status URL, USB source label.")
    parser.add_argument("--source-title", default="", help="Human-readable source folder title.")
    parser.add_argument(
        "--source-bucket",
        required=True,
        help="One of: Articles, Social Media/Online, Social Media/Offline, Internal Media, Reference Extants.",
    )
    parser.add_argument("--source-role", default="UNKNOWN_SOURCE_ROLE")
    parser.add_argument("--claim-basis", default="UNKNOWN_CLAIM_BASIS")
    parser.add_argument("--currentness-status", default="UNKNOWN")
    parser.add_argument("--disputed-framing", action="store_true")
    parser.add_argument("--notes-on-context-dispute", default="")
    parser.add_argument("--source-chain-gap", action="store_true")
    parser.add_argument("--confidence-notes", default="")
    parser.add_argument("--family-or-authority-claim-basis", default="")
    parser.add_argument("--identity-claim-basis", default="")
    parser.add_argument("--appearance-claim-basis", default="")
    parser.add_argument("--collaboration-notes", default="")
    parser.add_argument("--execute", action="store_true", help="Actually create the source folder and claim-evaluation files.")
    parser.add_argument(
        "--confirm-intake",
        default="",
        help=f"Required with --execute. Must equal {PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION}.",
    )
    parser.add_argument("--print-plan", action="store_true", help="Include source-intake plan and readable text in output.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    plan = build_source_intake_plan(
        database_root=args.database_root,
        case_title=args.case_title,
        case_root=args.case_root,
        source_page=args.source_page,
        source_title=args.source_title,
        source_bucket=args.source_bucket,
        source_role=args.source_role,
        claim_basis=args.claim_basis,
        currentness_status=args.currentness_status,
        disputed_framing=args.disputed_framing,
        notes_on_context_dispute=args.notes_on_context_dispute,
        source_chain_gap=args.source_chain_gap,
        confidence_or_verification_notes=args.confidence_notes,
        family_or_authority_claim_basis=args.family_or_authority_claim_basis,
        identity_claim_basis=args.identity_claim_basis,
        appearance_claim_basis=args.appearance_claim_basis,
        collaboration_or_corroboration_notes=args.collaboration_notes,
        execute=args.execute,
        confirmation_phrase=args.confirm_intake,
    )
    result = apply_source_intake_plan(plan)
    print(json.dumps(result_payload(result, plan=plan if args.print_plan else None), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.status in {"planned_dry_run", "created", "updated"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
