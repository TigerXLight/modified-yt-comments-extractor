#!/usr/bin/env python3
"""User-goal traceability report for the MSN source adapter.

This module is no-network. It maps the original user goal to repository-side
artifacts and output-evidence expectations. It does not claim live MSN
completion; positive live evidence is required for final signoff.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

STATUS_COVERED = "COVERED"
STATUS_PARTIAL = "PARTIAL"
STATUS_MISSING = "MISSING"


@dataclass(frozen=True)
class GoalTrace:
    goal_id: str
    user_goal: str
    status: str
    repo_artifacts: List[str]
    present_artifacts: List[str]
    missing_artifacts: List[str]
    output_evidence_patterns: List[str]
    live_evidence_required: bool
    notes: str


@dataclass(frozen=True)
class GoalTraceabilityReport:
    generated_at_utc: str
    repo_root: str
    output_root: str
    overall_state: str
    covered_goals: int
    total_goals: int
    goals: List[GoalTrace]
    boundary: str


GOALS: Sequence[tuple[str, str, Sequence[str], Sequence[str], bool, str]] = (
    (
        "article_comments_extraction",
        "Article extraction and comments/profile extraction",
        (
            "source_msn_adapter_manifest.py",
            "source_msn_adapter_total_package.py",
            "source_msn_adapter_completion_cli.py",
            "source_msn_adapter_done_gate.py",
            "source_msn_adapter_acceptance_suite.py",
        ),
        (
            "article*.json",
            "*comments*.json",
            "*profile*.json",
            "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json",
        ),
        False,
        "Repository must preserve both article-side and comments/profile-side reporting.",
    ),
    (
        "offline_webpage_viewer_archive",
        "Offline webpage viewer and archive outputs",
        (
            "source_msn_adapter_final_validator.py",
            "source_msn_adapter_done_gate.py",
            "source_msn_adapter_operator_final_runner.py",
            "source_msn_adapter_live_validation_index.py",
        ),
        (
            "rendered-page.html",
            "*.warc.gz",
            "*.wacz",
            "open_local_viewer.cmd",
        ),
        False,
        "WARC/WACZ support must be labelled honestly when replay is partial or experimental.",
    ),
    (
        "media_image_video_status",
        "Image/video discovery, download registration, and honest media status",
        (
            "source_msn_adapter_media_download_cli.py",
            "source_msn_adapter_total_package.py",
            "source_msn_adapter_final_validator.py",
            "source_msn_adapter_certification_archive.py",
        ),
        (
            "*media*.json",
            "*media*.csv",
            "*image*",
            "*video*",
        ),
        False,
        "Downloaded media should have paths and hashes; undiscovered or unsupported video should remain explicit status, not implied success.",
    ),
    (
        "source_role_provenance",
        "Source verification, source roles, and media source-chain gap preservation",
        (
            "source_msn_adapter_manifest.py",
            "source_msn_adapter_readiness.py",
            "source_msn_adapter_release_report.py",
            "source_msn_adapter_final_evidence_seal.py",
            "source_msn_adapter_final_operator_packet.py",
        ),
        (
            "*manifest*.json",
            "*provenance*.json",
            "*source*.json",
            "*evidence*.json",
        ),
        False,
        "MSN republisher, visible publisher, visible media credit, and original source must remain separate.",
    ),
    (
        "positive_live_evidence_boundary",
        "Final completion requires positive manual/live MSN evidence",
        (
            "source_msn_adapter_live_evidence_validator.py",
            "source_msn_adapter_release_promotion.py",
            "source_msn_adapter_final_promotion_closeout.py",
            "source_msn_adapter_certification_bundle.py",
            "source_msn_adapter_final_operator_packet.py",
        ),
        (
            "*LIVE*EVIDENCE*RESULT*.json",
            "*LIVE*ACCEPTANCE*RESULT*.json",
        ),
        True,
        "No-network tests can prove repository readiness, not live MSN completion.",
    ),
)


def _present(root: Path, names: Sequence[str]) -> tuple[List[str], List[str]]:
    present: List[str] = []
    missing: List[str] = []
    for name in names:
        if (root / name).exists():
            present.append(name)
        else:
            missing.append(name)
    return present, missing


def _has_output_evidence(output_root: Path, patterns: Sequence[str]) -> bool:
    if not output_root.exists():
        return False
    for pattern in patterns:
        if any(output_root.rglob(pattern)):
            return True
    return False


def build_goal_traceability(repo_root: Path, output_root: Path | None = None) -> GoalTraceabilityReport:
    repo = Path(repo_root).resolve()
    out = Path(output_root).resolve() if output_root else repo
    traces: List[GoalTrace] = []
    covered = 0
    for goal_id, user_goal, artifacts, output_patterns, live_required, notes in GOALS:
        present, missing = _present(repo, artifacts)
        artifact_ratio = len(present) / max(1, len(artifacts))
        has_output = _has_output_evidence(out, output_patterns)
        if not missing and (has_output or live_required):
            status = STATUS_COVERED
        elif artifact_ratio >= 0.6:
            status = STATUS_PARTIAL
        else:
            status = STATUS_MISSING
        if status == STATUS_COVERED:
            covered += 1
        traces.append(
            GoalTrace(
                goal_id=goal_id,
                user_goal=user_goal,
                status=status,
                repo_artifacts=list(artifacts),
                present_artifacts=present,
                missing_artifacts=missing,
                output_evidence_patterns=list(output_patterns),
                live_evidence_required=live_required,
                notes=notes,
            )
        )
    if any(t.status == STATUS_MISSING for t in traces):
        overall = "GOAL_TRACEABILITY_MISSING_ARTIFACTS"
    elif any(t.status == STATUS_PARTIAL for t in traces):
        overall = "GOAL_TRACEABILITY_PARTIAL"
    else:
        overall = "GOAL_TRACEABILITY_READY"
    return GoalTraceabilityReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        repo_root=str(repo),
        output_root=str(out),
        overall_state=overall,
        covered_goals=covered,
        total_goals=len(traces),
        goals=traces,
        boundary="Positive manual/live evidence is required before final live MSN COMPLETE/SIGNED_OFF wording.",
    )


def write_goal_traceability(report: GoalTraceabilityReport, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "MSN_SOURCE_ADAPTER_USER_GOAL_TRACEABILITY.json"
    md_path = out_dir / "MSN_SOURCE_ADAPTER_USER_GOAL_TRACEABILITY.md"
    csv_path = out_dir / "MSN_SOURCE_ADAPTER_USER_GOAL_TRACEABILITY.csv"
    json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# MSN Source Adapter User Goal Traceability",
        "",
        f"Generated: `{report.generated_at_utc}`",
        f"Overall state: `{report.overall_state}`",
        f"Covered goals: `{report.covered_goals}/{report.total_goals}`",
        "",
        report.boundary,
        "",
        "| Goal | Status | Present | Missing |",
        "|---|---:|---:|---:|",
    ]
    for goal in report.goals:
        lines.append(f"| {goal.user_goal} | `{goal.status}` | {len(goal.present_artifacts)} | {len(goal.missing_artifacts)} |")
    lines.extend(["", "## Notes", ""])
    for goal in report.goals:
        lines.append(f"- `{goal.goal_id}`: {goal.notes}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["goal_id", "user_goal", "status", "present_count", "missing_count", "live_evidence_required"])
        for goal in report.goals:
            writer.writerow([goal.goal_id, goal.user_goal, goal.status, len(goal.present_artifacts), len(goal.missing_artifacts), goal.live_evidence_required])
    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MSN user-goal traceability report.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--out", default="msn_goal_traceability_out")
    args = parser.parse_args()
    report = build_goal_traceability(Path(args.repo_root), Path(args.output_root) if args.output_root else None)
    paths = write_goal_traceability(report, Path(args.out))
    print(f"MSN goal traceability state: {report.overall_state}")
    for key, value in paths.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
