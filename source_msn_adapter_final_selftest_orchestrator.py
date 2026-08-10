from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


PASS_STATE = "ALL_SELFTESTS_PASSED"
FAIL_STATE = "SELFTEST_FAILURES_DETECTED"
NO_TESTS_STATE = "NO_SELFTESTS_FOUND"


@dataclass(frozen=True)
class TestResult:
    path: str
    status: str
    returncode: int
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str


@dataclass(frozen=True)
class SelftestReport:
    state: str
    repo: str
    python: str
    patterns: list[str]
    total: int
    passed: int
    failed: int
    duration_seconds: float
    tests: list[TestResult]


def _tail(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def _normalised_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def discover_tests(repo: Path, patterns: Sequence[str], include_self: bool = False) -> list[Path]:
    repo = repo.resolve()
    found: dict[str, Path] = {}
    for pattern in patterns:
        for path in repo.glob(pattern):
            if not path.is_file():
                continue
            if not include_self and path.name == "source_msn_adapter_final_selftest_orchestrator_test.py":
                continue
            found[_normalised_rel(path, repo)] = path
    return [found[key] for key in sorted(found)]


def run_tests(
    repo: Path,
    tests: Sequence[Path],
    python_executable: str = sys.executable,
    fail_fast: bool = False,
    timeout_seconds: int = 120,
) -> list[TestResult]:
    results: list[TestResult] = []
    repo = repo.resolve()
    for test_path in tests:
        started = time.perf_counter()
        proc = subprocess.run(
            [python_executable, str(test_path)],
            cwd=str(repo),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        duration = time.perf_counter() - started
        result = TestResult(
            path=_normalised_rel(test_path, repo),
            status="PASSED" if proc.returncode == 0 else "FAILED",
            returncode=proc.returncode,
            duration_seconds=round(duration, 3),
            stdout_tail=_tail(proc.stdout),
            stderr_tail=_tail(proc.stderr),
        )
        results.append(result)
        if fail_fast and proc.returncode != 0:
            break
    return results


def build_report(
    repo: Path,
    patterns: Sequence[str] | None = None,
    python_executable: str = sys.executable,
    fail_fast: bool = False,
    include_self: bool = False,
    timeout_seconds: int = 120,
) -> SelftestReport:
    patterns = list(patterns or ["source_msn_adapter_*_test.py"])
    started = time.perf_counter()
    tests = discover_tests(repo, patterns, include_self=include_self)
    results = run_tests(repo, tests, python_executable, fail_fast, timeout_seconds) if tests else []
    duration = time.perf_counter() - started
    failed = sum(1 for result in results if result.returncode != 0)
    passed = sum(1 for result in results if result.returncode == 0)
    if not tests:
        state = NO_TESTS_STATE
    elif failed:
        state = FAIL_STATE
    else:
        state = PASS_STATE
    return SelftestReport(
        state=state,
        repo=str(repo.resolve()),
        python=python_executable,
        patterns=list(patterns),
        total=len(results),
        passed=passed,
        failed=failed,
        duration_seconds=round(duration, 3),
        tests=results,
    )


def write_report(report: SelftestReport, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "MSN_FINAL_SELFTEST_ORCHESTRATOR_REPORT.json"
    md_path = out_dir / "MSN_FINAL_SELFTEST_ORCHESTRATOR_REPORT.md"
    csv_path = out_dir / "MSN_FINAL_SELFTEST_ORCHESTRATOR_REPORT.csv"

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(report), handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    with md_path.open("w", encoding="utf-8") as handle:
        handle.write("# MSN Final Self-Test Orchestrator Report\n\n")
        handle.write(f"State: `{report.state}`\n\n")
        handle.write(f"Repository: `{report.repo}`\n\n")
        handle.write(f"Python: `{report.python}`\n\n")
        handle.write(f"Total: {report.total}  Passed: {report.passed}  Failed: {report.failed}\n\n")
        handle.write("## Test results\n\n")
        for result in report.tests:
            handle.write(f"- `{result.status}` `{result.path}` returncode={result.returncode} duration={result.duration_seconds}s\n")
        if report.failed:
            handle.write("\n## Failure tails\n\n")
            for result in report.tests:
                if result.returncode != 0:
                    handle.write(f"### {result.path}\n\n")
                    if result.stdout_tail:
                        handle.write("stdout tail:\n\n```text\n" + result.stdout_tail + "\n```\n\n")
                    if result.stderr_tail:
                        handle.write("stderr tail:\n\n```text\n" + result.stderr_tail + "\n```\n\n")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "status", "returncode", "duration_seconds"])
        writer.writeheader()
        for result in report.tests:
            writer.writerow({
                "path": result.path,
                "status": result.status,
                "returncode": result.returncode,
                "duration_seconds": result.duration_seconds,
            })

    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MSN adapter self-tests with a strict non-zero failure boundary.")
    parser.add_argument("--repo", default=".", help="Repository root to test.")
    parser.add_argument("--out", default="reports/msn_final_selftests", help="Output directory for JSON/Markdown/CSV reports.")
    parser.add_argument("--pattern", action="append", help="Glob pattern to discover tests. May be repeated.")
    parser.add_argument("--python", default=sys.executable, help="Python executable used to run each test file.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop after the first failing test.")
    parser.add_argument("--include-self", action="store_true", help="Include the orchestrator self-test in discovery.")
    parser.add_argument("--timeout-seconds", type=int, default=120, help="Per-test timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    patterns = args.pattern or ["source_msn_adapter_*_test.py"]
    report = build_report(
        repo=Path(args.repo),
        patterns=patterns,
        python_executable=args.python,
        fail_fast=args.fail_fast,
        include_self=args.include_self,
        timeout_seconds=args.timeout_seconds,
    )
    paths = write_report(report, Path(args.out))
    print(f"MSN final self-test orchestrator state: {report.state}")
    print(f"JSON: {paths['json']}")
    print(f"Markdown: {paths['markdown']}")
    print(f"CSV: {paths['csv']}")
    return 0 if report.state == PASS_STATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
