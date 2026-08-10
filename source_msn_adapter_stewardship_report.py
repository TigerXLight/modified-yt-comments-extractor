from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from source_msn_adapter_maintenance_guard import build_maintenance_guard, write_report


@dataclass
class StewardshipReport:
    status: str
    maintenance_status: str
    preserved_boundary: str
    required_artifacts_present: int
    required_artifacts_total: int
    final_live_state_allowed: str
    repo_root: str
    report_paths: dict
    next_action: str

    def to_json_dict(self) -> dict:
        return asdict(self)


def build_stewardship_report(repo_root: Path, out_dir: Path) -> StewardshipReport:
    maintenance = build_maintenance_guard(repo_root)
    guard_paths = write_report(maintenance, out_dir / "maintenance_guard")

    if maintenance.required_missing:
        status = "BLOCKED_BY_MISSING_REPO_ARTIFACTS"
        next_action = "Restore missing MSN adapter artifacts before further roadmap work."
    else:
        status = "READY_FOR_LIVE_EVIDENCE"
        next_action = "Run live/manual MSN evidence workflow, then promotion/certification gates."

    return StewardshipReport(
        status=status,
        maintenance_status=maintenance.status,
        preserved_boundary="No COMPLETE claim without positive manual/live evidence.",
        required_artifacts_present=maintenance.required_present,
        required_artifacts_total=maintenance.total_required,
        final_live_state_allowed="COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE",
        repo_root=str(Path(repo_root).resolve()),
        report_paths=guard_paths,
        next_action=next_action,
    )


def write_stewardship_report(report: StewardshipReport, out_dir: Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_STEWARDSHIP_REPORT.json"
    md_path = out / "MSN_SOURCE_ADAPTER_STEWARDSHIP_REPORT.md"

    json_path.write_text(json.dumps(report.to_json_dict(), indent=2, sort_keys=True), encoding="utf-8")

    md = [
        "# MSN Source Adapter Stewardship Report",
        "",
        f"Status: `{report.status}`",
        f"Maintenance status: `{report.maintenance_status}`",
        f"Required artifacts: `{report.required_artifacts_present}/{report.required_artifacts_total}`",
        "",
        "## Preserved boundary",
        "",
        report.preserved_boundary,
        "",
        "## Final promoted state allowed",
        "",
        f"`{report.final_live_state_allowed}`",
        "",
        "## Next action",
        "",
        report.next_action,
        "",
        "## Nested reports",
    ]
    for key, value in report.report_paths.items():
        md.append(f"- {key}: `{value}`")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate MSN source adapter stewardship report.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--out-dir", default=None, help="Output directory.")
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    out = Path(args.out_dir).resolve() if args.out_dir else repo / "reports" / "msn_stewardship"
    report = build_stewardship_report(repo, out)
    outputs = write_stewardship_report(report, out)
    print(f"MSN stewardship status: {report.status}")
    print(f"Required: {report.required_artifacts_present}/{report.required_artifacts_total}")
    for key, value in outputs.items():
        print(f"{key}: {value}")
    return 0 if report.status == "READY_FOR_LIVE_EVIDENCE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
