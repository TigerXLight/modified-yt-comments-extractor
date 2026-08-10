from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PASS = "PASS"
PARTIAL = "PARTIAL"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"

CERTIFIED_COMPLETE = "CERTIFIED_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
RC_PENDING = "RC_LOCKED_PENDING_LIVE_EVIDENCE"
PROMOTION_BLOCKED = "PROMOTION_BLOCKED"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class CertificationCheck:
    check_id: str
    label: str
    status: str
    evidence: str = ""
    required_for_complete: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CertificationBundle:
    generated_at_utc: str
    root: str
    decision: str
    summary: str
    checks: list[CertificationCheck]
    report_files: list[str]
    live_evidence_files: list[str]
    warnings: list[str]

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find(root: Path, patterns: Iterable[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        found.extend(p for p in root.rglob(pattern) if p.is_file())
    return sorted(set(found), key=lambda p: str(p).lower())


def _rel(root: Path, paths: Iterable[Path]) -> list[str]:
    out: list[str] = []
    for path in paths:
        try:
            out.append(str(path.relative_to(root)))
        except ValueError:
            out.append(str(path))
    return sorted(out)


def _contains_positive_live_evidence(path: Path) -> bool:
    data = _read_json(path)
    if not isinstance(data, dict):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        return "positive" in text and "pass" in text and "live" in text

    direct_status = str(data.get("status") or data.get("decision") or data.get("promotion_state") or "").upper()
    if any(token in direct_status for token in ("COMPLETE", "PROMOTED", "POSITIVE")) and "BLOCK" not in direct_status:
        return True

    required_keys = (
        "article_extraction",
        "comments_profile_extraction",
        "offline_viewer_archive",
        "media_registration_download_status",
        "source_chain_provenance",
    )
    checks = data.get("checks") or data.get("live_checks") or {}
    if isinstance(checks, dict):
        passed = 0
        for key in required_keys:
            value = checks.get(key)
            if isinstance(value, dict):
                value = value.get("status") or value.get("result")
            if str(value).upper() in {"PASS", "PASSED", "TRUE", "YES"}:
                passed += 1
        return passed == len(required_keys)
    if isinstance(checks, list):
        required_hits = {key: False for key in required_keys}
        for item in checks:
            if not isinstance(item, dict):
                continue
            name = str(item.get("check_id") or item.get("name") or item.get("label") or "").lower()
            status = str(item.get("status") or item.get("result") or "").upper()
            for key in required_hits:
                if key.replace("_", " ") in name or key in name:
                    if status in {"PASS", "PASSED", "TRUE", "YES"}:
                        required_hits[key] = True
        return all(required_hits.values())
    return False


def _report_decision_values(path: Path) -> list[str]:
    values: list[str] = []
    data = _read_json(path)
    if isinstance(data, dict):
        for key in ("decision", "status", "state", "promotion_state", "lock_state", "final_state"):
            value = data.get(key)
            if value:
                values.append(str(value))
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")[:20000]
        for token in (
            "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE",
            "CERTIFIED_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE",
            "RC_LOCKED_PENDING_LIVE_EVIDENCE",
            "CONFIDENT_WITH_MANUAL_REVIEW",
            "PROMOTION_BLOCKED",
        ):
            if token in text:
                values.append(token)
    return values


def build_certification_bundle(root: Path) -> CertificationBundle:
    root = root.resolve()
    report_patterns = (
        "MSN_*REPORT*.json",
        "MSN_*REPORT*.md",
        "MSN_*SUMMARY*.json",
        "MSN_*SUMMARY*.md",
        "MSN_*CLOSEOUT*.json",
        "MSN_*CLOSEOUT*.md",
        "MSN_*PROMOTION*.json",
        "MSN_*PROMOTION*.md",
        "MSN_*LOCK*.json",
        "MSN_*LOCK*.md",
    )
    report_files = _find(root, report_patterns)
    live_evidence_files = _find(root, (
        "*LIVE*EVIDENCE*.json",
        "*LIVE*ACCEPTANCE*RESULT*.json",
        "*MANUAL*VALIDATION*RESULT*.json",
        "*LIVE*EVIDENCE*.md",
        "*LIVE*ACCEPTANCE*RESULT*.md",
    ))

    article_files = _find(root, ("*article*.json", "*article*.html", "rendered-page.html"))
    comments_files = _find(root, ("*comments*.json", "*comments*.txt", "*comments*.html", "*comments*.md"))
    profile_files = _find(root, ("*profile*.json", "*profiles*.json", "*profiles*.csv", "*profile*.html"))
    archive_files = _find(root, ("*.warc", "*.warc.gz", "*.wacz", "open_local_viewer.cmd", "*local_viewer*.html"))
    media_files = _find(root, ("*media*.json", "*media*.csv", "*.jpg", "*.jpeg", "*.png", "*.webp", "*.gif", "*.mp4", "*.webm", "*.m3u8", "*.mpd"))
    source_chain_files = _find(root, ("*source*chain*.json", "*source*role*.json", "*provenance*.json", "*manifest*.json"))

    positive_live = any(_contains_positive_live_evidence(path) for path in live_evidence_files)
    decision_values: list[str] = []
    for path in report_files[:50]:
        decision_values.extend(_report_decision_values(path))
    decision_blob = " ".join(decision_values).upper()

    checks: list[CertificationCheck] = [
        CertificationCheck("article", "Article extraction output present", PASS if article_files else FAIL, "; ".join(_rel(root, article_files[:5]))),
        CertificationCheck("comments", "Comments export output present", PASS if comments_files else FAIL, "; ".join(_rel(root, comments_files[:5]))),
        CertificationCheck("profiles", "Profile export output present", PASS if profile_files else PARTIAL, "; ".join(_rel(root, profile_files[:5]))),
        CertificationCheck("archive", "Offline viewer/archive output present", PASS if archive_files else PARTIAL, "; ".join(_rel(root, archive_files[:5]))),
        CertificationCheck("media", "Media candidates/download status output present", PASS if media_files else PARTIAL, "; ".join(_rel(root, media_files[:5]))),
        CertificationCheck("source_chain", "Source-role/provenance output present", PASS if source_chain_files else PARTIAL, "; ".join(_rel(root, source_chain_files[:5]))),
        CertificationCheck("reports", "Final adapter reports present", PASS if report_files else PARTIAL, "; ".join(_rel(root, report_files[:5]))),
        CertificationCheck("live_evidence", "Positive manual/live evidence present", PASS if positive_live else FAIL, "; ".join(_rel(root, live_evidence_files[:5]))),
    ]

    warnings: list[str] = []
    if not positive_live:
        warnings.append("No positive manual/live evidence was found; certification cannot claim real MSN COMPLETE.")
    if "PROMOTION_BLOCKED" in decision_blob:
        warnings.append("A promotion-blocked report was detected in existing outputs.")
    if "RC_LOCKED_PENDING_LIVE_EVIDENCE" in decision_blob and not positive_live:
        warnings.append("Existing reports indicate release-candidate lock pending live evidence.")

    required_failed = [check for check in checks if check.required_for_complete and check.status == FAIL]
    if positive_live and not [check for check in checks if check.check_id != "live_evidence" and check.status == FAIL]:
        decision = CERTIFIED_COMPLETE
        summary = "Certification bundle found positive live evidence and required adapter outputs."
    elif "PROMOTION_BLOCKED" in decision_blob:
        decision = PROMOTION_BLOCKED
        summary = "Certification bundle found a blocked promotion state."
    elif required_failed:
        if all(check.check_id == "live_evidence" for check in required_failed):
            decision = RC_PENDING
            summary = "Release candidate remains locked pending positive live evidence."
        else:
            decision = INSUFFICIENT
            summary = "Required adapter evidence is missing."
    else:
        decision = RC_PENDING
        summary = "Adapter evidence is present but live evidence boundary prevents final COMPLETE certification."

    return CertificationBundle(
        generated_at_utc=_now(),
        root=str(root),
        decision=decision,
        summary=summary,
        checks=checks,
        report_files=_rel(root, report_files),
        live_evidence_files=_rel(root, live_evidence_files),
        warnings=warnings,
    )


def write_certification_bundle(bundle: CertificationBundle, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.json"
    md_path = out_dir / "MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.md"
    csv_path = out_dir / "MSN_SOURCE_ADAPTER_CERTIFICATION_CHECKS.csv"

    json_path.write_text(json.dumps(bundle.to_json_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# MSN Source Adapter Certification Bundle",
        "",
        f"Generated: `{bundle.generated_at_utc}`",
        f"Root: `{bundle.root}`",
        f"Decision: **{bundle.decision}**",
        "",
        bundle.summary,
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "|---|---:|---|",
    ]
    for check in bundle.checks:
        evidence = check.evidence.replace("|", "\\|") if check.evidence else ""
        lines.append(f"| {check.label} | {check.status} | {evidence} |")
    if bundle.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in bundle.warnings)
    lines.extend(["", "## Live-evidence boundary", "", "A real MSN COMPLETE claim requires positive manual/live evidence. No-network fixture tests alone keep the adapter at release-candidate status.", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["check_id", "label", "status", "required_for_complete", "evidence", "notes"])
        writer.writeheader()
        for check in bundle.checks:
            writer.writerow({
                "check_id": check.check_id,
                "label": check.label,
                "status": check.status,
                "required_for_complete": check.required_for_complete,
                "evidence": check.evidence,
                "notes": "; ".join(check.notes),
            })

    return {"json": json_path, "markdown": md_path, "csv": csv_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build final MSN source adapter certification bundle.")
    parser.add_argument("--root", required=True, type=Path, help="Existing MSN output folder to scan.")
    parser.add_argument("--out", required=True, type=Path, help="Output folder for certification files.")
    args = parser.parse_args(argv)

    bundle = build_certification_bundle(args.root)
    paths = write_certification_bundle(bundle, args.out)
    print(f"MSN certification decision: {bundle.decision}")
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
