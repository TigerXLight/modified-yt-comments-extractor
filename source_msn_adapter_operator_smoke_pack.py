"""Generate an operator smoke-test pack for final MSN adapter validation.

This module creates files only. It does not perform live capture, network access, or
media download. The generated pack tells the operator what to check on a real MSN
article and gives a structured JSON template that the final done gate can read.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass
class SmokeStep:
    id: str
    title: str
    expected: str
    status: str = "PENDING"
    notes: str = ""


@dataclass
class SmokePack:
    target_url: str
    output_dir: str
    created_at_utc: str
    steps: list[SmokeStep] = field(default_factory=list)
    generated_files: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "output_dir": self.output_dir,
            "created_at_utc": self.created_at_utc,
            "steps": [asdict(step) for step in self.steps],
            "generated_files": list(self.generated_files),
        }


def default_steps() -> list[SmokeStep]:
    return [
        SmokeStep(
            "article",
            "Article extraction",
            "Title, URL/canonical/raw URL, publisher/source, author/date/read-time where available, body/bullets, and extracted source links are present or honestly marked missing.",
        ),
        SmokeStep(
            "comments",
            "Comments/profile extraction",
            "Top/Newest run outputs preserve parents, nested replies, deleted placeholders, votes, profile URLs/CIDs, and profile account stats where MSN exposes them.",
        ),
        SmokeStep(
            "offline_viewer",
            "Offline webpage/archive viewer",
            "rendered-page.html opens as best viewable page, local viewer opens, WARC.GZ is present/partial, strict WACZ is not overclaimed, compatible WACZ status is labelled if present.",
        ),
        SmokeStep(
            "media",
            "Images/video/media registration",
            "Hero/OpenGraph/Twitter-card/JSON-LD images and video/poster/stream candidates are registered; downloaded files have hashes; blocked/external/streamed items have status notes.",
        ),
        SmokeStep(
            "source_chain",
            "Source-role and media source-chain",
            "MSN republisher surface, visible publisher/source, credits such as Google Street View, claimed original source, and source-chain gaps are preserved separately.",
        ),
        SmokeStep(
            "total_package",
            "Total package and reports",
            "Total package, release report, final validation report, and done-gate report exist and agree on PASS/PARTIAL/FAIL status.",
        ),
    ]


def render_steps_markdown(pack: SmokePack) -> str:
    lines = [
        "# MSN Adapter Operator Smoke Pack",
        "",
        f"Target URL: `{pack.target_url}`",
        f"Created at UTC: `{pack.created_at_utc}`",
        "",
        "This checklist is for manual validation only. It must not auto-start live capture or claim success without operator evidence.",
        "",
        "## Steps",
        "",
    ]
    for step in pack.steps:
        lines.extend(
            [
                f"### {step.id}: {step.title}",
                "",
                f"Expected: {step.expected}",
                "",
                "Result: PASS / PARTIAL / FAIL / NOT_APPLICABLE",
                "",
                "Notes:",
                "",
                "- ",
                "",
            ]
        )
    lines.extend(
        [
            "## Source-role reminder",
            "",
            "Do not treat MSN as primary/original merely because the page is captured from MSN. For reposted articles, preserve the MSN captured surface separately from the visible publisher/source, visible media credits, claimed original source, and any source-chain gap.",
            "",
            "Example: MSN page = captured platform/republisher surface; The Independent = visible publisher/source if shown; Google Street View = visible media credit if shown; original media source remains unverified unless located.",
            "",
        ]
    )
    return "\n".join(lines)


def manual_validation_template(pack: SmokePack) -> dict[str, Any]:
    return {
        "target_url": pack.target_url,
        "created_at_utc": pack.created_at_utc,
        "completed_at_utc": "",
        "operator": "",
        "article_status": "PENDING",
        "comments_status": "PENDING",
        "archive_status": "PENDING",
        "media_status": "PENDING",
        "source_chain_status": "PENDING",
        "total_package_status": "PENDING",
        "wacz_replayweb_status": "PENDING",
        "warc_replayweb_status": "PENDING",
        "rendered_html_status": "PENDING",
        "notes": "",
        "source_role_notes": {
            "msn_surface_role": "secondary/outside perspective unless directly authored/original",
            "visible_publisher_or_source": "",
            "visible_media_credit": "",
            "claimed_original_source": "",
            "original_source_url": "",
            "source_chain_gap": True,
            "primary_source_status": "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED",
        },
        "steps": [asdict(step) for step in pack.steps],
    }


def run_command_text(bundle_dir_placeholder: str = "<MSN_OUTPUT_FOLDER>") -> str:
    return (
        "@echo off\n"
        "setlocal\n"
        "set REPO=T:\\References\\to go\\Media\\tools\\Modified YouTube comment extractor\n"
        f"set BUNDLE={bundle_dir_placeholder}\n"
        "set PY=C:\\Users\\fahad\\AppData\\Local\\Programs\\Python\\Python311\\python.exe\n"
        '"%PY%" "%REPO%\\source_msn_adapter_done_gate.py" --bundle-dir "%BUNDLE%"\n'
        "endlocal\n"
    )


def create_operator_smoke_pack(target_url: str, output_dir: str | Path) -> SmokePack:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    pack = SmokePack(
        target_url=target_url,
        output_dir=str(out),
        created_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        steps=default_steps(),
    )
    files = {
        "MSN_OPERATOR_SMOKE_STEPS.md": render_steps_markdown(pack),
        "MSN_MANUAL_VALIDATION_RESULT_TEMPLATE.json": json.dumps(manual_validation_template(pack), indent=2, ensure_ascii=False),
        "RUN_DONE_GATE_AFTER_MANUAL_REVIEW.cmd": run_command_text(),
    }
    generated: list[str] = []
    for name, content in files.items():
        path = out / name
        path.write_text(content, encoding="utf-8")
        generated.append(str(path))
    index = {
        "target_url": pack.target_url,
        "created_at_utc": pack.created_at_utc,
        "generated_files": generated,
        "purpose": "manual_operator_smoke_validation_for_msn_adapter_completion",
    }
    index_path = out / "MSN_OPERATOR_SMOKE_PACK_INDEX.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    generated.append(str(index_path))
    pack.generated_files = generated
    return pack


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a manual operator smoke pack for MSN adapter validation.")
    parser.add_argument("--target-url", required=True, help="MSN article URL to validate manually.")
    parser.add_argument("--output-dir", required=True, help="Directory where smoke-pack files should be written.")
    parser.add_argument("--json", action="store_true", help="Print generated pack JSON.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    pack = create_operator_smoke_pack(args.target_url, args.output_dir)
    if args.json:
        print(json.dumps(pack.as_dict(), indent=2, ensure_ascii=False))
    else:
        print("MSN operator smoke pack created:")
        for path in pack.generated_files:
            print(path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
