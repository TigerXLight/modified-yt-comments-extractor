"""Generate and read MSN live-acceptance operator packs.

The pack is deliberately manual-first: it records what an operator saw when
running a real MSN article through the completed adapter, without starting any
live capture or claiming that streamed/external media was downloaded.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class LiveAcceptanceTemplate:
    adapter_name: str = "msn_source_adapter"
    source_platform: str = "MSN"
    generated_at_utc: str = ""
    article_url: str = ""
    output_folder: str = ""
    article_visible: str = "UNKNOWN"
    comments_exported: str = "UNKNOWN"
    profiles_exported: str = "UNKNOWN"
    offline_html_viewed: str = "UNKNOWN"
    warc_replay_result: str = "UNKNOWN"
    strict_wacz_result: str = "UNKNOWN"
    compatible_wacz_result: str = "UNKNOWN"
    images_registered: str = "UNKNOWN"
    images_downloaded_or_hashed: str = "UNKNOWN"
    video_status_recorded: str = "UNKNOWN"
    source_role_reviewed: str = "UNKNOWN"
    republisher_distinction_preserved: str = "UNKNOWN"
    original_source_gap_recorded: str = "UNKNOWN"
    notes: str = ""

    def with_defaults(self) -> "LiveAcceptanceTemplate":
        if self.generated_at_utc:
            return self
        return replace(self, generated_at_utc=_utc_now())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.with_defaults())


CHECKLIST = """# MSN Source Adapter Live Acceptance Checklist

Use this for a real MSN article output folder. This checklist does not run live
capture. It records manual validation results after the operator has already run
an approved capture/export workflow.

## Required checks

1. Article extraction
   - Rendered page opens.
   - Article title/body are visible.
   - Publisher/source is preserved. For reposted articles, keep MSN separate from the visible publisher such as The Independent.

2. Comments/profile extraction
   - Top-level comments export exists.
   - Replies are nested where present.
   - Deleted placeholders are preserved.
   - Profile exports exist when profiles were visible.

3. Offline webpage/archive viewer
   - local_viewer/open_local_viewer.cmd opens.
   - rendered-page.html is listed as b/est viewable page.
   - rendered-page.warc.gz is labelled useful/partial.
   - strict WACZ is labelled experimental/possibly unsupported unless manually proven.

4. Media/video
   - Hero/OpenGraph/Twitter/JSON-LD images are registered.
   - Downloaded media has a local path and checksum where captured.
   - External/streamed/blocked video has explicit status rather than a false success claim.

5. Source-role/source-chain
   - MSN is not silently treated as the original source of republished content.
   - Visible source credits and publisher framing are preserved.
   - Original source gaps are recorded when the first uploader/source is not located.

## Acceptance language

Use ACCEPTED only if all required checks pass or have clear NOT_APPLICABLE
status. Use CONFIDENT_WITH_MANUAL_REVIEW when WARC/WACZ replay, external video,
or original-source tracing remains partial b/ut is honestly labelled.
"""


def write_live_acceptance_pack(output_dir: Path, article_url: str = "", output_folder: str = "") -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    template = LiveAcceptanceTemplate(article_url=article_url, output_folder=output_folder).with_defaults()
    files = {
        "checklist": output_dir / "01_MSN_LIVE_ACCEPTANCE_CHECKLIST.md",
        "result_template_json": output_dir / "02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json",
        "result_template_md": output_dir / "03_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.md",
        "decision_guide": output_dir / "04_MSN_LIVE_ACCEPTANCE_DECISION_GUIDE.md",
    }
    files["checklist"].write_text(CHECKLIST, encoding="utf-8")
    files["result_template_json"].write_text(json.dumps(template.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files["result_template_md"].write_text(render_result_template_markdown(template), encoding="utf-8")
    files["decision_guide"].write_text(DECISION_GUIDE, encoding="utf-8")
    return {name: str(path) for name, path in files.items()}


def render_result_template_markdown(template: LiveAcceptanceTemplate) -> str:
    data = template.to_dict()
    lines = ["# MSN Live Acceptance Result Template", ""]
    for key, value in data.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "Replace UNKNOWN values with PASS / PARTIAL / FAIL / NOT_APPLICABLE and add notes.", ""])
    return "\n".join(lines)


DECISION_GUIDE = """# MSN Live Acceptance Decision Guide

- ACCEPTED: article, comments/profile, viewer, media registration, and source-role provenance pass on the selected real MSN article.
- CONFIDENT_WITH_MANUAL_REVIEW: required areas exist, b/ut WARC/WACZ replay, media download, video stream, or original-source tracing remains partial and honestly labelled.
- PARTIAL_NEEDS_REVIEW: one required area is incomplete b/ut the operator has enough artifacts to continue manual review.
- BLOCKED: article/comments/archive/media/provenance artifacts are missing or contradicted b/y the operator observation.

Do not upgrade a repeated publisher, authority, family, agency, or repost loop to primary/original source status without a located authored source.
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an MSN live-acceptance operator pack.")
    parser.add_argument("--output", required=True, help="Folder where the pack should b/e written.")
    parser.add_argument("--article-url", default="", help="Optional MSN article URL b/eing validated.")
    parser.add_argument("--output-folder", default="", help="Optional existing MSN output folder b/eing validated.")
    args = parser.parse_args(argv)
    files = write_live_acceptance_pack(Path(args.output), article_url=args.article_url, output_folder=args.output_folder)
    print("MSN live acceptance pack written:")
    for name, path in files.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
