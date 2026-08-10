from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from source_msn_adapter_goal_matrix import (
    BLOCKED,
    COMPLETE,
    CONFIDENT_WITH_MANUAL_REVIEW,
    FAIL,
    INSUFFICIENT_EVIDENCE,
    NOT_APPLICABLE,
    PARTIAL,
    PASS,
    UNKNOWN,
    GoalMatrix,
    build_goal_matrix,
    render_goal_matrix_markdown,
)

REPORT_JSON = "MSN_SOURCE_ADAPTER_CLOSEOUT_REPORT.json"
REPORT_MD = "MSN_SOURCE_ADAPTER_CLOSEOUT_REPORT.md"
CHECKS_CSV = "MSN_SOURCE_ADAPTER_CLOSEOUT_CHECKS.csv"
ACTIONS_MD = "MSN_SOURCE_ADAPTER_CLOSEOUT_ACTIONS.md"

STATUS_RE = re.compile(r"\b(PASS|PARTIAL|FAIL|NOT_APPLICABLE|UNKNOWN|COMPLETE|CONFIDENT_WITH_MANUAL_REVIEW|BLOCKED|INSUFFICIENT_EVIDENCE)\b", re.I)
PASS_WORDS = {"pass", "passed", "true", "yes", "complete", "completed", "ok", "success"}
FAIL_WORDS = {"fail", "failed", "false", "no", "blocked", "error", "missing"}


@dataclass
class CloseoutEvidence:
    kind: str
    path: str
    size: int
    status_hint: str = UNKNOWN
    extracted_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class CloseoutCheck:
    key: str
    label: str
    status: str
    evidence: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class CloseoutReport:
    schema: str
    generated_at_utc: str
    root: str
    final_status: str
    static_status: str
    live_status: str
    goal_matrix: Dict[str, Any]
    checks: List[CloseoutCheck]
    evidence_files: List[CloseoutEvidence]
    missing_static: List[str]
    missing_live: List[str]
    blocking_reasons: List[str]
    next_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "generated_at_utc": self.generated_at_utc,
            "root": self.root,
            "final_status": self.final_status,
            "static_status": self.static_status,
            "live_status": self.live_status,
            "goal_matrix": dict(self.goal_matrix),
            "checks": [x.to_dict() for x in self.checks],
            "evidence_files": [x.to_dict() for x in self.evidence_files],
            "missing_static": list(self.missing_static),
            "missing_live": list(self.missing_live),
            "blocking_reasons": list(self.blocking_reasons),
            "next_actions": list(self.next_actions),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_read(path: Path, limit: int = 500_000) -> str:
    try:
        data = path.read_bytes()[:limit]
    except OSError:
        return ""
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def safe_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(safe_read(path, limit=2_000_000))
    except Exception:
        return None


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def all_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file()]


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return UNKNOWN
    aliases = {
        "OK": PASS,
        "PASSED": PASS,
        "SUCCESS": PASS,
        "TRUE": PASS,
        "YES": PASS,
        "COMPLETE": PASS,
        "COMPLETED": PASS,
        "CONFIDENT_WITH_MANUAL_REVIEW": PARTIAL,
        "REVIEW": PARTIAL,
        "PARTLY": PARTIAL,
        "PARTIAL_SUCCESS": PARTIAL,
        "MISSING": FAIL,
        "FALSE": FAIL,
        "NO": FAIL,
        "FAILED": FAIL,
        "BLOCKED": FAIL,
    }
    text = aliases.get(text, text)
    if text in {PASS, PARTIAL, FAIL, NOT_APPLICABLE, UNKNOWN}:
        return text
    match = STATUS_RE.search(text)
    if match:
        return normalize_status(match.group(1))
    return UNKNOWN


def flatten_strings(obj: Any, limit: int = 80_000) -> str:
    out: List[str] = []
    total = 0

    def walk(x: Any) -> None:
        nonlocal total
        if total > limit:
            return
        if isinstance(x, Mapping):
            for k, v in x.items():
                s = str(k)
                out.append(s)
                total += len(s)
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)
        elif isinstance(x, (str, int, float, bool)) or x is None:
            s = str(x)
            out.append(s)
            total += len(s)

    walk(obj)
    return "\n".join(out)


def status_hint_from_json(obj: Any) -> str:
    seen: List[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, Mapping):
            for k, v in x.items():
                key = str(k).lower()
                if key in {"status", "result", "final_status", "overall_status", "decision", "live_status", "static_status"}:
                    seen.append(str(v))
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)
        elif isinstance(x, str):
            match = STATUS_RE.search(x)
            if match:
                seen.append(match.group(1))

    walk(obj)
    statuses = [normalize_status(x) for x in seen]
    if FAIL in statuses:
        return FAIL
    if PARTIAL in statuses:
        return PARTIAL
    if PASS in statuses:
        return PASS
    if NOT_APPLICABLE in statuses:
        return NOT_APPLICABLE
    return UNKNOWN


def status_hint_from_text(text: str) -> str:
    values = [normalize_status(m.group(1)) for m in STATUS_RE.finditer(text or "")]
    if FAIL in values:
        return FAIL
    if PARTIAL in values:
        return PARTIAL
    if PASS in values:
        return PASS
    if NOT_APPLICABLE in values:
        return NOT_APPLICABLE
    return UNKNOWN


def classify_file(root: Path, path: Path) -> Optional[CloseoutEvidence]:
    name = path.name.lower()
    full = rel(root, path).lower()
    suffix = path.suffix.lower()
    kind = "other"
    if "/profiles/" in ("/" + full) or name.endswith("profiles.csv") or name.endswith("profiles.json") or name.endswith("profiles.html"):
        kind = "profiles"
    elif "/comments/" in ("/" + full) or name.startswith("msn-comments"):
        kind = "comments"
    tokens = [
        ("closeout_report", ["closeout_report", "closeout_checks", "closeout_actions"]),
        ("live_reconciliation", ["live_reconciliation", "live_result_reconciler"]),
        ("operator_final", ["operator_final_summary", "operator_final"]),
        ("acceptance", ["acceptance_report", "acceptance_checks", "acceptance_suite"]),
        ("done_gate", ["done_gate", "done-gate"]),
        ("final_validation", ["final_validation_report", "adapter_final_validation"]),
        ("completion", ["completion_summary", "completion_report"]),
        ("release", ["release_report", "release_validation"]),
        ("readiness", ["readiness_report", "readiness"]),
        ("manual_live_result", ["live_acceptance_result", "manual_validation_result", "operator_result", "manual_live_result"]),
        ("media_inventory", ["media_inventory", "media_manifest", "media-manifest", "media_download", "download_results"]),
        ("profiles", ["profiles", "profile"]),
        ("comments", ["comments", "comment"]),
        ("article", ["article", "rendered-page", "rendered_page"]),
        ("offline_viewer", ["open_local_viewer", "local_viewer"]),
        ("archive_warc", [".warc", "warc.gz"]),
        ("archive_wacz", [".wacz", "wacz"]),
    ]
    if kind == "other":
        for candidate, needles in tokens:
            if any(n in name or n in full for n in needles):
                kind = candidate
                break
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm", ".m3u8", ".mpd"}:
        kind = "downloaded_media"
    if kind == "other":
        return None

    size = path.stat().st_size
    fields: Dict[str, Any] = {}
    hint = UNKNOWN
    if suffix == ".json":
        obj = safe_json(path)
        if obj is not None:
            hint = status_hint_from_json(obj)
            if isinstance(obj, Mapping):
                fields["keys"] = sorted(str(k) for k in obj.keys())[:40]
                for k in ("final_status", "status", "decision", "overall_status", "live_status", "static_status"):
                    if k in obj:
                        fields[k] = obj[k]
            fields["json_type"] = type(obj).__name__
        else:
            hint = UNKNOWN
    elif suffix in {".md", ".txt", ".csv", ".html", ".cmd"}:
        hint = status_hint_from_text(safe_read(path, limit=150_000))
    elif kind == "downloaded_media":
        hint = PASS if size > 0 else FAIL

    return CloseoutEvidence(kind=kind, path=rel(root, path), size=size, status_hint=hint, extracted_fields=fields)


def collect_evidence(root: Path, manual_result: Optional[Path] = None) -> List[CloseoutEvidence]:
    evidence = [e for p in all_files(root) if (e := classify_file(root, p)) is not None]
    if manual_result and manual_result.exists():
        manual = classify_file(root, manual_result) if manual_result.is_relative_to(root) else None  # type: ignore[attr-defined]
        if manual is None:
            size = manual_result.stat().st_size
            obj = safe_json(manual_result)
            hint = status_hint_from_json(obj) if obj is not None else status_hint_from_text(safe_read(manual_result))
            manual = CloseoutEvidence("manual_live_result", str(manual_result), size, hint, {"external_manual_result": True})
        evidence.append(manual)
    evidence.sort(key=lambda e: (e.kind, e.path))
    return evidence


def evidence_by_kind(evidence: Sequence[CloseoutEvidence], *kinds: str) -> List[CloseoutEvidence]:
    want = set(kinds)
    return [e for e in evidence if e.kind in want]


def paths(entries: Sequence[CloseoutEvidence], limit: int = 8) -> List[str]:
    return [e.path for e in entries[:limit]]


def status_from_entries(entries: Sequence[CloseoutEvidence], require_pass_hint: bool = False) -> str:
    if not entries:
        return FAIL
    if any(e.status_hint == FAIL for e in entries):
        return FAIL
    if any(e.status_hint == PARTIAL for e in entries):
        return PARTIAL
    if require_pass_hint and not any(e.status_hint == PASS for e in entries):
        return PARTIAL
    return PASS


def status_from_presence(entries: Sequence[CloseoutEvidence]) -> str:
    if not entries:
        return FAIL
    if any(e.status_hint == FAIL for e in entries):
        return FAIL
    return PASS


def file_blob(root: Path, evidence: Sequence[CloseoutEvidence], kinds: Sequence[str]) -> str:
    selected = evidence_by_kind(evidence, *kinds)
    chunks: List[str] = []
    for item in selected[:40]:
        p = root / item.path
        if p.suffix.lower() == ".json":
            obj = safe_json(p)
            if obj is not None:
                chunks.append(flatten_strings(obj))
        else:
            chunks.append(safe_read(p, limit=120_000))
    return "\n".join(chunks).lower()


def detect_source_chain(root: Path, evidence: Sequence[CloseoutEvidence]) -> Tuple[str, List[str]]:
    blob = file_blob(root, evidence, ["media_inventory", "article", "release", "final_validation", "acceptance", "done_gate", "operator_final", "live_reconciliation", "closeout_report"])
    if not blob:
        return FAIL, ["No source-chain/provenance text was found."]
    required_terms = {
        "msn": "MSN captured surface",
        "publisher": "visible publisher/source field",
        "original": "original-source/original-source-gap field",
        "source_role": "source-role field",
        "primary_source": "primary-source-status field",
    }
    missing = [label for term, label in required_terms.items() if term not in blob]
    media_credit_ok = "credit" in blob or "google street view" in blob or "media source" in blob
    if missing:
        return PARTIAL, ["Missing source-chain markers: " + ", ".join(missing)]
    if not media_credit_ok:
        return PARTIAL, ["Source-chain markers exist, but media-credit evidence was not obvious."]
    return PASS, ["MSN/source-role/original-source/media-credit markers found."]


def detect_manual_live_result(root: Path, evidence: Sequence[CloseoutEvidence]) -> Tuple[str, List[str]]:
    entries = evidence_by_kind(evidence, "manual_live_result")
    if not entries:
        return PARTIAL, ["No filled manual/live acceptance result was found; live MSN cannot be closed as COMPLETE."]
    blob = file_blob(root, evidence, ["manual_live_result"])
    lowered = blob.lower()
    if any(word in lowered for word in ["blocked", "failed", "fail", "false"]):
        return FAIL, ["Manual/live result contains failure/blocking wording."]
    pass_markers = ["pass", "passed", "live_article_passed", "article_extraction_passed", "comments_export_passed", "source_chain_review_passed"]
    if any(marker in lowered for marker in pass_markers) or any(e.status_hint == PASS for e in entries):
        return PASS, ["Filled manual/live acceptance result appears to indicate pass."]
    return PARTIAL, ["Manual/live result exists but did not clearly indicate pass."]


def build_checks(root: Path, evidence: Sequence[CloseoutEvidence]) -> Tuple[List[CloseoutCheck], Dict[str, str], Dict[str, List[str]], Dict[str, List[str]]]:
    checks: List[CloseoutCheck] = []
    status_map: Dict[str, str] = {}
    evidence_map: Dict[str, List[str]] = {}
    notes_map: Dict[str, List[str]] = {}

    def add(key: str, label: str, status: str, entries: Sequence[CloseoutEvidence], notes: Optional[Sequence[str]] = None) -> None:
        ev_paths = paths(entries)
        note_list = list(notes or [])
        checks.append(CloseoutCheck(key, label, status, ev_paths, note_list))
        status_map[key] = status
        evidence_map[key] = ev_paths
        notes_map[key] = note_list

    article_entries = evidence_by_kind(evidence, "article")
    add("article", "Article extraction evidence", status_from_entries(article_entries), article_entries)

    comments_entries = evidence_by_kind(evidence, "comments")
    add("comments", "Comments export evidence", status_from_entries(comments_entries), comments_entries)

    profile_entries = evidence_by_kind(evidence, "profiles")
    add("profiles", "Profile export evidence", status_from_entries(profile_entries), profile_entries)

    viewer_entries = evidence_by_kind(evidence, "offline_viewer")
    html_entries = [e for e in evidence_by_kind(evidence, "article") if e.path.lower().endswith((".html", ".htm"))]
    offline_entries = viewer_entries + html_entries
    add("offline_viewer", "Offline viewer / rendered HTML evidence", status_from_entries(offline_entries), offline_entries)

    archive_entries = evidence_by_kind(evidence, "archive_warc", "archive_wacz")
    archive_status = status_from_entries(archive_entries) if archive_entries else PARTIAL
    archive_notes = [] if archive_entries else ["No WARC/WACZ evidence found. This may be acceptable only when the target was a comments-only validation."]
    add("archive", "WARC/WACZ/archive evidence", archive_status, archive_entries, archive_notes)

    media_entries = evidence_by_kind(evidence, "media_inventory", "downloaded_media")
    add("media", "Image/media inventory and download status evidence", status_from_entries(media_entries), media_entries)

    media_blob = file_blob(root, evidence, ["media_inventory", "downloaded_media"])
    video_terms = ["video", "stream", "hls", "dash", "m3u8", "mpd", "player"]
    if any(term in media_blob for term in video_terms):
        video_status = PASS
        video_notes = ["Video/stream candidate status markers found."]
    else:
        video_status = NOT_APPLICABLE
        video_notes = ["No video/stream markers found; treated as not applicable unless the live target visibly had video."]
    add("video", "Video/stream candidate status when present", video_status, media_entries, video_notes)

    source_status, source_notes = detect_source_chain(root, evidence)
    source_entries = evidence_by_kind(evidence, "media_inventory", "article", "release", "final_validation", "acceptance", "done_gate", "operator_final", "live_reconciliation")
    add("source_roles", "Source role / primary-source status evidence", source_status, source_entries, source_notes)
    add("source_chain", "MSN/publisher/media-credit/original-source separation", source_status, source_entries, source_notes)

    readiness_entries = evidence_by_kind(evidence, "readiness", "release", "final_validation")
    add("readiness_reports", "Readiness/release/final validation reports", status_from_presence(readiness_entries), readiness_entries)

    done_entries = evidence_by_kind(evidence, "done_gate", "acceptance", "operator_final", "live_reconciliation", "completion")
    add("done_acceptance_reports", "Done-gate/acceptance/operator/reconciliation reports", status_from_presence(done_entries), done_entries)

    manual_status, manual_notes = detect_manual_live_result(root, evidence)
    manual_entries = evidence_by_kind(evidence, "manual_live_result")
    add("manual_live_result", "Filled manual/live result", manual_status, manual_entries, manual_notes)

    return checks, status_map, evidence_map, notes_map


def next_actions_for(matrix: GoalMatrix) -> List[str]:
    if matrix.final_status == COMPLETE:
        return ["No MSN adapter blocker remains. Preserve the closeout report with the validated output bundle."]
    actions: List[str] = []
    if "manual_live_result" in matrix.missing_live:
        actions.append("Run the live acceptance/operator smoke pack on one real MSN article and place the filled result JSON in the output folder.")
    if "media" in matrix.missing_static:
        actions.append("Run or attach the media inventory/download status workflow for the MSN output folder.")
    if "source_roles" in matrix.missing_static or "source_chain" in matrix.missing_static:
        actions.append("Add source-role, primary-source-status, and MSN/publisher/media-credit/original-source-gap fields to the output bundle.")
    if "comments" in matrix.missing_static or "profiles" in matrix.missing_static:
        actions.append("Attach the accepted comments/profile export generated from the V34/V35 path or rerun the comments/profile exporter.")
    if "offline_viewer" in matrix.missing_static:
        actions.append("Attach the offline rendered HTML/local viewer output and archive status sidecars.")
    if "done_acceptance_reports" in matrix.missing_static or "readiness_reports" in matrix.missing_static:
        actions.append("Run the final validator, done gate, acceptance suite, operator final runner, and live reconciler before closeout.")
    if not actions:
        actions.append("Review the partial/unknown checks in the closeout report and provide the missing sidecar files.")
    return actions


def build_closeout_report(root: Path, out_dir: Optional[Path] = None, manual_result: Optional[Path] = None) -> CloseoutReport:
    evidence = collect_evidence(root, manual_result=manual_result)
    checks, status_map, evidence_map, notes_map = build_checks(root, evidence)
    matrix = build_goal_matrix(status_map, evidence_map, notes_map)
    actions = next_actions_for(matrix)
    return CloseoutReport(
        schema="msn.source_adapter.closeout.v1",
        generated_at_utc=utc_now(),
        root=str(root),
        final_status=matrix.final_status,
        static_status=matrix.static_status,
        live_status=matrix.live_status,
        goal_matrix=matrix.to_dict(),
        checks=checks,
        evidence_files=list(evidence),
        missing_static=list(matrix.missing_static),
        missing_live=list(matrix.missing_live),
        blocking_reasons=list(matrix.blocking_reasons),
        next_actions=actions,
    )


def render_markdown(report: CloseoutReport) -> str:
    lines = [
        "# MSN Source Adapter Closeout Report",
        "",
        f"Generated: `{report.generated_at_utc}`",
        f"Root: `{report.root}`",
        f"Final status: `{report.final_status}`",
        f"Static status: `{report.static_status}`",
        f"Live status: `{report.live_status}`",
        "",
        "## Checks",
        "",
        "| Key | Status | Evidence | Notes |",
        "|---|---|---|---|",
    ]
    for check in report.checks:
        ev = "; ".join(check.evidence[:4]) if check.evidence else "-"
        notes = " ".join(check.notes) if check.notes else "-"
        lines.append(f"| `{check.key}` | `{check.status}` | {ev} | {notes} |")
    if report.missing_static:
        lines.extend(["", "## Missing static evidence", ""])
        lines.extend(f"- `{x}`" for x in report.missing_static)
    if report.missing_live:
        lines.extend(["", "## Missing live evidence", ""])
        lines.extend(f"- `{x}`" for x in report.missing_live)
    if report.blocking_reasons:
        lines.extend(["", "## Blocking reasons", ""])
        lines.extend(f"- {x}" for x in report.blocking_reasons)
    lines.extend(["", "## Next actions", ""])
    lines.extend(f"- {x}" for x in report.next_actions)
    lines.extend(["", "## Goal matrix", ""])
    gm = report.goal_matrix
    lines.append(f"Final goal status: `{gm.get('final_status', report.final_status)}`")
    lines.append(f"Static goal status: `{gm.get('static_status', report.static_status)}`")
    lines.append(f"Live goal status: `{gm.get('live_status', report.live_status)}`")
    lines.extend(["", "| Criterion | Static required | Live required | Status | Evidence |", "|---|---:|---:|---|---|"])
    for item in gm.get("criteria", []):
        if isinstance(item, Mapping):
            label = str(item.get("label", item.get("key", "criterion")))
            static_req = item.get("required_for_static_confidence", "")
            live_req = item.get("required_for_live_complete", "")
            status = item.get("status", UNKNOWN)
            evidence = item.get("evidence") or []
            ev = "; ".join(str(x) for x in evidence[:3]) if isinstance(evidence, list) else str(evidence)
            lines.append(f"| {label} | {static_req} | {live_req} | `{status}` | {ev or '-'} |")
    return "\n".join(lines)


def render_actions(report: CloseoutReport) -> str:
    lines = [
        "# MSN Source Adapter Closeout Actions",
        "",
        f"Final status: `{report.final_status}`",
        "",
    ]
    if report.final_status == COMPLETE:
        lines.append("The MSN adapter has enough static and live/manual evidence to be treated as complete for the validated target output folder.")
        lines.append("")
        lines.append("Preserve the output folder and closeout report with the captured evidence package.")
    else:
        lines.append("The MSN adapter is not yet closed as live-complete for this output folder.")
        lines.append("")
        for action in report.next_actions:
            lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def write_closeout_report(report: CloseoutReport, out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / REPORT_JSON
    md_path = out_dir / REPORT_MD
    csv_path = out_dir / CHECKS_CSV
    actions_path = out_dir / ACTIONS_MD
    json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    actions_path.write_text(render_actions(report), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["key", "label", "status", "evidence", "notes"])
        writer.writeheader()
        for check in report.checks:
            writer.writerow({
                "key": check.key,
                "label": check.label,
                "status": check.status,
                "evidence": "; ".join(check.evidence),
                "notes": " ".join(check.notes),
            })
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "csv": str(csv_path),
        "actions": str(actions_path),
    }


def run_closeout(root: Path, out_dir: Optional[Path] = None, manual_result: Optional[Path] = None) -> Tuple[CloseoutReport, Dict[str, str]]:
    root = root.resolve()
    if out_dir is None:
        out_dir = root / "reports"
    report = build_closeout_report(root, out_dir=out_dir, manual_result=manual_result)
    written = write_closeout_report(report, out_dir)
    return report, written


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build final MSN source adapter closeout reports from an existing output folder.")
    parser.add_argument("--root", required=True, help="Existing MSN output folder to scan.")
    parser.add_argument("--out", help="Directory for closeout reports. Defaults to ROOT\\reports.")
    parser.add_argument("--manual-result", help="Optional filled manual/live acceptance result JSON/MD outside or inside ROOT.")
    args = parser.parse_args(argv)
    root = Path(args.root)
    out = Path(args.out) if args.out else None
    manual = Path(args.manual_result) if args.manual_result else None
    report, written = run_closeout(root, out, manual)
    print("MSN closeout status:", report.final_status)
    print("Static status:", report.static_status)
    print("Live status:", report.live_status)
    print("JSON:", written["json"])
    print("Markdown:", written["markdown"])
    print("CSV:", written["csv"])
    print("Actions:", written["actions"])
    return 0 if report.final_status in {COMPLETE, CONFIDENT_WITH_MANUAL_REVIEW, PARTIAL} else 2


if __name__ == "__main__":
    raise SystemExit(_main())
