from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

REQUIRED_LIVE_CHECKS = (
    "article_extraction",
    "comments_extraction",
    "profile_export",
    "offline_viewer",
    "warc_or_archive",
    "media_discovery",
    "source_chain_preserved",
)

BINDER_JSON = "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER.json"
BINDER_MD = "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER.md"
BINDER_CSV = "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER_FILES.csv"
BINDER_NOTES = "MSN_SOURCE_ADAPTER_LIVE_RUN_BINDER_NOTES.txt"

POSITIVE_VALUES = {"true", "yes", "pass", "passed", "ok", "complete", "present", "positive"}
NEGATIVE_VALUES = {"false", "no", "fail", "failed", "blocked", "missing", "negative"}

KNOWN_REPORT_PATTERNS = (
    "MSN_*REPORT*.json",
    "MSN_*REPORT*.md",
    "MSN_*CHECKS*.csv",
    "MSN_*LEDGER*.json",
    "MSN_*LEDGER*.md",
    "MSN_*LOCK*.json",
    "MSN_*LOCK*.md",
    "MSN_*CERTIFICATION*.json",
    "MSN_*CERTIFICATION*.md",
    "MSN_*EVIDENCE*.json",
    "MSN_*EVIDENCE*.md",
    "MSN_*ARCHIVE*.json",
    "MSN_*ARCHIVE*.md",
    "media*.json",
    "media*.csv",
    "comments*.json",
    "comments*.md",
    "profiles*.json",
    "profiles*.csv",
    "rendered-page.html",
    "*.warc.gz",
    "*.wacz",
)

LIVE_EVIDENCE_NAMES = (
    "MSN_LIVE_ACCEPTANCE_RESULT.json",
    "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json",
    "MSN_SOURCE_ADAPTER_FINAL_LIVE_EVIDENCE.json",
    "02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json",
)

@dataclass
class BinderFile:
    path: str
    size: int
    sha256: str
    category: str

@dataclass
class LiveEvidence:
    found: bool
    path: str | None
    positive: bool
    blocked: bool
    checks: dict[str, str]
    missing_checks: list[str]
    notes: list[str]

@dataclass
class BinderReport:
    root: str
    output_dir: str
    status: str
    live_evidence: LiveEvidence
    files: list[BinderFile]
    summary: dict[str, Any]
    warnings: list[str]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalise_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "missing"
    return str(value).strip().lower().replace(" ", "_")


def _extract_checks(data: Any) -> dict[str, str]:
    checks: dict[str, str] = {}
    if not isinstance(data, dict):
        return checks

    direct = data.get("checks") or data.get("live_checks") or data.get("required_checks")
    if isinstance(direct, dict):
        for key, value in direct.items():
            checks[str(key)] = _normalise_value(value)
    elif isinstance(direct, list):
        for item in direct:
            if isinstance(item, dict):
                key = item.get("id") or item.get("name") or item.get("check") or item.get("area")
                value = item.get("status") if "status" in item else item.get("passed")
                if key:
                    checks[str(key)] = _normalise_value(value)

    # Accept common flat fields in filled templates.
    for key in REQUIRED_LIVE_CHECKS:
        if key in data:
            checks[key] = _normalise_value(data[key])

    aliases = {
        "article": "article_extraction",
        "comments": "comments_extraction",
        "profiles": "profile_export",
        "profile": "profile_export",
        "viewer": "offline_viewer",
        "archive": "warc_or_archive",
        "warc": "warc_or_archive",
        "media": "media_discovery",
        "source_chain": "source_chain_preserved",
        "source_role": "source_chain_preserved",
    }
    for source, target in aliases.items():
        if source in data and target not in checks:
            checks[target] = _normalise_value(data[source])

    return checks


def _find_live_evidence(root: Path) -> LiveEvidence:
    candidates: list[Path] = []
    for name in LIVE_EVIDENCE_NAMES:
        candidates.extend(root.rglob(name))
    candidates.extend(root.rglob("*LIVE*EVIDENCE*.json"))
    candidates.extend(root.rglob("*LIVE*ACCEPTANCE*RESULT*.json"))
    unique = []
    seen = set()
    for path in candidates:
        key = str(path.resolve())
        if key not in seen and path.is_file():
            unique.append(path)
            seen.add(key)
    unique.sort(key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)

    if not unique:
        return LiveEvidence(False, None, False, False, {}, list(REQUIRED_LIVE_CHECKS), ["No live evidence result JSON found."])

    path = unique[0]
    data = _safe_read_json(path)
    checks = _extract_checks(data)
    missing = [key for key in REQUIRED_LIVE_CHECKS if key not in checks]
    values = {_normalise_value(v) for v in checks.values()}
    blocked = bool(values & NEGATIVE_VALUES) or bool(missing)
    positive = not blocked and all(_normalise_value(checks.get(key)) in POSITIVE_VALUES for key in REQUIRED_LIVE_CHECKS)
    notes: list[str] = []
    if missing:
        notes.append("Missing required checks: " + ", ".join(missing))
    if values & NEGATIVE_VALUES:
        notes.append("Negative/blocking live check values found.")
    if positive:
        notes.append("Positive live evidence satisfied required checks.")
    return LiveEvidence(True, str(path), positive, blocked, checks, missing, notes)


def _categorise(path: Path) -> str:
    name = path.name.lower()
    if "comment" in name:
        return "comments"
    if "profile" in name:
        return "profiles"
    if "media" in name or name.endswith((".jpg", ".jpeg", ".png", ".webp", ".mp4", ".m3u8", ".mpd")):
        return "media"
    if name.endswith(".warc.gz") or name.endswith(".wacz") or "archive" in name:
        return "archive"
    if name.endswith(".html") or "viewer" in name:
        return "offline_viewer"
    if "source" in name or "provenance" in name or "evidence" in name:
        return "source_chain"
    if "report" in name or "lock" in name or "ledger" in name or "certification" in name:
        return "report"
    return "other"


def _iter_candidate_files(root: Path) -> Iterable[Path]:
    yielded: set[str] = set()
    for pattern in KNOWN_REPORT_PATTERNS:
        for path in root.rglob(pattern):
            if path.is_file():
                key = str(path.resolve())
                if key not in yielded:
                    yielded.add(key)
                    yield path


def build_live_run_binder(root: Path, output_dir: Path) -> BinderReport:
    root = root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    live = _find_live_evidence(root)
    files: list[BinderFile] = []
    warnings: list[str] = []
    for path in sorted(_iter_candidate_files(root), key=lambda p: str(p.relative_to(root)).lower()):
        try:
            files.append(BinderFile(str(path.relative_to(root)), path.stat().st_size, _sha256(path), _categorise(path)))
        except Exception as exc:
            warnings.append(f"Could not hash {path}: {exc}")

    categories: dict[str, int] = {}
    for item in files:
        categories[item.category] = categories.get(item.category, 0) + 1

    if live.positive:
        status = "BINDER_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
    elif live.found and live.blocked:
        status = "BINDER_BLOCKED"
    else:
        status = "BINDER_PENDING_LIVE_EVIDENCE"

    summary = {
        "file_count": len(files),
        "categories": categories,
        "has_article_or_viewer": categories.get("offline_viewer", 0) > 0,
        "has_comments": categories.get("comments", 0) > 0,
        "has_profiles": categories.get("profiles", 0) > 0,
        "has_archive": categories.get("archive", 0) > 0,
        "has_media": categories.get("media", 0) > 0,
        "has_source_chain": categories.get("source_chain", 0) > 0,
    }

    report = BinderReport(str(root), str(output_dir), status, live, files, summary, warnings)
    _write_outputs(report, output_dir)
    return report


def _write_outputs(report: BinderReport, output_dir: Path) -> None:
    data = asdict(report)
    (output_dir / BINDER_JSON).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = [
        "# MSN Source Adapter Live Run Binder",
        "",
        f"Status: `{report.status}`",
        "",
        f"Root: `{report.root}`",
        f"Files indexed: {len(report.files)}",
        "",
        "## Live evidence",
        "",
        f"Found: {report.live_evidence.found}",
        f"Positive: {report.live_evidence.positive}",
        f"Blocked: {report.live_evidence.blocked}",
        f"Path: `{report.live_evidence.path or ''}`",
        "",
        "## Required checks",
        "",
    ]
    for key in REQUIRED_LIVE_CHECKS:
        rows.append(f"- {key}: {report.live_evidence.checks.get(key, 'missing')}")
    rows.extend(["", "## Category counts", ""])
    for key, value in sorted(report.summary.get("categories", {}).items()):
        rows.append(f"- {key}: {value}")
    if report.warnings:
        rows.extend(["", "## Warnings", ""])
        rows.extend(f"- {warning}" for warning in report.warnings)
    (output_dir / BINDER_MD).write_text("\n".join(rows) + "\n", encoding="utf-8")

    with (output_dir / BINDER_CSV).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "size", "sha256", "category"])
        writer.writeheader()
        for item in report.files:
            writer.writerow(asdict(item))

    notes = [
        "MSN live run binder notes",
        "No real MSN COMPLETE claim is allowed unless status is BINDER_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE.",
        "MSN captured surface, visible publisher/source credit, media credit, and original-source status must remain separate.",
    ]
    (output_dir / BINDER_NOTES).write_text("\n".join(notes) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a final MSN live-run binder for an existing MSN output folder.")
    parser.add_argument("--root", required=True, help="Existing MSN output folder to scan.")
    parser.add_argument("--out", required=True, help="Output binder folder.")
    args = parser.parse_args(argv)
    report = build_live_run_binder(Path(args.root), Path(args.out))
    print("MSN live run binder status:", report.status)
    print("JSON:", Path(args.out) / BINDER_JSON)
    print("Markdown:", Path(args.out) / BINDER_MD)
    print("CSV:", Path(args.out) / BINDER_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
