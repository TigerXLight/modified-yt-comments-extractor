
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_ARTIFACTS = [
    "source_msn_adapter_manifest.py",
    "source_msn_adapter_readiness.py",
    "source_msn_adapter_release_report.py",
    "source_msn_adapter_final_validator.py",
    "source_msn_adapter_media_download_cli.py",
    "source_msn_adapter_total_package.py",
    "source_msn_adapter_completion_cli.py",
    "source_msn_adapter_done_gate.py",
    "source_msn_adapter_acceptance_suite.py",
    "source_msn_adapter_operator_final_runner.py",
    "source_msn_adapter_live_result_reconciler.py",
    "source_msn_adapter_closeout_orchestrator.py",
    "source_msn_adapter_final_lock.py",
    "source_msn_adapter_final_evidence_seal.py",
    "source_msn_adapter_release_candidate_lock.py",
    "source_msn_adapter_release_promotion.py",
    "source_msn_adapter_certification_bundle.py",
    "source_msn_adapter_operator_health_dashboard.py",
    "source_msn_adapter_live_run_binder.py",
    "source_msn_adapter_live_validation_index.py",
    "source_msn_adapter_regression_smoke_runner.py",
    "source_msn_adapter_maintenance_guard.py",
    "source_msn_adapter_stewardship_report.py",
    "source_msn_adapter_final_readiness_badge.py",
]

@dataclass(frozen=True)
class ArtifactStatus:
    path: str
    status: str

@dataclass(frozen=True)
class EndStateSummary:
    status: str
    present_count: int
    missing_count: int
    artifacts: list[ArtifactStatus]
    preserved_rules: list[str]

def build_end_state_summary(repo_root: Path) -> EndStateSummary:
    artifacts = [ArtifactStatus(name, "PRESENT" if (repo_root / name).exists() else "MISSING") for name in REQUIRED_ARTIFACTS]
    missing = sum(1 for item in artifacts if item.status == "MISSING")
    status = "CHAIN_PRESENT" if missing == 0 else "CHAIN_PARTIAL"
    return EndStateSummary(
        status=status,
        present_count=len(artifacts) - missing,
        missing_count=missing,
        artifacts=artifacts,
        preserved_rules=[
            "No COMPLETE claim from no-network tests alone.",
            "Positive manual/live MSN evidence is required for final promotion.",
            "MSN republisher, visible publisher/source, media credit, and original source must remain separate.",
        ],
    )

def write_end_state_outputs(summary: EndStateSummary, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_END_STATE_SUMMARY.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_END_STATE_SUMMARY.md"
    csv_path = output_dir / "MSN_SOURCE_ADAPTER_END_STATE_ARTIFACTS.csv"
    json_path.write_text(json.dumps(asdict(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    md_lines = ["# MSN Source Adapter End-State Summary", "", f"Status: `{summary.status}`", f"Present: `{summary.present_count}`", f"Missing: `{summary.missing_count}`", "", "## Preserved rules"]
    md_lines += [f"- {rule}" for rule in summary.preserved_rules]
    md_lines += ["", "## Artifacts"]
    md_lines += [f"- `{item.status}` - `{item.path}`" for item in summary.artifacts]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "status"])
        writer.writeheader()
        for item in summary.artifacts:
            writer.writerow(asdict(item))
    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build final end-state summary for the MSN adapter chain.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    summary = build_end_state_summary(Path(args.repo_root))
    paths = write_end_state_outputs(summary, Path(args.output_dir))
    print("MSN end-state summary:", summary.status)
    print("JSON:", paths["json"])
    print("Markdown:", paths["markdown"])
    print("CSV:", paths["csv"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
