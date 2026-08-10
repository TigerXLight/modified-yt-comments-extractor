from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

REPO_REQUIRED_FILES = [
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
]

OUTPUT_SIGNAL_NAMES = [
    "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json",
    "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json",
    "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json",
    "MSN_SOURCE_ADAPTER_COMPLETION_LEDGER.json",
    "MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.json",
    "MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT_REPORT.json",
]

POSITIVE_STATUS_VALUES = {
    "COMPLETE",
    "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE",
    "CERTIFIED_WITH_POSITIVE_LIVE_EVIDENCE",
    "PROMOTED_COMPLETE",
}

BLOCKING_STATUS_VALUES = {
    "FAIL",
    "FAILED",
    "BLOCKED",
    "PROMOTION_BLOCKED",
    "INCOMPLETE_TOOLING",
    "INSUFFICIENT_EVIDENCE",
}

LIVE_EVIDENCE_KEYWORDS = ("live", "manual", "evidence", "acceptance", "promotion")


@dataclass
class DashboardCheck:
    name: str
    status: str
    detail: str


@dataclass
class OperatorHealthDashboard:
    overall_status: str
    repo_root: str
    target_root: str
    repo_required_count: int
    repo_present_count: int
    repo_missing: list[str]
    output_signal_count: int
    output_signals_found: list[str]
    live_evidence_files_found: list[str]
    checks: list[DashboardCheck]


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _flatten_values(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _flatten_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_values(item)
    elif isinstance(value, (str, int, float, bool)):
        yield str(value)


def _file_name_mentions_live_evidence(path: Path) -> bool:
    lower = path.name.lower()
    return all(part in lower for part in ("evidence",)) and any(k in lower for k in LIVE_EVIDENCE_KEYWORDS)


def discover_live_evidence_files(target_root: Path) -> list[Path]:
    if not target_root.exists():
        return []
    found: list[Path] = []
    for path in target_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt"}:
            if _file_name_mentions_live_evidence(path):
                found.append(path)
    return sorted(found, key=lambda p: str(p).lower())


def classify_live_evidence(files: list[Path]) -> tuple[str, str]:
    if not files:
        return "MISSING", "No filled manual/live evidence file found."
    saw_positive = False
    saw_blocking = False
    details: list[str] = []
    for path in files:
        if path.suffix.lower() == ".json":
            data = _read_json(path)
            if data is None:
                details.append(f"{path.name}: unreadable JSON")
                continue
            values = {v.upper() for v in _flatten_values(data)}
            if values & POSITIVE_STATUS_VALUES:
                saw_positive = True
                details.append(f"{path.name}: positive status value found")
            if values & BLOCKING_STATUS_VALUES:
                saw_blocking = True
                details.append(f"{path.name}: blocking status value found")
        else:
            text = path.read_text(encoding="utf-8", errors="replace")[:200_000].upper()
            if any(value in text for value in POSITIVE_STATUS_VALUES):
                saw_positive = True
                details.append(f"{path.name}: positive status text found")
            if any(value in text for value in BLOCKING_STATUS_VALUES):
                saw_blocking = True
                details.append(f"{path.name}: blocking status text found")
    if saw_blocking and not saw_positive:
        return "BLOCKING", "; ".join(details) or "Blocking live-evidence status found."
    if saw_positive:
        return "POSITIVE", "; ".join(details) or "Positive live-evidence status found."
    return "PRESENT_UNDECIDED", "; ".join(details) or "Live-evidence files exist, but no positive completion status was found."


def build_dashboard(repo_root: Path, target_root: Path) -> OperatorHealthDashboard:
    repo_missing = [name for name in REPO_REQUIRED_FILES if not (repo_root / name).exists()]
    repo_present = len(REPO_REQUIRED_FILES) - len(repo_missing)
    output_signals = []
    if target_root.exists():
        for signal in OUTPUT_SIGNAL_NAMES:
            matches = list(target_root.rglob(signal))
            if matches:
                output_signals.append(signal)
    live_files = discover_live_evidence_files(target_root)
    live_status, live_detail = classify_live_evidence(live_files)

    checks = [
        DashboardCheck(
            "repo_msn_tooling",
            "PASS" if not repo_missing else "FAIL",
            f"{repo_present}/{len(REPO_REQUIRED_FILES)} required repo-side MSN files present.",
        ),
        DashboardCheck(
            "known_output_signals",
            "PASS" if output_signals else "PARTIAL",
            f"{len(output_signals)} known report/output signal files found under target root.",
        ),
        DashboardCheck("manual_live_evidence", live_status, live_detail),
    ]

    if repo_missing:
        overall = "INCOMPLETE_TOOLING"
    elif live_status == "POSITIVE":
        overall = "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
    elif live_status == "BLOCKING":
        overall = "PROMOTION_BLOCKED"
    else:
        overall = "READY_FOR_LIVE_EVIDENCE"

    return OperatorHealthDashboard(
        overall_status=overall,
        repo_root=str(repo_root),
        target_root=str(target_root),
        repo_required_count=len(REPO_REQUIRED_FILES),
        repo_present_count=repo_present,
        repo_missing=repo_missing,
        output_signal_count=len(output_signals),
        output_signals_found=output_signals,
        live_evidence_files_found=[str(path) for path in live_files],
        checks=checks,
    )


def write_dashboard(report: OperatorHealthDashboard, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "MSN_SOURCE_ADAPTER_OPERATOR_HEALTH_DASHBOARD.json"
    md_path = out_dir / "MSN_SOURCE_ADAPTER_OPERATOR_HEALTH_DASHBOARD.md"
    csv_path = out_dir / "MSN_SOURCE_ADAPTER_OPERATOR_HEALTH_DASHBOARD.csv"

    payload = asdict(report)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# MSN Source Adapter Operator Health Dashboard",
        "",
        f"Overall status: `{report.overall_status}`",
        "",
        f"Repo root: `{report.repo_root}`",
        f"Target root: `{report.target_root}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in report.checks:
        detail = check.detail.replace("|", "\\|")
        lines.append(f"| {check.name} | {check.status} | {detail} |")
    lines.extend(["", "## Missing repo files", ""])
    if report.repo_missing:
        lines.extend(f"- `{name}`" for name in report.repo_missing)
    else:
        lines.append("None.")
    lines.extend(["", "## Live evidence files found", ""])
    if report.live_evidence_files_found:
        lines.extend(f"- `{path}`" for path in report.live_evidence_files_found)
    else:
        lines.append("None found. This is expected before the manual/live evidence step is completed.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        for check in report.checks:
            writer.writerow({"check": check.name, "status": check.status, "detail": check.detail})

    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a conservative MSN operator health dashboard.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--target-root", default=".")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    target_root = Path(args.target_root).resolve()
    out_dir = Path(args.out).resolve() if args.out else target_root / "reports"
    report = build_dashboard(repo_root, target_root)
    paths = write_dashboard(report, out_dir)
    print(f"MSN operator health dashboard status: {report.overall_status}")
    for key, value in paths.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
