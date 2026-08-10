from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


SCHEMA_VERSION = "2026-08-10.1"
ARTIFACT_KIND = "msn_source_adapter_live_evidence_template"


@dataclass(frozen=True)
class LiveEvidenceCheckTemplate:
    check_id: str
    label: str
    required: bool = True
    status: str = "UNSET"
    evidence_files: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class LiveEvidenceTemplate:
    schema_version: str
    artifact_kind: str
    target_url: str
    article_output_folder: str
    operator: str
    checked_at_utc: str
    operator_signed: bool
    checks: List[LiveEvidenceCheckTemplate]


def default_checks() -> List[LiveEvidenceCheckTemplate]:
    return [
        LiveEvidenceCheckTemplate("article_extracted", "Article title/body/source metadata were extracted."),
        LiveEvidenceCheckTemplate("comments_exported", "Comments were exported with parent/reply structure where available."),
        LiveEvidenceCheckTemplate("profiles_exported", "Profile links and account-stat rows were exported where available."),
        LiveEvidenceCheckTemplate("offline_html_viewer", "Offline HTML viewer exists and opens the captured article view."),
        LiveEvidenceCheckTemplate("archive_present_honest_status", "WARC/WACZ/archive outputs are present or honestly labelled partial/experimental."),
        LiveEvidenceCheckTemplate("media_registered", "Image/video/media candidates are registered in media outputs."),
        LiveEvidenceCheckTemplate("media_status_recorded", "Downloaded media, skipped media, and failed media have explicit status records."),
        LiveEvidenceCheckTemplate("source_chain_separated", "MSN republisher, visible publisher/source, media credit, original-source claim, and source-chain gaps are separated."),
        LiveEvidenceCheckTemplate("final_reports_present", "Final validation, acceptance, done-gate, reconciliation, lock, seal, or promotion reports are present."),
        LiveEvidenceCheckTemplate("no_false_complete_claim", "No COMPLETE state is claimed from no-network self-tests alone."),
    ]


def build_template(
    *,
    target_url: str = "",
    article_output_folder: str = "",
    operator: str = "",
    checked_at_utc: str | None = None,
) -> LiveEvidenceTemplate:
    if checked_at_utc is None:
        checked_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return LiveEvidenceTemplate(
        schema_version=SCHEMA_VERSION,
        artifact_kind=ARTIFACT_KIND,
        target_url=target_url,
        article_output_folder=article_output_folder,
        operator=operator,
        checked_at_utc=checked_at_utc,
        operator_signed=False,
        checks=default_checks(),
    )


def _json_default(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(f"Object is not JSON serializable: {type(value)!r}")


def write_template(output_dir: Path, *, target_url: str = "", article_output_folder: str = "", operator: str = "") -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    template = build_template(target_url=target_url, article_output_folder=article_output_folder, operator=operator)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_TEMPLATE.json"
    markdown_path = output_dir / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_TEMPLATE.md"
    json_path.write_text(json.dumps(template, default=_json_default, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# MSN Source Adapter Live Evidence Template",
        "",
        f"Target URL: {target_url or '(fill after manual/live run)'}",
        f"Output folder: {article_output_folder or '(fill after manual/live run)'}",
        "",
        "Set `operator_signed` to `true` only after checking the required live outputs.",
        "",
        "| Check | Required | Status | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for check in template.checks:
        lines.append(f"| `{check.check_id}` | {str(check.required).lower()} | `{check.status}` | {check.label} |")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path), "checks": len(template.checks)}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a fillable MSN source adapter live-evidence template.")
    parser.add_argument("--output-dir", required=True, help="Directory where the template files will be written.")
    parser.add_argument("--target-url", default="", help="MSN URL tested by the operator.")
    parser.add_argument("--article-output-folder", default="", help="Existing MSN output folder inspected by the operator.")
    parser.add_argument("--operator", default="", help="Operator name or initials.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_template(
        Path(args.output_dir),
        target_url=args.target_url,
        article_output_folder=args.article_output_folder,
        operator=args.operator,
    )
    print("MSN live evidence template written:")
    print(f"json: {result['json']}")
    print(f"markdown: {result['markdown']}")
    print(f"checks: {result['checks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
