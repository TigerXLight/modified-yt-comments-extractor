from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_case_materialize import (  # noqa: E402
    PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION,
    apply_case_materialize_plan,
    build_case_materialize_plan,
    result_payload,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run or explicitly materialize a guarded profile/media case pack.")
    parser.add_argument("--database-root", required=True)
    parser.add_argument("--case-title", required=True)
    parser.add_argument("--case-root", default="")
    parser.add_argument("--source-page", default="")
    parser.add_argument("--source-title", default="")
    parser.add_argument("--source-bucket", default="Articles")
    parser.add_argument("--profile-text", default="")
    parser.add_argument("--canonical-name", default="")
    parser.add_argument("--source-role", default="UNKNOWN_SOURCE_ROLE")
    parser.add_argument("--claim-basis", default="UNKNOWN_CLAIM_BASIS")
    parser.add_argument("--currentness-status", default="UNKNOWN")
    parser.add_argument("--source-chain-gap", action="store_true")
    parser.add_argument("--disputed-framing", action="store_true")
    parser.add_argument("--notes-on-context-dispute", default="")
    parser.add_argument("--confidence-or-verification-notes", default="")
    parser.add_argument("--collaboration-or-corroboration-notes", default="")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-materialize", default="")
    parser.add_argument("--print-plan", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source_specs = []
    if args.source_page or args.source_title:
        source_specs.append(
            {
                "source_page": args.source_page,
                "source_title": args.source_title,
                "source_bucket": args.source_bucket,
                "source_role": args.source_role,
                "claim_basis": args.claim_basis,
                "currentness_status": args.currentness_status,
                "source_chain_gap": args.source_chain_gap,
                "disputed_framing": args.disputed_framing,
                "notes_on_context_dispute": args.notes_on_context_dispute,
                "confidence_or_verification_notes": args.confidence_or_verification_notes,
                "collaboration_or_corroboration_notes": args.collaboration_or_corroboration_notes,
            }
        )
    profile_specs = []
    if args.profile_text or args.canonical_name:
        profile_specs.append(
            {
                "profile_text": args.profile_text,
                "canonical_name": args.canonical_name,
                "source_bucket": args.source_bucket,
                "source_role": args.source_role,
                "claim_basis": args.claim_basis,
                "currentness_status": args.currentness_status,
            }
        )
    plan = build_case_materialize_plan(
        database_root=args.database_root,
        case_title=args.case_title,
        case_root=args.case_root,
        source_specs=tuple(source_specs),
        profile_specs=tuple(profile_specs),
        source_role=args.source_role,
        claim_basis=args.claim_basis,
        currentness_status=args.currentness_status,
        execute=args.execute,
        confirmation_phrase=args.confirm_materialize,
    )
    result = apply_case_materialize_plan(plan)
    payload = result_payload(result, plan=plan if args.print_plan else None)
    payload["confirmation_phrase_expected"] = PROFILE_MEDIA_CASE_MATERIALIZE_CONFIRMATION if args.execute else ""
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not result.status.startswith("blocked") else 2


if __name__ == "__main__":
    raise SystemExit(main())
