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

REPORT_JSON = "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json"
REPORT_MD = "MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.md"

PASS = "PASS"
PARTIAL = "PARTIAL"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"
UNKNOWN = "UNKNOWN"

FINAL_COMPLETE = "COMPLETE"
FINAL_CONFIDENT_REVIEW = "CONFIDENT_WITH_MANUAL_REVIEW"
FINAL_PARTIAL = "PARTIAL"
FINAL_BLOCKED = "BLOCKED"
FINAL_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

STATUS_RE = re.compile(r"\b(PASS|PARTIAL|FAIL|NOT_APPLICABLE|UNKNOWN|COMPLETE|CONFIDENT_WITH_MANUAL_REVIEW|BLOCKED|INSUFFICIENT_EVIDENCE)\b", re.I)


@dataclass
class EvidenceFile:
    kind: str
    path: str
    size: int
    status_hint: str = UNKNOWN
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconcileCheck:
    name: str
    status: str
    evidence: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ReconciliationReport:
    schema: str
    generated_at_utc: str
    root: str
    final_status: str
    checks: List[ReconcileCheck]
    evidence_files: List[EvidenceFile]
    blocking_reasons: List[str]
    manual_review_reasons: List[str]
    next_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "generated_at_utc": self.generated_at_utc,
            "root": self.root,
            "final_status": self.final_status,
            "checks": [dataclasses.asdict(c) for c in self.checks],
            "evidence_files": [dataclasses.asdict(e) for e in self.evidence_files],
            "blocking_reasons": self.blocking_reasons,
            "manual_review_reasons": self.manual_review_reasons,
            "next_actions": self.next_actions,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_read(path: Path, limit: int = 500_000) -> str:
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


def _safe_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(_safe_read(path, limit=2_000_000))
    except Exception:
        return None


def _all_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file()]


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _status_hint_from_text(text: str) -> str:
    values = [m.group(1).upper() for m in STATUS_RE.finditer(text or "")]
    if not values:
        return UNKNOWN
    if FAIL in values or FINAL_BLOCKED in values:
        return FAIL
    if PARTIAL in values:
        return PARTIAL
    if FINAL_COMPLETE in values or PASS in values:
        return PASS
    if FINAL_CONFIDENT_REVIEW in values:
        return PARTIAL
    return values[0]


def _status_hint_from_json(value: Any) -> str:
    statuses: List[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, Mapping):
            for k, v in x.items():
                key = str(k).lower()
                if key in {"status", "final_status", "overall_status", "decision", "result"}:
                    if isinstance(v, str):
                        statuses.append(v.upper())
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)
        elif isinstance(x, str):
            match = STATUS_RE.search(x)
            if match:
                statuses.append(match.group(1).upper())

    walk(value)
    normalized = [s for s in statuses if s]
    if not normalized:
        return UNKNOWN
    if any(s in {FAIL, FINAL_BLOCKED} for s in normalized):
        return FAIL
    if any(s == PARTIAL for s in normalized):
        return PARTIAL
    if any(s in {PASS, FINAL_COMPLETE, FINAL_CONFIDENT_REVIEW} for s in normalized):
        return PASS
    return normalized[0]


def _classify_file(root: Path, path: Path) -> Optional[EvidenceFile]:
    name = path.name.lower()
    rel = _rel(root, path)
    size = path.stat().st_size
    kind = "other"
    important = False

    markers = {
        "operator_final_summary": ["operator_final_summary"],
        "acceptance_report": ["acceptance_report", "acceptance_checks"],
        "final_validation_report": ["final_validation_report"],
        "done_gate_report": ["done_gate", "done-gate"],
        "completion_report": ["completion", "completion_summary"],
        "release_report": ["release_report"],
        "readiness_report": ["readiness"],
        "manual_live_result": ["live_acceptance_result", "manual_validation", "operator_result"],
        "media_inventory": ["media_inventory", "media-manifest", "media_manifest", "media_download"],
        "comments_export": ["comments", "comment"],
        "profiles_export": ["profiles", "profile"],
        "article_export": ["article", "rendered-page", "rendered_page"],
        "offline_viewer": ["open_local_viewer", "local_viewer"],
        "archive_warc": [".warc", "warc.gz"],
        "archive_wacz": [".wacz", "wacz"],
    }
    for candidate, tokens in markers.items():
        if any(t in name or t in rel.lower() for t in tokens):
            kind = candidate
            important = True
            break

    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm", ".m3u8", ".mpd"}:
        kind = "downloaded_media"
        important = True

    if not important:
        return None

    details: Dict[str, Any] = {}
    hint = UNKNOWN
    if path.suffix.lower() == ".json":
        obj = _safe_json(path)
        if obj is not None:
            hint = _status_hint_from_json(obj)
            details["json_type"] = type(obj).__name__
            if isinstance(obj, Mapping):
                details["json_keys"] = sorted(str(k) for k in obj.keys())[:30]
        else:
            hint = UNKNOWN
    elif path.suffix.lower() in {".md", ".txt", ".csv", ".html", ".cmd"}:
        hint = _status_hint_from_text(_safe_read(path, limit=120_000))
    elif kind == "downloaded_media":
        hint = PASS if size > 0 else FAIL

    return EvidenceFile(kind=kind, path=rel, size=size, status_hint=hint, details=details)


def collect_evidence(root: Path) -> List[EvidenceFile]:
    evidence = []
    for path in _all_files(root):
        entry = _classify_file(root, path)
        if entry:
            evidence.append(entry)
    evidence.sort(key=lambda e: (e.kind, e.path))
    return evidence


def _has_kind(evidence: Sequence[EvidenceFile], *kinds: str) -> List[EvidenceFile]:
    want = set(kinds)
    return [e for e in evidence if e.kind in want]


def _evidence_paths(entries: Sequence[EvidenceFile], limit: int = 8) -> List[str]:
    return [e.path for e in entries[:limit]]


def _status_from_entries(entries: Sequence[EvidenceFile], require_pass_hint: bool = False) -> str:
    if not entries:
        return FAIL
    if any(e.status_hint == FAIL for e in entries):
        return FAIL
    if require_pass_hint and not any(e.status_hint == PASS for e in entries):
        return PARTIAL
    if any(e.status_hint == PARTIAL for e in entries):
        return PARTIAL
    return PASS


def _json_values(root: Path, entries: Sequence[EvidenceFile]) -> List[Any]:
    values = []
    for e in entries:
        p = root / e.path
        if p.suffix.lower() == ".json":
            obj = _safe_json(p)
            if obj is not None:
                values.append(obj)
    return values


def _flatten_strings(obj: Any, limit: int = 50_000) -> str:
    out: List[str] = []

    def walk(x: Any) -> None:
        if sum(len(s) for s in out) > limit:
            return
        if isinstance(x, Mapping):
            for k, v in x.items():
                out.append(str(k))
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, (str, int, float, bool)) or x is None:
            out.append(str(x))

    walk(obj)
    return "\n".join(out).lower()


def _live_result_status(root: Path, live_entries: Sequence[EvidenceFile]) -> Tuple[str, List[str]]:
    if not live_entries:
        return FAIL, ["No filled manual/live acceptance result was found."]

    notes: List[str] = []
    values = _json_values(root, live_entries)
    blob = "\n".join(_flatten_strings(v) for v in values)
    text_blob = blob + "\n" + "\n".join(_safe_read(root / e.path, limit=80_000).lower() for e in live_entries if not e.path.lower().endswith(".json"))

    explicit_fail = any(word in text_blob for word in ["fail", "blocked", "not passed", "did not pass"])
    explicit_partial = any(word in text_blob for word in ["partial", "needs review", "manual review", "not sure"])
    explicit_pass = any(word in text_blob for word in ["pass", "passed", "complete", "accepted"])

    required_terms = [
        "article",
        "comments",
        "profile",
        "offline",
        "warc",
        "media",
        "source",
    ]
    missing_terms = [term for term in required_terms if term not in text_blob]
    if missing_terms:
        notes.append("Live result does not mention required areas: " + ", ".join(missing_terms))

    if explicit_fail:
        return FAIL, notes or ["Live result includes a fail/blocked indicator."]
    if explicit_partial or missing_terms:
        return PARTIAL, notes or ["Live result indicates manual review or partial status."]
    if explicit_pass:
        return PASS, ["Live result contains pass/complete indicators for the expected areas."]
    return PARTIAL, notes or ["Live result was found but no explicit pass/fail signal was detected."]


def build_reconciliation_report(root: Path) -> ReconciliationReport:
    root = root.resolve()
    evidence = collect_evidence(root)
    checks: List[ReconcileCheck] = []

    def add(name: str, status: str, entries: Sequence[EvidenceFile] = (), notes: Sequence[str] = ()) -> None:
        checks.append(ReconcileCheck(name=name, status=status, evidence=_evidence_paths(entries), notes=list(notes)))

    operator_entries = _has_kind(evidence, "operator_final_summary")
    acceptance_entries = _has_kind(evidence, "acceptance_report")
    final_validation_entries = _has_kind(evidence, "final_validation_report")
    done_gate_entries = _has_kind(evidence, "done_gate_report")
    completion_entries = _has_kind(evidence, "completion_report")
    media_entries = _has_kind(evidence, "media_inventory", "downloaded_media")
    article_entries = _has_kind(evidence, "article_export")
    comments_entries = _has_kind(evidence, "comments_export")
    profile_entries = _has_kind(evidence, "profiles_export")
    viewer_entries = _has_kind(evidence, "offline_viewer", "archive_warc", "archive_wacz")
    live_entries = _has_kind(evidence, "manual_live_result")

    add("operator_final_summary_present", _status_from_entries(operator_entries), operator_entries)
    add("acceptance_suite_present", _status_from_entries(acceptance_entries), acceptance_entries)
    add("final_validator_present", _status_from_entries(final_validation_entries), final_validation_entries)
    add("done_gate_present", _status_from_entries(done_gate_entries), done_gate_entries)
    add("completion_cli_output_present", PASS if completion_entries else PARTIAL, completion_entries, [] if completion_entries else ["Completion CLI output not found; this can be acceptable if operator-final summary is present."])
    add("article_output_present", _status_from_entries(article_entries), article_entries)
    add("comments_output_present", _status_from_entries(comments_entries), comments_entries)
    add("profile_output_present", _status_from_entries(profile_entries), profile_entries)
    add("offline_viewer_or_archive_present", _status_from_entries(viewer_entries), viewer_entries)
    add("media_inventory_or_downloads_present", _status_from_entries(media_entries), media_entries)

    live_status, live_notes = _live_result_status(root, live_entries)
    add("manual_live_acceptance_result_present", live_status, live_entries, live_notes)

    combined_json_values = _json_values(root, evidence)
    combined_blob = "\n".join(_flatten_strings(v) for v in combined_json_values)
    combined_blob += "\n" + "\n".join(_safe_read(root / e.path, limit=100_000).lower() for e in evidence if e.path.lower().endswith((".md", ".txt", ".csv")))

    role_terms = ["source_role", "primary_source_status", "source_chain_gap"]
    missing_role_terms = [term for term in role_terms if term not in combined_blob]
    role_status = PASS if not missing_role_terms else PARTIAL if any(term in combined_blob for term in role_terms) else FAIL
    add("source_role_and_chain_fields_present", role_status, evidence[:8], [] if not missing_role_terms else ["Missing terms in collected outputs: " + ", ".join(missing_role_terms)])

    republisher_terms = ["msn", "republisher", "visible publisher", "original source"]
    republisher_hits = sum(1 for term in republisher_terms if term in combined_blob)
    if republisher_hits >= 3:
        repub_status = PASS
    elif republisher_hits:
        repub_status = PARTIAL
    else:
        repub_status = FAIL
    add("msn_republisher_source_distinction_present", repub_status, evidence[:8], [] if repub_status == PASS else ["Need explicit MSN republisher / visible publisher / original source distinction in outputs."])

    media_blob_terms = ["media", "download", "hash", "video", "stream", "candidate"]
    media_term_hits = sum(1 for term in media_blob_terms if term in combined_blob)
    media_status = PASS if media_term_hits >= 4 and media_entries else PARTIAL if media_term_hits or media_entries else FAIL
    add("media_download_and_video_status_present", media_status, media_entries, [] if media_status == PASS else ["Media sidecars or video/stream status are incomplete or absent."])

    statuses = [c.status for c in checks]
    blocking_reasons: List[str] = []
    manual_review_reasons: List[str] = []

    for c in checks:
        if c.status == FAIL and c.name in {
            "operator_final_summary_present",
            "acceptance_suite_present",
            "final_validator_present",
            "article_output_present",
            "comments_output_present",
            "profile_output_present",
            "offline_viewer_or_archive_present",
            "media_inventory_or_downloads_present",
            "source_role_and_chain_fields_present",
            "msn_republisher_source_distinction_present",
        }:
            blocking_reasons.append(f"{c.name}: {', '.join(c.notes) if c.notes else 'missing or failed'}")
        if c.status in {PARTIAL, UNKNOWN}:
            manual_review_reasons.append(f"{c.name}: {', '.join(c.notes) if c.notes else 'partial/uncertain'}")

    if live_status == FAIL:
        manual_review_reasons.append("manual_live_acceptance_result_present: live result missing, so completion remains manual-review gated.")
    elif live_status == PARTIAL:
        manual_review_reasons.append("manual_live_acceptance_result_present: live result exists but is partial/uncertain.")

    any_static_fail = any(c.status == FAIL for c in checks if c.name != "manual_live_acceptance_result_present")
    any_partial = any(c.status == PARTIAL for c in checks)

    if any_static_fail:
        final_status = FINAL_BLOCKED
    elif live_status == PASS and not any_partial:
        final_status = FINAL_COMPLETE
    elif live_status == PASS:
        final_status = FINAL_PARTIAL
    elif not evidence:
        final_status = FINAL_INSUFFICIENT
    else:
        final_status = FINAL_CONFIDENT_REVIEW

    next_actions: List[str] = []
    if final_status == FINAL_COMPLETE:
        next_actions.append("Record the MSN adapter as complete for the validated target bundle and preserve the reconciliation report with the evidence package.")
    elif final_status == FINAL_CONFIDENT_REVIEW:
        next_actions.append("Run the operator final runner against a real MSN output folder, fill the live acceptance result, then rerun this reconciler.")
    elif final_status == FINAL_PARTIAL:
        next_actions.append("Resolve partial checks listed in manual_review_reasons, then rerun the operator final runner and reconciler.")
    elif final_status == FINAL_BLOCKED:
        next_actions.append("Fix blocking missing/failed outputs before marking MSN complete.")
    else:
        next_actions.append("Provide an MSN output folder containing article, comments, archive, media, source-chain, and validation reports.")

    return ReconciliationReport(
        schema="msn_source_adapter_live_result_reconciliation.v1",
        generated_at_utc=_utc_now(),
        root=str(root),
        final_status=final_status,
        checks=checks,
        evidence_files=evidence,
        blocking_reasons=blocking_reasons,
        manual_review_reasons=manual_review_reasons,
        next_actions=next_actions,
    )


def write_report(report: ReconciliationReport, out_dir: Path) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / REPORT_JSON
    md_path = out_dir / REPORT_MD
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def render_markdown(report: ReconciliationReport) -> str:
    lines: List[str] = []
    lines.append("# MSN Source Adapter Live Reconciliation Report")
    lines.append("")
    lines.append(f"- Generated: `{report.generated_at_utc}`")
    lines.append(f"- Root: `{report.root}`")
    lines.append(f"- Final status: **{report.final_status}**")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Status | Evidence | Notes |")
    lines.append("|---|---:|---|---|")
    for c in report.checks:
        evidence = "<br>".join(f"`{p}`" for p in c.evidence) if c.evidence else ""
        notes = "<br>".join(c.notes) if c.notes else ""
        lines.append(f"| {c.name} | {c.status} | {evidence} | {notes} |")
    lines.append("")
    lines.append("## Blocking reasons")
    lines.append("")
    if report.blocking_reasons:
        for reason in report.blocking_reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- None recorded.")
    lines.append("")
    lines.append("## Manual review reasons")
    lines.append("")
    if report.manual_review_reasons:
        for reason in report.manual_review_reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- None recorded.")
    lines.append("")
    lines.append("## Next actions")
    lines.append("")
    for action in report.next_actions:
        lines.append(f"- {action}")
    lines.append("")
    lines.append("## Evidence files")
    lines.append("")
    lines.append("| Kind | Status hint | Size | Path |")
    lines.append("|---|---:|---:|---|")
    for e in report.evidence_files[:200]:
        lines.append(f"| {e.kind} | {e.status_hint} | {e.size} | `{e.path}` |")
    if len(report.evidence_files) > 200:
        lines.append(f"| ... | ... | ... | {len(report.evidence_files) - 200} more files omitted |")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile MSN adapter static reports with manual/live validation evidence.")
    parser.add_argument("--root", required=True, help="Existing MSN output folder to scan.")
    parser.add_argument("--out", default=None, help="Directory for reconciliation outputs. Defaults to <root>/reports.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"MSN live reconciler root not found: {root}", file=sys.stderr)
        return 2
    out_dir = Path(args.out) if args.out else root / "reports"
    report = build_reconciliation_report(root)
    json_path, md_path = write_report(report, out_dir)
    print(f"MSN live reconciliation status: {report.final_status}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    if report.final_status == FINAL_BLOCKED:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
