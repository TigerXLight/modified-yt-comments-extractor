"""Promote the MSN source adapter release candidate only with live evidence.

The project can have a release-candidate lock based on no-network fixtures and
artifact structure.  This module is the final promotion gate: it keeps the
state at RC_LOCKED_PENDING_LIVE_EVIDENCE unless filled manual/live evidence is
present and accepted by source_msn_adapter_live_evidence_validator.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from source_msn_adapter_live_evidence_validator import validate_live_evidence, write_live_evidence_report


NON_FAILING_NO_NETWORK = {
    "CONFIDENT_WITH_MANUAL_REVIEW",
    "RC_LOCKED_PENDING_LIVE_EVIDENCE",
    "PASS",
    "PARTIAL",
    "COMPLETE_PENDING_LIVE_EVIDENCE",
}


@dataclass
class PromotionInputSummary:
    root: str
    no_network_reports_found: int = 0
    failing_no_network_reports: list[str] = field(default_factory=list)
    live_evidence_status: str = "NO_LIVE_EVIDENCE"
    live_evidence_file: str = ""


@dataclass
class ReleasePromotionReport:
    generated_at_utc: str
    root: str
    promotion_status: str
    summary: str
    input_summary: PromotionInputSummary
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_status(data: Any) -> str:
    if isinstance(data, dict):
        for key in ("status", "final_status", "overall_status", "promotion_status", "lock_state", "decision", "completion_status"):
            value = data.get(key)
            if value:
                return str(value).strip().upper()
        for value in data.values():
            status = _extract_status(value)
            if status:
                return status
    elif isinstance(data, list):
        for value in data:
            status = _extract_status(value)
            if status:
                return status
    return ""


def _scan_no_network_reports(root: Path) -> tuple[int, list[str]]:
    """Scan canonical no-network report JSON files without treating old run output as current.

    The MSN output folder may contain many generated strict/live evidence run folders from
    earlier attempts.  Those historical reports are useful evidence, but they must not
    block the current promotion decision after a later run has superseded them.  This scan
    therefore ignores generated/recheck/archive bundles and only evaluates canonical
    report locations that belong to the selected output folder itself.
    """
    names = (
        "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json",
        "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json",
        "MSN_SOURCE_ADAPTER_DONE_GATE_REPORT.json",
        "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json",
        "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json",
        "MSN_SOURCE_ADAPTER_CLOSEOUT_REPORT.json",
        "MSN_SOURCE_ADAPTER_FINAL_LOCK.json",
        "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.json",
        "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.json",
    )

    generated_dir_prefixes = (
        "final_msn_live_evidence",
        "live_reconciliation_recheck",
        "acceptance_recheck",
    )
    generated_dir_names = {
        "certification_archive",
        "evidence_files",
    }

    def is_generated_or_superseded(path: Path) -> bool:
        try:
            parts = [part.lower() for part in path.relative_to(root).parts[:-1]]
        except ValueError:
            return True
        for part in parts:
            if part in generated_dir_names:
                return True
            if any(part.startswith(prefix) for prefix in generated_dir_prefixes):
                return True
        return False

    found = 0
    failing: list[str] = []
    for name in names:
        for path in root.rglob(name):
            if not path.is_file():
                continue
            if is_generated_or_superseded(path):
                continue
            found += 1
            try:
                status = _extract_status(_read_json(path))
            except Exception:
                failing.append(f"{path.relative_to(root)}: unreadable")
                continue
            if status and status not in NON_FAILING_NO_NETWORK and ("FAIL" in status or "BLOCK" in status):
                failing.append(f"{path.relative_to(root)}: {status}")
    return found, failing
def build_release_promotion(root: str | Path, evidence_out_dir: str | Path | None = None) -> ReleasePromotionReport:
    root_path = Path(root).expanduser().resolve()
    live = validate_live_evidence(root_path)
    if evidence_out_dir:
        write_live_evidence_report(live, evidence_out_dir)
    reports_found, failing = _scan_no_network_reports(root_path) if root_path.exists() else (0, [])
    input_summary = PromotionInputSummary(
        root=str(root_path),
        no_network_reports_found=reports_found,
        failing_no_network_reports=failing,
        live_evidence_status=live.status,
        live_evidence_file=live.accepted_file,
    )

    warnings: list[str] = []
    next_actions: list[str] = []
    if not root_path.exists():
        return ReleasePromotionReport(
            generated_at_utc=_now(),
            root=str(root_path),
            promotion_status="INSUFFICIENT_EVIDENCE",
            summary="Cannot evaluate release promotion because the MSN output folder does not exist.",
            input_summary=input_summary,
            warnings=["No COMPLETE claim is allowed."],
            next_actions=["Provide an existing MSN output folder."],
        )
    if failing:
        return ReleasePromotionReport(
            generated_at_utc=_now(),
            root=str(root_path),
            promotion_status="BLOCKED",
            summary="No-network reports include failing/blocking status. Live evidence cannot override failing adapter artifacts.",
            input_summary=input_summary,
            warnings=failing,
            next_actions=["Fix the failing report areas, regenerate outputs, then rerun release promotion."],
        )
    if live.status == "LIVE_EVIDENCE_ACCEPTED":
        if reports_found == 0:
            warnings.append("Positive live evidence exists, but no no-network MSN report JSON files were found in this folder.")
        return ReleasePromotionReport(
            generated_at_utc=_now(),
            root=str(root_path),
            promotion_status="COMPLETE",
            summary="MSN adapter may be marked COMPLETE for this evidence folder: positive manual/live evidence passed and no failing no-network reports were found.",
            input_summary=input_summary,
            warnings=warnings,
            next_actions=["Keep the promotion report with the evidence pack and do not generalise beyond validated MSN layout families."],
        )
    if live.status == "NO_LIVE_EVIDENCE":
        next_actions.append("Run or fill the live acceptance result JSON, then rerun this promotion gate.")
        return ReleasePromotionReport(
            generated_at_utc=_now(),
            root=str(root_path),
            promotion_status="RC_LOCKED_PENDING_LIVE_EVIDENCE",
            summary="Release candidate remains locked; positive manual/live MSN evidence is still missing.",
            input_summary=input_summary,
            warnings=["No real MSN COMPLETE claim is allowed yet."],
            next_actions=next_actions,
        )
    return ReleasePromotionReport(
        generated_at_utc=_now(),
        root=str(root_path),
        promotion_status="PARTIAL",
        summary="Manual/live evidence exists but is incomplete or rejected; release cannot be promoted to COMPLETE.",
        input_summary=input_summary,
        warnings=["Required manual/live checks did not all pass."],
        next_actions=["Correct failed/missing live evidence checks and rerun."],
    )


def write_release_promotion_report(report: ReleasePromotionReport, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_RELEASE_PROMOTION_REPORT.json"
    md_path = out / "MSN_SOURCE_ADAPTER_RELEASE_PROMOTION_REPORT.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# MSN Source Adapter Release Promotion Report",
        "",
        f"Promotion status: **{report.promotion_status}**",
        "",
        report.summary,
        "",
        f"Root: `{report.root}`",
        f"Generated: `{report.generated_at_utc}`",
        "",
        "## Inputs",
        f"- No-network reports found: {report.input_summary.no_network_reports_found}",
        f"- Live evidence status: {report.input_summary.live_evidence_status}",
        f"- Accepted live evidence file: `{report.input_summary.live_evidence_file or 'none'}`",
    ]
    if report.input_summary.failing_no_network_reports:
        lines.extend(["", "## Failing no-network reports"])
        for item in report.input_summary.failing_no_network_reports:
            lines.append(f"- {item}")
    if report.warnings:
        lines.extend(["", "## Warnings"])
        for warning in report.warnings:
            lines.append(f"- {warning}")
    if report.next_actions:
        lines.extend(["", "## Next actions"])
        for action in report.next_actions:
            lines.append(f"- {action}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote MSN release candidate only when live evidence permits it.")
    parser.add_argument("--root", required=True, help="Existing MSN output folder")
    parser.add_argument("--out-dir", default=None, help="Output report directory; defaults to <root>/reports")
    args = parser.parse_args(argv)
    root = Path(args.root)
    out_dir = Path(args.out_dir) if args.out_dir else root / "reports"
    report = build_release_promotion(root, evidence_out_dir=out_dir)
    json_path, md_path = write_release_promotion_report(report, out_dir)
    print(f"MSN release promotion status: {report.promotion_status}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0 if report.promotion_status in {"COMPLETE", "RC_LOCKED_PENDING_LIVE_EVIDENCE", "PARTIAL"} else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
