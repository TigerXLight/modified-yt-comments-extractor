from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional


STATUS_PRESENT = "PRESENT"
STATUS_MISSING = "MISSING"
STATUS_OPTIONAL_MISSING = "OPTIONAL_MISSING"

FINAL_STATES = (
    "READY_FOR_LIVE_EVIDENCE",
    "RC_LOCKED_PENDING_LIVE_EVIDENCE",
    "PROMOTION_BLOCKED",
    "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE",
)


@dataclass(frozen=True)
class GuardArtifact:
    path: str
    category: str
    required: bool
    purpose: str


@dataclass
class GuardCheck:
    path: str
    category: str
    required: bool
    purpose: str
    status: str


@dataclass
class MaintenanceGuardReport:
    status: str
    total_required: int
    required_present: int
    required_missing: int
    optional_present: int
    optional_missing: int
    checks: List[GuardCheck]
    notes: List[str]

    def to_json_dict(self) -> dict:
        return {
            "status": self.status,
            "total_required": self.total_required,
            "required_present": self.required_present,
            "required_missing": self.required_missing,
            "optional_present": self.optional_present,
            "optional_missing": self.optional_missing,
            "checks": [asdict(c) for c in self.checks],
            "notes": list(self.notes),
        }


CORE_ARTIFACTS: List[GuardArtifact] = [
    GuardArtifact("source_msn_adapter_manifest.py", "provenance", True, "Manifest and source-chain data model."),
    GuardArtifact("source_msn_adapter_readiness.py", "readiness", True, "Structural readiness gate."),
    GuardArtifact("source_msn_adapter_release_report.py", "release", True, "Release report generator."),
    GuardArtifact("source_msn_adapter_final_validator.py", "validation", True, "Final bundle validator."),
    GuardArtifact("source_msn_adapter_media_download_cli.py", "media", True, "Media registration/download status workflow."),
    GuardArtifact("source_msn_adapter_total_package.py", "package", True, "Total MSN package builder."),
    GuardArtifact("source_msn_adapter_completion_cli.py", "operator", True, "Operator completion runner."),
    GuardArtifact("source_msn_adapter_manual_validation.py", "manual", True, "Manual validation intake."),
    GuardArtifact("source_msn_adapter_done_gate.py", "done_gate", True, "Done gate scanner."),
    GuardArtifact("source_msn_adapter_operator_smoke_pack.py", "operator", True, "Operator smoke pack."),
    GuardArtifact("source_msn_adapter_acceptance_suite.py", "acceptance", True, "Acceptance suite."),
    GuardArtifact("source_msn_adapter_live_acceptance_pack.py", "manual", True, "Live acceptance pack."),
    GuardArtifact("source_msn_adapter_operator_final_runner.py", "operator", True, "Final operator runner."),
    GuardArtifact("source_msn_adapter_live_result_reconciler.py", "live_evidence", True, "Live result reconciler."),
    GuardArtifact("source_msn_adapter_closeout_orchestrator.py", "closeout", True, "Closeout orchestrator."),
    GuardArtifact("source_msn_adapter_goal_matrix.py", "closeout", True, "Goal matrix."),
    GuardArtifact("source_msn_adapter_final_lock.py", "lock", True, "Final lock generator."),
    GuardArtifact("source_msn_adapter_regression_index.py", "regression", True, "Regression index."),
    GuardArtifact("source_msn_adapter_evidence_pack_index.py", "evidence", True, "Evidence pack index."),
    GuardArtifact("source_msn_adapter_completion_snapshot.py", "snapshot", True, "Completion snapshot."),
    GuardArtifact("source_msn_adapter_final_evidence_seal.py", "evidence", True, "Final evidence seal."),
    GuardArtifact("source_msn_adapter_release_candidate_ledger.py", "release_candidate", True, "Completion ledger."),
    GuardArtifact("source_msn_adapter_release_candidate_lock.py", "release_candidate", True, "Release candidate lock."),
    GuardArtifact("source_msn_adapter_live_evidence_validator.py", "live_evidence", True, "Live evidence validator."),
    GuardArtifact("source_msn_adapter_release_promotion.py", "promotion", True, "Release promotion gate."),
    GuardArtifact("source_msn_adapter_final_promotion_closeout.py", "promotion", True, "Final promotion closeout."),
    GuardArtifact("source_msn_adapter_live_evidence_template.py", "manual", True, "Fillable live evidence template."),
    GuardArtifact("source_msn_adapter_certification_bundle.py", "certification", True, "Certification bundle generator."),
    GuardArtifact("source_msn_adapter_certification_archive.py", "certification", True, "Certification archive generator."),
    GuardArtifact("source_msn_adapter_operator_quickstart.py", "operator", True, "Operator quickstart generator."),
    GuardArtifact("source_msn_adapter_post_certification_audit.py", "audit", True, "Post-certification audit."),
    GuardArtifact("source_msn_adapter_operator_health_dashboard.py", "health", True, "Operator health dashboard."),
    GuardArtifact("source_msn_adapter_final_command_index.py", "commands", True, "Final command index."),
    GuardArtifact("MSN_SOURCE_ADAPTER_STATUS_WORDING_LOCK.md", "wording", True, "Final state wording lock."),
    GuardArtifact("MSN_SOURCE_ADAPTER_FINAL_LIVE_RUN_SEQUENCE.md", "operator", True, "Live run sequence documentation."),
    GuardArtifact("MSN_SOURCE_ADAPTER_DO_NOT_REGRESS.md", "regression", True, "Do-not-regress documentation."),
    GuardArtifact("MSN_SOURCE_ADAPTER_FINAL_HANDOFF_LOCK.md", "handoff", True, "Final handoff lock documentation."),
    GuardArtifact("README.md", "repo", False, "Repository top-level README, optional for this guard."),
]


def build_maintenance_guard(repo_root: Path, artifacts: Optional[Iterable[GuardArtifact]] = None) -> MaintenanceGuardReport:
    root = Path(repo_root)
    selected = list(artifacts or CORE_ARTIFACTS)
    checks: List[GuardCheck] = []

    for item in selected:
        exists = (root / item.path).exists()
        if exists:
            status = STATUS_PRESENT
        elif item.required:
            status = STATUS_MISSING
        else:
            status = STATUS_OPTIONAL_MISSING
        checks.append(
            GuardCheck(
                path=item.path,
                category=item.category,
                required=item.required,
                purpose=item.purpose,
                status=status,
            )
        )

    required = [c for c in checks if c.required]
    optional = [c for c in checks if not c.required]
    required_present = sum(1 for c in required if c.status == STATUS_PRESENT)
    required_missing = sum(1 for c in required if c.status == STATUS_MISSING)
    optional_present = sum(1 for c in optional if c.status == STATUS_PRESENT)
    optional_missing = sum(1 for c in optional if c.status == STATUS_OPTIONAL_MISSING)

    if required_missing:
        status = "MAINTENANCE_GUARD_FAIL"
    else:
        status = "READY_FOR_LIVE_EVIDENCE"

    notes = [
        "This guard is repo-side only; it does not prove current live MSN behaviour.",
        "Do not promote to COMPLETE without positive manual/live evidence.",
        "Allowed final positive state is COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE.",
    ]
    if required_missing:
        notes.append("Required MSN adapter artifacts are missing and should be restored before further roadmap work.")

    return MaintenanceGuardReport(
        status=status,
        total_required=len(required),
        required_present=required_present,
        required_missing=required_missing,
        optional_present=optional_present,
        optional_missing=optional_missing,
        checks=checks,
        notes=notes,
    )


def write_report(report: MaintenanceGuardReport, out_dir: Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = report.to_json_dict()

    json_path = out / "MSN_SOURCE_ADAPTER_MAINTENANCE_GUARD_REPORT.json"
    md_path = out / "MSN_SOURCE_ADAPTER_MAINTENANCE_GUARD_REPORT.md"
    csv_path = out / "MSN_SOURCE_ADAPTER_MAINTENANCE_GUARD_CHECKS.csv"

    json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    md_lines = [
        "# MSN Source Adapter Maintenance Guard Report",
        "",
        f"Status: `{report.status}`",
        "",
        f"Required artifacts present: `{report.required_present}/{report.total_required}`",
        f"Required artifacts missing: `{report.required_missing}`",
        f"Optional artifacts present: `{report.optional_present}`",
        f"Optional artifacts missing: `{report.optional_missing}`",
        "",
        "## Notes",
    ]
    for note in report.notes:
        md_lines.append(f"- {note}")
    md_lines.extend(["", "## Checks", "", "| Status | Required | Category | Path | Purpose |", "|---|---:|---|---|---|"])
    for c in report.checks:
        md_lines.append(f"| {c.status} | {str(c.required).lower()} | {c.category} | `{c.path}` | {c.purpose} |")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["status", "required", "category", "path", "purpose"])
        writer.writeheader()
        for c in report.checks:
            writer.writerow(
                {
                    "status": c.status,
                    "required": str(c.required).lower(),
                    "category": c.category,
                    "path": c.path,
                    "purpose": c.purpose,
                }
            )

    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate MSN source adapter maintenance guard report.")
    parser.add_argument("--repo-root", default=".", help="Repository root to scan.")
    parser.add_argument("--out-dir", default=None, help="Output directory for reports.")
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else repo / "reports" / "msn_maintenance_guard"
    report = build_maintenance_guard(repo)
    outputs = write_report(report, out_dir)
    print(f"MSN maintenance guard status: {report.status}")
    print(f"Required: {report.required_present}/{report.total_required}")
    for key, value in outputs.items():
        print(f"{key}: {value}")
    return 0 if report.required_missing == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
