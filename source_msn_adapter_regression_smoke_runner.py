from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DEFAULT_TESTS = [
    "source_msn_adapter_manifest_test.py",
    "source_msn_adapter_readiness_test.py",
    "source_msn_adapter_release_report_test.py",
    "source_msn_adapter_final_validator_test.py",
    "source_msn_adapter_media_download_cli_test.py",
    "source_msn_adapter_total_package_test.py",
    "source_msn_adapter_completion_cli_test.py",
    "source_msn_adapter_done_gate_test.py",
    "source_msn_adapter_acceptance_suite_test.py",
    "source_msn_adapter_live_result_reconciler_test.py",
    "source_msn_adapter_release_candidate_lock_test.py",
    "source_msn_adapter_release_promotion_test.py",
    "source_msn_adapter_certification_bundle_test.py",
    "source_msn_adapter_operator_health_dashboard_test.py",
    "source_msn_adapter_live_run_binder_test.py",
    "source_msn_adapter_final_operator_checkpoint_test.py",
    "source_msn_adapter_maintenance_guard_test.py",
    "source_msn_adapter_stewardship_report_test.py",
    "source_msn_adapter_live_validation_index_test.py",
]


@dataclass(frozen=True)
class SmokeTestResult:
    test_file: str
    status: str
    returncode: Optional[int] = None
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass(frozen=True)
class SmokeReport:
    repo: str
    output_dir: str
    execute: bool
    status: str
    results: List[SmokeTestResult] = field(default_factory=list)
    missing_tests: List[str] = field(default_factory=list)


def _tail(text: str, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def build_regression_smoke_report(repo: Path, output_dir: Path, python_exe: str = sys.executable, execute: bool = False, tests: Optional[Iterable[str]] = None) -> SmokeReport:
    repo = repo.resolve()
    output_dir = output_dir.resolve()
    selected = list(tests or DEFAULT_TESTS)
    results: List[SmokeTestResult] = []
    missing: List[str] = []
    for test in selected:
        p = repo / test
        if not p.exists():
            missing.append(test)
            results.append(SmokeTestResult(test_file=test, status="MISSING"))
            continue
        if not execute:
            results.append(SmokeTestResult(test_file=test, status="FOUND_NOT_EXECUTED"))
            continue
        completed = subprocess.run([python_exe, str(p)], cwd=str(repo), text=True, capture_output=True)
        results.append(SmokeTestResult(
            test_file=test,
            status="PASS" if completed.returncode == 0 else "FAIL",
            returncode=completed.returncode,
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        ))
    if any(r.status == "FAIL" for r in results):
        status = "FAIL"
    elif missing:
        status = "PARTIAL_MISSING_TESTS"
    elif execute:
        status = "PASS"
    else:
        status = "READY_TO_EXECUTE"
    return SmokeReport(repo=str(repo), output_dir=str(output_dir), execute=execute, status=status, results=results, missing_tests=missing)


def write_regression_smoke_report(report: SmokeReport) -> Dict[str, str]:
    out = Path(report.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_REGRESSION_SMOKE_REPORT.json"
    md_path = out / "MSN_SOURCE_ADAPTER_REGRESSION_SMOKE_REPORT.md"
    csv_path = out / "MSN_SOURCE_ADAPTER_REGRESSION_SMOKE_REPORT.csv"
    json_path.write_text(json.dumps(dataclasses.asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    md_lines = [
        "# MSN Source Adapter Regression Smoke Report",
        "",
        f"Status: **{report.status}**",
        "",
        f"Repo: `{report.repo}`",
        f"Execute mode: `{report.execute}`",
        "",
        "| Test | Status | Return code |",
        "|---|---:|---:|",
    ]
    for r in report.results:
        md_lines.append(f"| {r.test_file} | {r.status} | {'' if r.returncode is None else r.returncode} |")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_file", "status", "returncode"])
        writer.writeheader()
        for r in report.results:
            writer.writerow({"test_file": r.test_file, "status": r.status, "returncode": r.returncode})
    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run or prepare the MSN adapter regression smoke suite.")
    parser.add_argument("--repo", required=True, help="Repository root.")
    parser.add_argument("--output", required=True, help="Output report directory.")
    parser.add_argument("--python", default=sys.executable, help="Python executable.")
    parser.add_argument("--execute", action="store_true", help="Actually execute found smoke tests. Default only indexes them.")
    args = parser.parse_args(argv)
    report = build_regression_smoke_report(Path(args.repo), Path(args.output), python_exe=args.python, execute=args.execute)
    paths = write_regression_smoke_report(report)
    print("MSN regression smoke status:", report.status)
    print("JSON:", paths["json"])
    print("Markdown:", paths["markdown"])
    print("CSV:", paths["csv"])
    return 0 if report.status not in {"FAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
