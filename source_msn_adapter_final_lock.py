"""Final lock report for the MSN source adapter.

This module is intentionally no-network and filesystem based. It does not
claim a live MSN article is proven complete unless an operator/manual live
acceptance result is present and positive. It is the last guardrail before
calling the MSN source adapter done for real-world use.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


COMPLETE = "COMPLETE"
LOCKED_WITH_LIVE_REVIEW = "LOCKED_WITH_LIVE_REVIEW"
READY_FOR_REAL_ARTICLE_VALIDATION = "READY_FOR_REAL_ARTICLE_VALIDATION"
PARTIAL = "PARTIAL"
BLOCKED = "BLOCKED"


REQUIRED_CODE_FILES = [
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
]

REQUIRED_DOC_FILES = [
    "MSN_SOURCE_ADAPTER_FINAL_STATE_LOCK.md",
    "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_INSTRUCTIONS.md",
    "MSN_SOURCE_ADAPTER_COMPLETION_DECISION_MATRIX.md",
    "MSN_SOURCE_ADAPTER_NEXT_REMAINING_WORK.md",
    "MSN_SOURCE_ADAPTER_CLOSEOUT_ORCHESTRATOR.md",
]

OUTPUT_GROUPS = {
    "article": ["article", "rendered-page.html", "source_article"],
    "comments": ["comments", "comment"],
    "profiles": ["profiles", "profile"],
    "offline_viewer": ["local_viewer", "open_local_viewer.cmd", "rendered-page.html"],
    "archive": [".warc", ".warc.gz", ".wacz"],
    "media": ["media", "image", "video", "poster", "stream"],
    "source_chain": ["source_role", "primary_source_status", "source_chain", "visible_credit"],
    "reports": ["MSN_ADAPTER_FINAL_VALIDATION_REPORT", "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT", "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT"],
}


@dataclass
class LockCheck:
    name: str
    status: str
    detail: str
    evidence: list[str]


@dataclass
class FinalLockReport:
    generated_at_utc: str
    target_root: str
    repo_root: str
    status: str
    summary: str
    checks: list[LockCheck]
    missing_code_files: list[str]
    missing_doc_files: list[str]
    live_acceptance_result: dict[str, Any]
    output_files_sampled: int


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iter_files(root: Path, limit: int = 8000) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file():
            out.append(path)
            if len(out) >= limit:
                break
    return out


def _rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path, limit: int = 300_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _json_load(path: Path) -> Any:
    try:
        return json.loads(_read_text(path, limit=1_000_000))
    except Exception:
        return None


def _contains_any(path: Path, needles: Iterable[str]) -> bool:
    hay = (path.name + "\n" + _read_text(path, limit=200_000)).lower()
    return any(needle.lower() in hay for needle in needles)


def _find_group(files: list[Path], base: Path, needles: Iterable[str]) -> list[str]:
    hits: list[str] = []
    for path in files:
        lower_name = path.name.lower()
        lower_rel = _rel(path, base).lower()
        if any(needle.lower() in lower_name or needle.lower() in lower_rel for needle in needles):
            hits.append(_rel(path, base))
            continue
        if path.suffix.lower() in {".json", ".md", ".txt", ".html", ".csv"} and _contains_any(path, needles):
            hits.append(_rel(path, base))
    return sorted(set(hits))[:12]


def _detect_live_acceptance(files: list[Path], base: Path) -> dict[str, Any]:
    candidates = [
        p for p in files
        if p.suffix.lower() in {".json", ".md", ".txt"}
        and any(token in p.name.lower() for token in ["live_acceptance", "manual_validation", "operator_acceptance"])
    ]
    result: dict[str, Any] = {
        "present": False,
        "positive": False,
        "negative": False,
        "evidence": [],
        "note": "No filled manual/live acceptance result was found.",
    }
    for path in candidates:
        text = _read_text(path, limit=500_000).lower()
        data = _json_load(path) if path.suffix.lower() == ".json" else None
        rel = _rel(path, base)
        result["present"] = True
        result["evidence"].append(rel)
        if isinstance(data, dict):
            status = str(data.get("status") or data.get("decision") or data.get("overall_status") or "").upper()
            passed = data.get("passed") or data.get("all_required_passed") or data.get("live_passed")
            if status in {"COMPLETE", "PASS", "PASSED", "ACCEPTED"} or passed is True:
                result["positive"] = True
                result["note"] = "A positive structured manual/live acceptance result was found."
            if status in {"FAIL", "FAILED", "BLOCKED", "REJECTED"} or passed is False:
                result["negative"] = True
                result["note"] = "A negative structured manual/live acceptance result was found."
        else:
            if "complete" in text and "pass" in text and "fail" not in text:
                result["positive"] = True
                result["note"] = "A positive text manual/live acceptance result was found."
            if "blocked" in text or "failed" in text or "fail" in text:
                result["negative"] = True
                result["note"] = "A negative text manual/live acceptance result was found."
    result["evidence"] = result["evidence"][:10]
    return result


def build_final_lock_report(target_root: Path, repo_root: Path | None = None) -> FinalLockReport:
    target_root = target_root.resolve()
    repo_root = (repo_root or Path.cwd()).resolve()
    files = _iter_files(target_root)

    checks: list[LockCheck] = []
    missing_code = [name for name in REQUIRED_CODE_FILES if not (repo_root / name).exists()]
    missing_docs = [name for name in REQUIRED_DOC_FILES if not (repo_root / name).exists()]

    checks.append(LockCheck(
        name="repo_code_surface",
        status="PASS" if not missing_code else "FAIL",
        detail="All MSN adapter code modules are present." if not missing_code else f"Missing {len(missing_code)} required code module(s).",
        evidence=[name for name in REQUIRED_CODE_FILES if (repo_root / name).exists()][:20],
    ))
    checks.append(LockCheck(
        name="repo_documentation_surface",
        status="PASS" if not missing_docs else "PARTIAL",
        detail="Closeout/live-evidence documentation is present." if not missing_docs else f"Missing {len(missing_docs)} expected documentation file(s).",
        evidence=[name for name in REQUIRED_DOC_FILES if (repo_root / name).exists()][:20],
    ))

    group_passes = 0
    for group, needles in OUTPUT_GROUPS.items():
        hits = _find_group(files, target_root, needles)
        status = "PASS" if hits else "MISSING"
        if hits:
            group_passes += 1
        checks.append(LockCheck(
            name=f"output_{group}",
            status=status,
            detail=(f"Found {len(hits)} evidence file(s) for {group}." if hits else f"No {group} output evidence found under target root."),
            evidence=hits,
        ))

    live = _detect_live_acceptance(files, target_root)
    checks.append(LockCheck(
        name="manual_live_acceptance_result",
        status="PASS" if live["positive"] else ("FAIL" if live["negative"] else "MISSING"),
        detail=str(live["note"]),
        evidence=list(live["evidence"]),
    ))

    if missing_code:
        status = BLOCKED
        summary = "MSN adapter cannot be locked because required source modules are missing."
    elif live["negative"]:
        status = BLOCKED
        summary = "MSN adapter has a negative manual/live acceptance result."
    elif live["positive"] and group_passes >= len(OUTPUT_GROUPS) - 1:
        status = COMPLETE
        summary = "MSN adapter is complete against the scanned output folder and positive live/manual evidence."
    elif group_passes >= max(5, len(OUTPUT_GROUPS) - 2):
        status = LOCKED_WITH_LIVE_REVIEW
        summary = "MSN adapter is structurally locked; final live/manual evidence is still required for a complete claim."
    elif not files:
        status = READY_FOR_REAL_ARTICLE_VALIDATION
        summary = "MSN adapter code is present, but no output folder evidence was found in the target."
    else:
        status = PARTIAL
        summary = "MSN adapter evidence is partial; run the operator final runner and live acceptance pack on a real MSN bundle."

    return FinalLockReport(
        generated_at_utc=_now(),
        target_root=str(target_root),
        repo_root=str(repo_root),
        status=status,
        summary=summary,
        checks=checks,
        missing_code_files=missing_code,
        missing_doc_files=missing_docs,
        live_acceptance_result=live,
        output_files_sampled=len(files),
    )


def write_final_lock_report(report: FinalLockReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_LOCK_REPORT.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_LOCK_REPORT.md"
    payload = asdict(report)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# MSN Source Adapter Final Lock Report",
        "",
        f"- Generated: `{report.generated_at_utc}`",
        f"- Status: `{report.status}`",
        f"- Summary: {report.summary}",
        f"- Target root: `{report.target_root}`",
        f"- Repo root: `{report.repo_root}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail | Evidence sample |",
        "|---|---:|---|---|",
    ]
    for check in report.checks:
        ev = "<br>".join(f"`{item}`" for item in check.evidence[:5]) or "—"
        lines.append(f"| `{check.name}` | `{check.status}` | {check.detail} | {ev} |")
    if report.missing_code_files:
        lines.extend(["", "## Missing code files", ""])
        lines.extend(f"- `{name}`" for name in report.missing_code_files)
    if report.missing_doc_files:
        lines.extend(["", "## Missing documentation files", ""])
        lines.extend(f"- `{name}`" for name in report.missing_doc_files)
    lines.extend([
        "",
        "## Lock rule",
        "",
        "Do not mark a live MSN source adapter run as `COMPLETE` unless a positive manual/live acceptance result is present. No-network fixture tests may justify `LOCKED_WITH_LIVE_REVIEW`, not a live-complete claim.",
        "",
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the MSN source adapter final lock report.")
    parser.add_argument("--target", default=".", help="Existing MSN output folder or repo root to inspect.")
    parser.add_argument("--repo-root", default=".", help="Repository root containing MSN adapter modules.")
    parser.add_argument("--output", default=None, help="Output directory for final lock reports.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout.")
    args = parser.parse_args(argv)
    target = Path(args.target)
    repo_root = Path(args.repo_root)
    output_dir = Path(args.output) if args.output else target / "reports"
    report = build_final_lock_report(target, repo_root)
    json_path, md_path = write_final_lock_report(report, output_dir)
    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        print(f"MSN final lock status: {report.status}")
        print(f"JSON: {json_path}")
        print(f"Markdown: {md_path}")
    return 0 if report.status != BLOCKED else 2


if __name__ == "__main__":
    raise SystemExit(main())
