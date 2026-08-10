from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

POSITIVE_STATUSES = {
    "pass",
    "passed",
    "complete",
    "completed",
    "accepted",
    "confident",
    "confident_with_manual_review",
    "complete_with_manual_evidence",
    "ready",
    "yes",
    "true",
}
NEGATIVE_STATUSES = {
    "fail",
    "failed",
    "blocked",
    "no",
    "false",
    "missing",
    "not_present",
    "not_applicable_but_required",
    "insufficient_evidence",
}
UNCERTAIN_STATUSES = {
    "partial",
    "manual_review_required",
    "confident_with_manual_review",
    "not_applicable",
    "unknown",
    "not_checked",
    "pending",
}

AUTOMATED_REPORT_NAMES = (
    "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json",
    "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json",
    "MSN_SOURCE_ADAPTER_DONE_GATE_REPORT.json",
    "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json",
    "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json",
    "MSN_SOURCE_ADAPTER_CLOSEOUT_REPORT.json",
    "MSN_SOURCE_ADAPTER_FINAL_LOCK_REPORT.json",
    "MSN_SOURCE_ADAPTER_REGRESSION_INDEX.json",
    "MSN_SOURCE_ADAPTER_EVIDENCE_PACK_INDEX.json",
)

MANUAL_EVIDENCE_NAME_HINTS = (
    "LIVE_ACCEPTANCE_RESULT",
    "MANUAL_VALIDATION_RESULT",
    "MANUAL_LIVE_RESULT",
    "OPERATOR_ACCEPTANCE_RESULT",
    "MSN_OPERATOR_SMOKE_RESULT",
    "MSN_LIVE_EVIDENCE",
)

CORE_AREAS = (
    "article",
    "comments",
    "profiles",
    "offline_viewer",
    "archive",
    "media",
    "video",
    "source_chain",
    "provenance",
    "package",
    "reports",
)

@dataclass
class EvidenceFile:
    path: str
    kind: str
    sha256: str
    size_bytes: int
    status: str = "UNKNOWN"
    notes: list[str] = field(default_factory=list)

@dataclass
class AreaDecision:
    area: str
    status: str
    evidence: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

@dataclass
class FinalEvidenceSeal:
    adapter: str
    final_status: str
    manual_live_evidence_status: str
    automated_report_status: str
    areas: list[AreaDecision]
    evidence_files: list[EvidenceFile]
    blocking_reasons: list[str]
    warnings: list[str]
    outputs: dict[str, str]


def _normalise_status(value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value).strip().replace(" ", "_").replace("-", "_").upper()
    return text or "UNKNOWN"


def _status_bucket(value: Any) -> str:
    status = _normalise_status(value).lower()
    if status in POSITIVE_STATUSES:
        return "positive"
    if status in NEGATIVE_STATUSES:
        return "negative"
    if status in UNCERTAIN_STATUSES:
        return "uncertain"
    return "unknown"


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_read_text(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _walk_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file()]


def _find_named_reports(root: Path) -> list[Path]:
    names = set(AUTOMATED_REPORT_NAMES)
    return sorted([p for p in _walk_files(root) if p.name in names])


def _looks_like_manual_evidence(path: Path) -> bool:
    upper = path.name.upper()
    if path.suffix.lower() not in {".json", ".md", ".txt"}:
        return False
    return any(hint in upper for hint in MANUAL_EVIDENCE_NAME_HINTS)


def _find_manual_evidence(root: Path) -> list[Path]:
    return sorted([p for p in _walk_files(root) if _looks_like_manual_evidence(p)])


def _extract_json_statuses(data: Any) -> list[str]:
    statuses: list[str] = []
    if isinstance(data, Mapping):
        for key, value in data.items():
            lower = str(key).lower()
            if lower in {"status", "overall_status", "final_status", "decision", "result", "completion_status"}:
                statuses.append(_normalise_status(value))
            elif isinstance(value, (Mapping, list)):
                statuses.extend(_extract_json_statuses(value))
    elif isinstance(data, list):
        for item in data:
            statuses.extend(_extract_json_statuses(item))
    return statuses


def _extract_text_status(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("manual live pass", "operator pass", "accepted", "complete")):
        return "PASS"
    if any(token in lowered for token in ("blocked", "fail", "missing required", "insufficient evidence")):
        return "FAIL"
    if any(token in lowered for token in ("partial", "manual review", "review required")):
        return "PARTIAL"
    return "UNKNOWN"


def _classify_evidence_file(path: Path, kind: str) -> EvidenceFile:
    data = _safe_read_json(path) if path.suffix.lower() == ".json" else None
    statuses = _extract_json_statuses(data) if data is not None else []
    status = statuses[0] if statuses else _extract_text_status(_safe_read_text(path))
    notes: list[str] = []
    if statuses:
        notes.append("statuses=" + ",".join(statuses[:8]))
    return EvidenceFile(
        path=str(path),
        kind=kind,
        sha256=_sha256(path),
        size_bytes=path.stat().st_size,
        status=_normalise_status(status),
        notes=notes,
    )


def _text_blob_for(root: Path) -> str:
    interesting_suffixes = {".json", ".md", ".txt", ".csv", ".html", ".htm"}
    chunks: list[str] = []
    for path in _walk_files(root):
        if path.suffix.lower() in interesting_suffixes and path.stat().st_size <= 2_000_000:
            chunks.append(path.name.lower())
            chunks.append(_safe_read_text(path, limit=100_000).lower())
    return "\n".join(chunks)


def _area_decisions(root: Path, reports: list[EvidenceFile], manual: list[EvidenceFile]) -> list[AreaDecision]:
    blob = _text_blob_for(root)
    decisions: list[AreaDecision] = []
    evidence_names = [Path(e.path).name for e in reports + manual]

    def decide(area: str, positive_terms: Sequence[str], required: bool = True) -> AreaDecision:
        hits = [term for term in positive_terms if term.lower() in blob]
        if hits:
            return AreaDecision(area=area, status="PASS", evidence=evidence_names[:10], notes=["matched: " + ", ".join(hits[:8])])
        if required:
            return AreaDecision(area=area, status="MANUAL_REVIEW_REQUIRED", evidence=evidence_names[:10], notes=["No direct evidence term found in scanned output files."])
        return AreaDecision(area=area, status="NOT_APPLICABLE", evidence=evidence_names[:10], notes=["Optional capability or not present in this article."])

    decisions.append(decide("article", ("article", "headline", "body", "published", "source_url")))
    decisions.append(decide("comments", ("comments", "comment_count", "parent", "reply", "source_comment_id")))
    decisions.append(decide("profiles", ("profiles", "profile_url", "followers", "account_comments", "account_likes")))
    decisions.append(decide("offline_viewer", ("offline viewer", "local viewer", "rendered-page.html", "open_local_viewer.cmd")))
    decisions.append(decide("archive", ("warc", "wacz", "archive", "replayweb")))
    decisions.append(decide("media", ("media", "image", "download", "sha256", "media_candidates")))
    decisions.append(decide("video", ("video", "hls", "dash", "stream", "poster"), required=False))
    decisions.append(decide("source_chain", ("source_chain", "source chain", "visible publisher", "republisher", "original source", "source_role")))
    decisions.append(decide("provenance", ("provenance", "primary_source_status", "capture_time", "canonical_url")))
    decisions.append(decide("package", ("total package", "package", "bundle", "manifest")))
    decisions.append(decide("reports", ("acceptance", "done gate", "final validation", "closeout", "regression")))
    return decisions


def _manual_live_status(manual_files: list[EvidenceFile]) -> tuple[str, list[str]]:
    if not manual_files:
        return "MISSING", ["No filled manual/live acceptance result file was found."]
    buckets = [_status_bucket(e.status) for e in manual_files]
    if "negative" in buckets:
        return "FAILED", ["At least one manual/live result has a failing status."]
    if "positive" in buckets:
        return "POSITIVE", ["Positive manual/live evidence was found."]
    return "PRESENT_BUT_UNCLEAR", ["Manual/live result files exist but do not contain a clear positive status."]


def _automated_status(report_files: list[EvidenceFile], areas: list[AreaDecision]) -> tuple[str, list[str]]:
    if not report_files:
        return "MISSING", ["No automated MSN adapter report files were found."]
    if any(_status_bucket(e.status) == "negative" for e in report_files):
        return "FAILED", ["At least one automated report has a failing status."]
    hard_fail = [a for a in areas if a.status == "FAIL"]
    if hard_fail:
        return "FAILED", ["One or more core areas failed: " + ", ".join(a.area for a in hard_fail)]
    review = [a for a in areas if a.status == "MANUAL_REVIEW_REQUIRED"]
    if review:
        return "CONFIDENT_WITH_MANUAL_REVIEW", ["Automated files exist, but some areas need operator evidence: " + ", ".join(a.area for a in review)]
    return "PASS", ["Automated reports and scanned outputs support all core areas."]


def build_final_evidence_seal(root: Path, output_dir: Path | None = None) -> FinalEvidenceSeal:
    root = root.resolve()
    output_dir = (output_dir or root / "reports").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    report_paths = _find_named_reports(root)
    manual_paths = _find_manual_evidence(root)
    reports = [_classify_evidence_file(p, "automated_report") for p in report_paths]
    manual = [_classify_evidence_file(p, "manual_live_evidence") for p in manual_paths]
    areas = _area_decisions(root, reports, manual)
    manual_status, manual_notes = _manual_live_status(manual)
    automated_status, automated_notes = _automated_status(reports, areas)

    blocking: list[str] = []
    warnings: list[str] = []
    warnings.extend(manual_notes)
    warnings.extend(automated_notes)

    if manual_status == "FAILED" or automated_status == "FAILED":
        final_status = "BLOCKED"
        blocking.extend([*manual_notes, *automated_notes])
    elif manual_status == "POSITIVE" and automated_status in {"PASS", "CONFIDENT_WITH_MANUAL_REVIEW"}:
        final_status = "COMPLETE_WITH_MANUAL_EVIDENCE"
    elif automated_status in {"PASS", "CONFIDENT_WITH_MANUAL_REVIEW"}:
        final_status = "CONFIDENT_WITH_MANUAL_REVIEW"
        blocking.append("Positive manual/live evidence is still required before calling real MSN operation COMPLETE.")
    elif automated_status == "MISSING":
        final_status = "INSUFFICIENT_EVIDENCE"
        blocking.append("Automated report outputs were not found.")
    else:
        final_status = "PARTIAL"
        blocking.append("One or more areas remain partial or unclear.")

    json_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.md"
    csv_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL_AREAS.csv"

    seal = FinalEvidenceSeal(
        adapter="MSN source adapter",
        final_status=final_status,
        manual_live_evidence_status=manual_status,
        automated_report_status=automated_status,
        areas=areas,
        evidence_files=[*reports, *manual],
        blocking_reasons=blocking,
        warnings=warnings,
        outputs={"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)},
    )
    _write_outputs(seal, json_path, md_path, csv_path)
    return seal


def _write_outputs(seal: FinalEvidenceSeal, json_path: Path, md_path: Path, csv_path: Path) -> None:
    json_path.write_text(json.dumps(asdict(seal), indent=2, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["area", "status", "evidence_count", "notes"])
        writer.writeheader()
        for area in seal.areas:
            writer.writerow({
                "area": area.area,
                "status": area.status,
                "evidence_count": len(area.evidence),
                "notes": " | ".join(area.notes),
            })
    lines = [
        "# MSN Source Adapter Final Evidence Seal",
        "",
        f"Final status: **{seal.final_status}**",
        f"Manual/live evidence: **{seal.manual_live_evidence_status}**",
        f"Automated reports: **{seal.automated_report_status}**",
        "",
        "## Area decisions",
        "",
        "| Area | Status | Notes |",
        "| --- | --- | --- |",
    ]
    for area in seal.areas:
        notes = "<br>".join(area.notes).replace("|", "\\|")
        lines.append(f"| {area.area} | {area.status} | {notes} |")
    lines.extend(["", "## Blocking reasons"])
    if seal.blocking_reasons:
        lines.extend(f"- {reason}" for reason in seal.blocking_reasons)
    else:
        lines.append("- None.")
    lines.extend(["", "## Evidence files"])
    if seal.evidence_files:
        for item in seal.evidence_files:
            lines.append(f"- `{Path(item.path).name}` ({item.kind}, {item.status}, sha256 `{item.sha256}`)")
    else:
        lines.append("- No report/evidence files were found.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create the final MSN adapter evidence seal from an existing output folder.")
    parser.add_argument("root", type=Path, help="Existing MSN output/package folder to scan")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for seal outputs; defaults to <root>/reports")
    args = parser.parse_args(argv)
    seal = build_final_evidence_seal(args.root, args.output_dir)
    print("MSN final evidence seal status:", seal.final_status)
    print("JSON:", seal.outputs["json"])
    print("Markdown:", seal.outputs["markdown"])
    print("CSV:", seal.outputs["csv"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
