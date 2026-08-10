#!/usr/bin/env python3
"""Final signoff gate for MSN source adapter.

This module joins goal traceability with a conservative live evidence check. It
can sign off only when the repository goal trace is ready and positive live
evidence is present.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from source_msn_adapter_user_goal_traceability import build_goal_traceability, write_goal_traceability

STATE_READY = "GOAL_TRACEABILITY_READY"
STATE_BLOCKED = "SIGNOFF_BLOCKED_MISSING_REPO_ARTIFACTS"
STATE_PENDING = "SIGNOFF_PENDING_POSITIVE_LIVE_EVIDENCE"
STATE_SIGNED = "SIGNED_OFF_WITH_POSITIVE_LIVE_EVIDENCE"


@dataclass(frozen=True)
class SignoffCheck:
    check: str
    status: str
    detail: str


@dataclass(frozen=True)
class SignoffReport:
    generated_at_utc: str
    repo_root: str
    output_root: str
    signoff_state: str
    live_completion_allowed: bool
    checks: List[SignoffCheck]
    boundary: str


def _find_live_evidence(output_root: Path) -> Path | None:
    names = [
        "MSN_LIVE_EVIDENCE_RESULT.json",
        "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json",
        "MSN_SOURCE_ADAPTER_LIVE_ACCEPTANCE_RESULT.json",
        "02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json",
    ]
    for name in names:
        path = output_root / name
        if path.exists():
            return path
    matches = sorted(output_root.rglob("*LIVE*EVIDENCE*RESULT*.json")) + sorted(output_root.rglob("*LIVE*ACCEPTANCE*RESULT*.json"))
    return matches[0] if matches else None


def _positive_live_evidence(path: Path | None) -> tuple[bool, str]:
    if not path:
        return False, "No live evidence result file found."
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Live evidence file is not valid JSON: {exc}"
    text = json.dumps(data, ensure_ascii=False).lower()
    positive = any(token in text for token in [
        "complete_with_positive_live_evidence",
        "signed_off_with_positive_live_evidence",
        "positive_live_evidence",
        '"passed": true',
        '"pass": true',
        '"all_required_checks_passed": true',
    ])
    negative = any(token in text for token in ["blocked", "fail", "failed", "missing", "false"])
    if positive and not negative:
        return True, f"Positive live evidence found: {path}"
    return False, f"Live evidence present but not positive/pass-only: {path}"


def build_signoff_report(repo_root: Path, output_root: Path) -> SignoffReport:
    repo = Path(repo_root).resolve()
    out = Path(output_root).resolve()
    trace = build_goal_traceability(repo, out)
    checks: List[SignoffCheck] = []
    repo_ready = trace.overall_state == "GOAL_TRACEABILITY_READY"
    checks.append(SignoffCheck("goal_traceability", "PASS" if repo_ready else "PARTIAL", trace.overall_state))
    live_path = _find_live_evidence(out)
    live_positive, live_detail = _positive_live_evidence(live_path)
    checks.append(SignoffCheck("positive_live_evidence", "PASS" if live_positive else "PENDING", live_detail))
    if not repo_ready:
        state = STATE_BLOCKED
    elif live_positive:
        state = STATE_SIGNED
    else:
        state = STATE_PENDING
    return SignoffReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        repo_root=str(repo),
        output_root=str(out),
        signoff_state=state,
        live_completion_allowed=state == STATE_SIGNED,
        checks=checks,
        boundary="Final signoff requires repository goal traceability plus positive manual/live evidence. No-network self-tests alone are insufficient.",
    )


def write_signoff_report(report: SignoffReport, out_dir: Path, trace_repo: Path | None = None, trace_output: Path | None = None) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "MSN_SOURCE_ADAPTER_FINAL_SIGNOFF_GATE.json"
    md_path = out_dir / "MSN_SOURCE_ADAPTER_FINAL_SIGNOFF_GATE.md"
    csv_path = out_dir / "MSN_SOURCE_ADAPTER_FINAL_SIGNOFF_GATE.csv"
    json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# MSN Source Adapter Final Signoff Gate",
        "",
        f"Generated: `{report.generated_at_utc}`",
        f"Signoff state: `{report.signoff_state}`",
        f"Live completion allowed: `{report.live_completion_allowed}`",
        "",
        report.boundary,
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in report.checks:
        lines.append(f"| {check.check} | `{check.status}` | {check.detail} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["check", "status", "detail"])
        for check in report.checks:
            writer.writerow([check.check, check.status, check.detail])
    paths = {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}
    if trace_repo and trace_output:
        trace = build_goal_traceability(trace_repo, trace_output)
        trace_paths = write_goal_traceability(trace, out_dir)
        paths.update({f"trace_{k}": v for k, v in trace_paths.items()})
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MSN final signoff gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-root", default=".")
    parser.add_argument("--out", default="msn_final_signoff_out")
    args = parser.parse_args()
    repo = Path(args.repo_root)
    output = Path(args.output_root)
    report = build_signoff_report(repo, output)
    paths = write_signoff_report(report, Path(args.out), repo, output)
    print(f"MSN final signoff state: {report.signoff_state}")
    for key, value in paths.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
