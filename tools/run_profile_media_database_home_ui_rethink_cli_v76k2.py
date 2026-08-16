from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_article_source_tooling_review import build_article_source_tooling_review, render_article_source_tooling_review_text
from profile_media_database_ui_language import home_repository_status_payload, render_home_repository_status
from profile_media_home_repository_model import parse_home_classification_path, render_home_classification_path
from profile_media_source_criticism_model import (
    EVIDENCE_CORROBORATED_TEXT_CHAIN,
    EVIDENCE_IMAGE,
    build_evidence_marking,
    evaluate_structural_source_criticism,
    render_source_criticism_decision,
)


def _build_demo_payload() -> dict[str, object]:
    home = home_repository_status_payload(
        home_root="%TEMP%\\ytce_profile_media_home_demo",
        primary_count=1,
        secondary_count=2,
        tertiary_count=3,
        internal_media_count=1,
        person_count=4,
        review_count=5,
    )
    classification = parse_home_classification_path(
        r"Sexual offences\Rape\Adults\Direct\Non-religious or not identified\June 2026\Belfast Telegraph\21 Jun - Example article folder - White"
    )
    affiliation_gap = evaluate_structural_source_criticism([
        build_evidence_marking(
            EVIDENCE_IMAGE,
            description="Image subject appears near a claim but is not affiliated with the claim.",
            sustainable_marking="example screenshot cell",
            directly_affiliated_with_claim=False,
        )
    ])
    text_chain = evaluate_structural_source_criticism([
        build_evidence_marking(
            EVIDENCE_CORROBORATED_TEXT_CHAIN,
            description="Publisher A with marked basis.",
            sustainable_marking="publisher/source/date/byline/outbound basis",
            directly_affiliated_with_claim=True,
        ),
        build_evidence_marking(
            EVIDENCE_CORROBORATED_TEXT_CHAIN,
            description="Publisher B with marked basis and bias notes.",
            sustainable_marking="publisher/source/date/byline/outbound basis",
            bias_notes="repeat-chain risk checked",
            directly_affiliated_with_claim=True,
        ),
    ])
    tooling = build_article_source_tooling_review()
    return {
        "schema_version": "profile-media-database-home-ui-rethink-cli-v76k2",
        "home_status": home,
        "classification_path": classification.to_dict(),
        "affiliation_gap_decision": affiliation_gap.to_dict(),
        "text_chain_decision": text_chain.to_dict(),
        "article_tooling_review": tooling.to_dict(),
        "folder_scan_performed": False,
        "file_copy_performed": False,
        "media_download_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the V76K2 HOME/source-criticism UI rethink proof.")
    parser.add_argument("--print-json", action="store_true")
    parser.add_argument("--print-text", action="store_true")
    args = parser.parse_args()
    payload = _build_demo_payload()
    if args.print_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if args.print_text or not args.print_json:
        print(render_home_repository_status(payload["home_status"]))
        print()
        print(render_home_classification_path(parse_home_classification_path(payload["classification_path"]["normalized_path"])))
        print()
        print(render_source_criticism_decision(evaluate_structural_source_criticism([
            build_evidence_marking(EVIDENCE_IMAGE, directly_affiliated_with_claim=False, sustainable_marking="example screenshot cell")
        ])))
        print()
        print(render_article_source_tooling_review_text(build_article_source_tooling_review()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
