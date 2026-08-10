from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "2026-08-10.1"
ARTIFACT_KIND = "msn_source_adapter_final_promotion_closeout"
PASS_STATUSES = {"PASS", "PASSED", "OK", "TRUE", "YES", "COMPLETE"}
FAIL_STATUSES = {"FAIL", "FAILED", "FALSE", "NO", "BLOCKED"}
REQUIRED_LIVE_CHECKS = [
    "article_extracted",
    "comments_exported",
    "profiles_exported",
    "offline_html_viewer",
    "archive_present_honest_status",
    "media_registered",
    "media_status_recorded",
    "source_chain_separated",
    "final_reports_present",
    "no_false_complete_claim",
]
EXPECTED_REPORT_NAMES = [
    "MSN_SOURCE_ADAPTER_RELEASE_PROMOTION_REPORT.json",
    "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_VALIDATION_REPORT.json",
    "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json",
    "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json",
    "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json",
    "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.json",
    "MSN_SOURCE_ADAPTER_COMPLETION_LEDGER.json",
]


@dataclass(frozen=True)
class CloseoutCheck:
    check_id: str
    label: str
    status: str
    required: bool = True
    evidence: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class FinalPromotionCloseout:
    schema_version: str
    artifact_kind: str
    generated_at_utc: str
    root: str
    decision: str
    live_evidence_status: str
    report_artifact_status: str
    required_live_checks_passed: int
    required_live_checks_total: int
    discovered_report_artifacts: List[str]
    live_evidence_files: List[str]
    checks: List[CloseoutCheck]
    summary: List[str]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalise_status(value: Any) -> str:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    return str(value or "").strip().upper().replace(" ", "_")


def _candidate_live_evidence_files(root: Path) -> List[Path]:
    names = [
        "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json",
        "MSN_SOURCE_ADAPTER_LIVE_ACCEPTANCE_RESULT.json",
        "02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json",
        "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_TEMPLATE.json",
    ]
    candidates: List[Path] = []
    for name in names:
        candidates.extend(root.rglob(name))
    for path in root.rglob("*.json"):
        lowered = path.name.lower()
        if "live" in lowered and "evidence" in lowered and "result" in lowered:
            candidates.append(path)
    unique: List[Path] = []
    seen = set()
    for path in candidates:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _extract_check_map(data: dict) -> Dict[str, str]:
    checks = data.get("checks")
    result: Dict[str, str] = {}
    if isinstance(checks, list):
        for entry in checks:
            if not isinstance(entry, dict):
                continue
            key = entry.get("check_id") or entry.get("id") or entry.get("name")
            if key:
                result[str(key)] = _normalise_status(entry.get("status") or entry.get("result") or entry.get("passed"))
    elif isinstance(checks, dict):
        for key, value in checks.items():
            if isinstance(value, dict):
                result[str(key)] = _normalise_status(value.get("status") or value.get("result") or value.get("passed"))
            else:
                result[str(key)] = _normalise_status(value)
    for key, value in data.items():
        if key in REQUIRED_LIVE_CHECKS and key not in result:
            result[key] = _normalise_status(value)
    return result


def evaluate_live_evidence(root: Path) -> tuple[str, List[Path], int, List[CloseoutCheck]]:
    files = _candidate_live_evidence_files(root)
    best_pass_count = 0
    best_checks: List[CloseoutCheck] = []
    signed_positive = False
    any_failed = False
    for path in files:
        data = _read_json(path)
        if not isinstance(data, dict):
            continue
        check_map = _extract_check_map(data)
        signed = bool(data.get("operator_signed") or data.get("operator_verified") or data.get("signed"))
        checks: List[CloseoutCheck] = []
        pass_count = 0
        fail_count = 0
        for check_id in REQUIRED_LIVE_CHECKS:
            status = check_map.get(check_id, "MISSING")
            if status in PASS_STATUSES:
                pass_count += 1
                public_status = "PASS"
            elif status in FAIL_STATUSES:
                fail_count += 1
                public_status = "FAIL"
            elif status in {"PARTIAL", "PARTIAL_PASS"}:
                public_status = "PARTIAL"
            elif status in {"N/A", "NA", "NOT_APPLICABLE"}:
                public_status = "NOT_APPLICABLE"
            else:
                public_status = "MISSING"
            checks.append(CloseoutCheck(check_id, f"Live evidence check: {check_id}", public_status, True, [str(path)]))
        if pass_count > best_pass_count:
            best_pass_count = pass_count
            best_checks = checks
        if signed and pass_count == len(REQUIRED_LIVE_CHECKS):
            signed_positive = True
            best_checks = checks
            best_pass_count = pass_count
        if fail_count:
            any_failed = True
    if not files:
        return "MISSING", [], 0, [
            CloseoutCheck(check_id, f"Live evidence check: {check_id}", "MISSING", True, [], "No live evidence file was found.")
            for check_id in REQUIRED_LIVE_CHECKS
        ]
    if signed_positive:
        return "POSITIVE", files, len(REQUIRED_LIVE_CHECKS), best_checks
    if any_failed:
        return "FAILED_OR_BLOCKED", files, best_pass_count, best_checks
    return "INCOMPLETE", files, best_pass_count, best_checks or [
        CloseoutCheck(check_id, f"Live evidence check: {check_id}", "MISSING", True, [str(files[0])])
        for check_id in REQUIRED_LIVE_CHECKS
    ]


def discover_expected_reports(root: Path) -> List[Path]:
    found: List[Path] = []
    for name in EXPECTED_REPORT_NAMES:
        matches = list(root.rglob(name))
        if matches:
            found.append(matches[0])
    return found


def build_closeout(root: Path) -> FinalPromotionCloseout:
    root = root.resolve()
    live_status, live_files, passed, live_checks = evaluate_live_evidence(root)
    report_files = discover_expected_reports(root)
    report_checks = []
    for name in EXPECTED_REPORT_NAMES:
        matches = [p for p in report_files if p.name == name]
        report_checks.append(
            CloseoutCheck(
                f"report_{name.replace('.', '_')}",
                f"Expected report artifact exists: {name}",
                "PASS" if matches else "MISSING",
                False,
                [str(p) for p in matches],
            )
        )
    report_status = "PASS" if report_files else "MISSING"
    if live_status == "POSITIVE" and passed == len(REQUIRED_LIVE_CHECKS):
        decision = "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
    elif live_status == "FAILED_OR_BLOCKED":
        decision = "PROMOTION_BLOCKED"
    elif live_status in {"MISSING", "INCOMPLETE"}:
        decision = "RC_LOCKED_PENDING_LIVE_EVIDENCE"
    else:
        decision = "INSUFFICIENT_EVIDENCE"
    summary = [
        f"Decision: {decision}",
        f"Live evidence status: {live_status}",
        f"Required live checks passed: {passed}/{len(REQUIRED_LIVE_CHECKS)}",
        f"Discovered report artifacts: {len(report_files)}/{len(EXPECTED_REPORT_NAMES)}",
    ]
    if decision != "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE":
        summary.append("Strict boundary preserved: no real MSN COMPLETE claim without positive manual/live evidence.")
    return FinalPromotionCloseout(
        schema_version=SCHEMA_VERSION,
        artifact_kind=ARTIFACT_KIND,
        generated_at_utc=_now_utc(),
        root=str(root),
        decision=decision,
        live_evidence_status=live_status,
        report_artifact_status=report_status,
        required_live_checks_passed=passed,
        required_live_checks_total=len(REQUIRED_LIVE_CHECKS),
        discovered_report_artifacts=[str(p) for p in report_files],
        live_evidence_files=[str(p) for p in live_files],
        checks=live_checks + report_checks,
        summary=summary,
    )


def write_closeout(report: FinalPromotionCloseout, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT.json"
    markdown_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT.md"
    csv_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT_CHECKS.csv"
    json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = [
        "# MSN Source Adapter Final Promotion Closeout",
        "",
        f"Decision: `{report.decision}`",
        f"Generated: `{report.generated_at_utc}`",
        f"Root: `{report.root}`",
        "",
        "## Summary",
        "",
    ]
    md.extend(f"- {item}" for item in report.summary)
    md.extend(["", "## Checks", "", "| Check | Status | Required | Evidence |", "| --- | --- | --- | --- |"])
    for check in report.checks:
        evidence = "; ".join(check.evidence) if check.evidence else ""
        md.append(f"| `{check.check_id}` | `{check.status}` | {str(check.required).lower()} | {evidence} |")
    markdown_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check_id", "label", "status", "required", "evidence", "notes"])
        writer.writeheader()
        for check in report.checks:
            writer.writerow({
                "check_id": check.check_id,
                "label": check.label,
                "status": check.status,
                "required": check.required,
                "evidence": "; ".join(check.evidence),
                "notes": check.notes,
            })
    return {"json": str(json_path), "markdown": str(markdown_path), "csv": str(csv_path), "decision": report.decision}


def run(root: Path, output_dir: Path) -> dict:
    return write_closeout(build_closeout(root), output_dir)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the final MSN source adapter promotion closeout report.")
    parser.add_argument("--root", required=True, help="Existing MSN output folder to inspect.")
    parser.add_argument("--out", required=True, help="Output directory for final promotion closeout reports.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run(Path(args.root), Path(args.out))
    print(f"MSN final promotion closeout decision: {result['decision']}")
    print(f"JSON: {result['json']}")
    print(f"Markdown: {result['markdown']}")
    print(f"CSV: {result['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
