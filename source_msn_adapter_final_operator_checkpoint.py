from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

REQUIRED_REPO_ARTIFACTS = (
    "source_msn_adapter_manifest.py",
    "source_msn_adapter_readiness.py",
    "source_msn_adapter_release_report.py",
    "source_msn_adapter_final_validator.py",
    "source_msn_adapter_media_download_cli.py",
    "source_msn_adapter_total_package.py",
    "source_msn_adapter_completion_cli.py",
    "source_msn_adapter_manual_validation.py",
    "source_msn_adapter_done_gate.py",
    "source_msn_adapter_operator_smoke_pack.py",
    "source_msn_adapter_acceptance_suite.py",
    "source_msn_adapter_live_acceptance_pack.py",
    "source_msn_adapter_operator_final_runner.py",
    "source_msn_adapter_live_result_reconciler.py",
    "source_msn_adapter_closeout_orchestrator.py",
    "source_msn_adapter_goal_matrix.py",
    "source_msn_adapter_final_lock.py",
    "source_msn_adapter_regression_index.py",
    "source_msn_adapter_evidence_pack_index.py",
    "source_msn_adapter_completion_snapshot.py",
    "source_msn_adapter_final_evidence_seal.py",
    "source_msn_adapter_release_candidate_ledger.py",
    "source_msn_adapter_release_candidate_lock.py",
    "source_msn_adapter_live_evidence_validator.py",
    "source_msn_adapter_release_promotion.py",
    "source_msn_adapter_final_promotion_closeout.py",
    "source_msn_adapter_live_evidence_template.py",
    "source_msn_adapter_certification_bundle.py",
    "source_msn_adapter_certification_archive.py",
    "source_msn_adapter_operator_quickstart.py",
    "source_msn_adapter_post_certification_audit.py",
    "source_msn_adapter_operator_health_dashboard.py",
    "source_msn_adapter_final_command_index.py",
    "source_msn_adapter_maintenance_guard.py",
    "source_msn_adapter_stewardship_report.py",
    "source_msn_adapter_live_run_binder.py",
)

REQUIRED_DOC_ARTIFACTS = (
    "MSN_SOURCE_ADAPTER_STATUS_WORDING_LOCK.md",
    "MSN_SOURCE_ADAPTER_FINAL_HANDOFF_LOCK.md",
    "MSN_SOURCE_ADAPTER_DO_NOT_REGRESS.md",
    "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_WORKFLOW.md",
    "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER.md",
    "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_CHECKPOINT.md",
)

@dataclass
class CheckpointItem:
    path: str
    present: bool
    kind: str

@dataclass
class CheckpointReport:
    repo: str
    status: str
    present: int
    missing: int
    items: list[CheckpointItem]
    warnings: list[str]


def build_checkpoint(repo: Path) -> CheckpointReport:
    repo = repo.resolve()
    items: list[CheckpointItem] = []
    for path in REQUIRED_REPO_ARTIFACTS:
        items.append(CheckpointItem(path, (repo / path).exists(), "python"))
    for path in REQUIRED_DOC_ARTIFACTS:
        items.append(CheckpointItem(path, (repo / path).exists(), "doc"))

    present = sum(1 for item in items if item.present)
    missing = len(items) - present
    warnings: list[str] = []
    if not repo.exists():
        warnings.append("Repository path does not exist.")
    if not (repo / ".git").exists():
        warnings.append("Repository .git folder was not found.")

    if warnings:
        status = "CHECKPOINT_BLOCKED"
    elif missing == 0:
        status = "CHECKPOINT_READY_FOR_LIVE_EVIDENCE"
    else:
        status = "CHECKPOINT_PARTIAL_TOOLING"
    return CheckpointReport(str(repo), status, present, missing, items, warnings)


def write_checkpoint(report: CheckpointReport, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_CHECKPOINT.json").write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    lines = [
        "# MSN Source Adapter Final Operator Checkpoint",
        "",
        f"Status: `{report.status}`",
        "",
        f"Present: {report.present}",
        f"Missing: {report.missing}",
        "",
        "## Items",
        "",
    ]
    for item in report.items:
        mark = "PASS" if item.present else "MISSING"
        lines.append(f"- {mark}: `{item.path}` ({item.kind})")
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {w}" for w in report.warnings)
    (out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_CHECKPOINT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_CHECKPOINT.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "present", "kind"])
        writer.writeheader()
        for item in report.items:
            writer.writerow(asdict(item))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a final operator checkpoint for MSN adapter tooling.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report = build_checkpoint(Path(args.repo))
    write_checkpoint(report, Path(args.out))
    print("MSN final operator checkpoint status:", report.status)
    print("Present:", report.present)
    print("Missing:", report.missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
