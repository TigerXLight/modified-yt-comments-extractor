#!/usr/bin/env python3
"""Final artifact manifest for the MSN source adapter.

This module is intentionally no-network. It audits the repository-side MSN
adapter artifacts and writes JSON, Markdown, and CSV inventory outputs.

It does not claim live MSN completion. Live completion requires positive
manual/live evidence validated by the live evidence validator.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

STATUS_PRESENT = "PRESENT"
STATUS_MISSING = "MISSING"

BOUNDARY_STATES = [
    "READY_FOR_LIVE_EVIDENCE",
    "RC_LOCKED_PENDING_LIVE_EVIDENCE",
    "PROMOTION_BLOCKED",
    "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE",
]

EXPECTED_ARTIFACTS: Sequence[str] = (
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
    "source_msn_adapter_live_run_binder.py",
    "source_msn_adapter_final_operator_checkpoint.py",
    "source_msn_adapter_live_validation_index.py",
    "source_msn_adapter_regression_smoke_runner.py",
    "source_msn_adapter_maintenance_guard.py",
    "source_msn_adapter_stewardship_report.py",
    "source_msn_adapter_final_artifact_manifest.py",
    "source_msn_adapter_final_operator_packet.py",
    "MSN_SOURCE_ADAPTER_FINAL_STATE_LOCK.md",
    "MSN_SOURCE_ADAPTER_STATUS_WORDING_LOCK.md",
    "MSN_SOURCE_ADAPTER_COMPLETION_BOUNDARY_LOCK.md",
    "MSN_SOURCE_ADAPTER_FINAL_CONTINUATION_HANDOFF.md",
)


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    status: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ManifestReport:
    generated_at_utc: str
    repo_root: str
    total_expected: int
    present_count: int
    missing_count: int
    boundary_states: List[str]
    live_completion_boundary: str
    artifacts: List[ArtifactRecord]

    @property
    def repository_state(self) -> str:
        if self.missing_count == 0:
            return "READY_FOR_LIVE_EVIDENCE"
        return "REPO_ARTIFACTS_MISSING"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(repo_root: Path, expected: Iterable[str] = EXPECTED_ARTIFACTS) -> ManifestReport:
    root = Path(repo_root).resolve()
    records: List[ArtifactRecord] = []
    for rel in expected:
        path = root / rel
        if path.exists() and path.is_file():
            records.append(ArtifactRecord(rel, STATUS_PRESENT, path.stat().st_size, _sha256(path)))
        else:
            records.append(ArtifactRecord(rel, STATUS_MISSING, 0, ""))
    present = sum(1 for r in records if r.status == STATUS_PRESENT)
    return ManifestReport(
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        repo_root=str(root),
        total_expected=len(records),
        present_count=present,
        missing_count=len(records) - present,
        boundary_states=list(BOUNDARY_STATES),
        live_completion_boundary=(
            "Repository artifact presence is not live MSN completion. "
            "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE requires a positive manual/live evidence result."
        ),
        artifacts=records,
    )


def write_manifest(report: ManifestReport, out_dir: Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_FINAL_ARTIFACT_MANIFEST.json"
    md_path = out / "MSN_SOURCE_ADAPTER_FINAL_ARTIFACT_MANIFEST.md"
    csv_path = out / "MSN_SOURCE_ADAPTER_FINAL_ARTIFACT_MANIFEST.csv"

    data = asdict(report)
    data["repository_state"] = report.repository_state
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# MSN Source Adapter Final Artifact Manifest",
        "",
        f"- Generated UTC: `{report.generated_at_utc}`",
        f"- Repository state: `{report.repository_state}`",
        f"- Expected artifacts: `{report.total_expected}`",
        f"- Present: `{report.present_count}`",
        f"- Missing: `{report.missing_count}`",
        "",
        "## Live completion boundary",
        "",
        report.live_completion_boundary,
        "",
        "## Artifacts",
        "",
        "| Status | Path | Size | SHA256 |",
        "|---|---:|---:|---|",
    ]
    for r in report.artifacts:
        md_lines.append(f"| {r.status} | `{r.path}` | {r.size_bytes} | `{r.sha256}` |")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "status", "size_bytes", "sha256"])
        writer.writeheader()
        for r in report.artifacts:
            writer.writerow(asdict(r))

    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate final MSN artifact manifest.")
    parser.add_argument("--repo-root", default=".", help="Repository root to inspect.")
    parser.add_argument("--out-dir", default="msn_final_operator_packet", help="Output directory.")
    args = parser.parse_args(argv)

    report = build_manifest(Path(args.repo_root))
    paths = write_manifest(report, Path(args.out_dir))
    print(f"MSN final artifact manifest state: {report.repository_state}")
    print(f"JSON: {paths['json']}")
    print(f"Markdown: {paths['markdown']}")
    print(f"CSV: {paths['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
