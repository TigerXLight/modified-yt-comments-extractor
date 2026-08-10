from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PASS = "PASS"
FAIL = "FAIL"

REQUIRED_ARTIFACTS = [
    "source_msn_adapter_manifest.py", "source_msn_adapter_readiness.py", "source_msn_adapter_release_report.py", "source_msn_adapter_final_validator.py",
    "source_msn_adapter_media_download_cli.py", "source_msn_adapter_total_package.py", "source_msn_adapter_completion_cli.py", "source_msn_adapter_manual_validation.py",
    "source_msn_adapter_done_gate.py", "source_msn_adapter_operator_smoke_pack.py", "source_msn_adapter_acceptance_suite.py", "source_msn_adapter_live_acceptance_pack.py",
    "source_msn_adapter_operator_final_runner.py", "source_msn_adapter_live_result_reconciler.py", "source_msn_adapter_closeout_orchestrator.py", "source_msn_adapter_goal_matrix.py",
    "source_msn_adapter_final_lock.py", "source_msn_adapter_regression_index.py", "source_msn_adapter_evidence_pack_index.py", "source_msn_adapter_completion_snapshot.py",
    "source_msn_adapter_final_evidence_seal.py", "source_msn_adapter_release_candidate_ledger.py", "source_msn_adapter_release_candidate_lock.py", "source_msn_adapter_live_evidence_validator.py",
    "source_msn_adapter_release_promotion.py", "source_msn_adapter_final_promotion_closeout.py", "source_msn_adapter_live_evidence_template.py", "source_msn_adapter_certification_bundle.py",
    "source_msn_adapter_certification_archive.py", "source_msn_adapter_operator_quickstart.py",
]

REQUIRED_DOCS = [
    "MSN_SOURCE_ADAPTER_READINESS_GATE.md", "MSN_SOURCE_ADAPTER_RELEASE_VALIDATION.md", "MSN_SOURCE_ADAPTER_FINAL_VALIDATION.md", "MSN_MEDIA_DOWNLOAD_WORKFLOW.md",
    "MSN_SOURCE_ADAPTER_TOTAL_PACKAGE.md", "MSN_SOURCE_ADAPTER_COMPLETION_RUNBOOK.md", "MSN_SOURCE_ADAPTER_MANUAL_VALIDATION_INTAKE.md", "MSN_SOURCE_ADAPTER_DONE_GATE.md",
    "MSN_SOURCE_ADAPTER_GOAL_STATUS.md", "MSN_SOURCE_ADAPTER_OPERATOR_SMOKE_PACK.md", "MSN_SOURCE_ADAPTER_ACCEPTANCE_SUITE.md", "MSN_SOURCE_ADAPTER_LIVE_ACCEPTANCE_PACK.md",
    "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_RUNNER.md", "MSN_SOURCE_ADAPTER_LIVE_RESULT_RECONCILER.md", "MSN_SOURCE_ADAPTER_COMPLETION_DECISION_MATRIX.md", "MSN_SOURCE_ADAPTER_NEXT_REMAINING_WORK.md",
    "MSN_SOURCE_ADAPTER_CLOSEOUT_ORCHESTRATOR.md", "MSN_SOURCE_ADAPTER_FINAL_STATE_LOCK.md", "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_INSTRUCTIONS.md", "MSN_SOURCE_ADAPTER_FINAL_LOCK.md",
    "MSN_SOURCE_ADAPTER_REGRESSION_INDEX.md", "MSN_SOURCE_ADAPTER_EVIDENCE_PACK_INDEX.md", "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_COMMANDS.md", "MSN_SOURCE_ADAPTER_COMPLETION_SNAPSHOT.md",
    "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.md", "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.md", "MSN_SOURCE_ADAPTER_COMPLETION_LEDGER.md", "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_STATUS.md",
    "MSN_SOURCE_ADAPTER_HANDOFF_INDEX.md", "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_VALIDATOR.md", "MSN_SOURCE_ADAPTER_RELEASE_PROMOTION.md", "MSN_SOURCE_ADAPTER_FINAL_COMPLETION_GUIDE.md",
    "MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT_BUNDLE.md", "MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT_COMMANDS.md", "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_TEMPLATE.md", "MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.md",
    "MSN_SOURCE_ADAPTER_CERTIFICATION_ARCHIVE.md", "MSN_SOURCE_ADAPTER_CERTIFICATION_COMMANDS.md", "MSN_SOURCE_ADAPTER_OPERATOR_QUICKSTART.md", "MSN_SOURCE_ADAPTER_POST_CERTIFICATION_AUDIT.md",
]


@dataclass(frozen=True)
class AuditRow:
    category: str
    path: str
    status: str
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PostCertificationAudit:
    generated_at_utc: str
    repo: str
    status: str
    present_count: int
    expected_count: int
    rows: list[AuditRow]
    warnings: list[str]

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_audit(repo: Path) -> PostCertificationAudit:
    repo = repo.resolve()
    rows: list[AuditRow] = []
    for path in REQUIRED_ARTIFACTS:
        full = repo / path
        rows.append(AuditRow("python", path, PASS if full.is_file() else FAIL))
        test = repo / path.replace(".py", "_test.py")
        if path.endswith(".py") and path != "source_msn_adapter_operator_quickstart.py":
            rows.append(AuditRow("python_test", test.name, PASS if test.is_file() else FAIL))
    for path in REQUIRED_DOCS:
        full = repo / path
        rows.append(AuditRow("doc", path, PASS if full.is_file() else FAIL))
    present = sum(1 for row in rows if row.status == PASS)
    expected = len(rows)
    return PostCertificationAudit(
        generated_at_utc=_now(), repo=str(repo), status=PASS if present == expected else FAIL, present_count=present, expected_count=expected, rows=rows,
        warnings=["This is a repo artifact audit only; it does not certify a live MSN page.", "Positive manual/live evidence remains required before final COMPLETE/certified status."],
    )


def write_audit(audit: PostCertificationAudit, out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_POST_CERTIFICATION_AUDIT.json"
    md_path = out / "MSN_SOURCE_ADAPTER_POST_CERTIFICATION_AUDIT.md"
    csv_path = out / "MSN_SOURCE_ADAPTER_POST_CERTIFICATION_AUDIT.csv"
    json_path.write_text(json.dumps(audit.to_json_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_lines = ["# MSN Source Adapter Post-Certification Audit", "", f"Generated UTC: `{audit.generated_at_utc}`", f"Status: `{audit.status}`", f"Present: `{audit.present_count}/{audit.expected_count}`", "", "## Checks", "", "| Category | Path | Status |", "|---|---|---|"]
    for row in audit.rows:
        md_lines.append(f"| {row.category} | `{row.path}` | {row.status} |")
    md_lines.extend(["", "## Warnings", ""])
    md_lines.extend(f"- {warning}" for warning in audit.warnings)
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "path", "status", "notes"])
        writer.writeheader()
        for row in audit.rows:
            writer.writerow({"category": row.category, "path": row.path, "status": row.status, "notes": "; ".join(row.notes)})
    return {"json": json_path, "markdown": md_path, "csv": csv_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit MSN source adapter repo artifacts after certification/archive work.")
    parser.add_argument("--repo", required=True, help="Repository root")
    parser.add_argument("--out", required=True, help="Output folder")
    args = parser.parse_args(argv)
    audit = build_audit(Path(args.repo))
    paths = write_audit(audit, Path(args.out))
    print(f"MSN post-certification audit status: {audit.status}")
    print(f"Repo artifacts: {audit.present_count}/{audit.expected_count}")
    for key, path in paths.items():
        print(f"{key}: {path}")
    return 0 if audit.status == PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
