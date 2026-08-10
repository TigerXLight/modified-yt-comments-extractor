"""MSN source adapter capstone acceptance/reporting utilities.

This module is intentionally no-network and file-system based.  It evaluates an
already-produced MSN output folder and tells the operator whether the adapter is
structurally complete enough to be treated as a confident MSN capture bundle.
It does not fetch MSN, replay WARC/WACZ, or infer that a publisher is the
original source of media without captured provenance.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class CheckStatus(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AcceptanceStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    CONFIDENT_WITH_MANUAL_REVIEW = "CONFIDENT_WITH_MANUAL_REVIEW"
    PARTIAL_NEEDS_REVIEW = "PARTIAL_NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AcceptanceCheck:
    check_id: str
    title: str
    status: CheckStatus
    summary: str
    evidence: tuple[str, ...] = ()
    required: bool = True
    operator_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AcceptanceReport:
    adapter_name: str
    source_platform: str
    assessed_root: str
    generated_at_utc: str
    acceptance_status: AcceptanceStatus
    checks: tuple[AcceptanceCheck, ...]
    pass_count: int
    partial_count: int
    fail_count: int
    not_applicable_count: int
    required_failures: tuple[str, ...]
    required_partials: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["acceptance_status"] = self.acceptance_status.value
        data["checks"] = [c.to_dict() for c in self.checks]
        return data


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            cleaned = data.strip()
            if cleaned:
                self.parts.append(cleaned)

    @property
    def text(self) -> str:
        return "\n".join(self.parts)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_read_text(path: Path, limit: int = 2_000_000) -> str:
    try:
        with path.open("rb") as f:
            raw = f.read(limit)
    except OSError:
        return ""
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(_safe_read_text(path))
    except Exception:
        return None


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (p for p in root.rglob("*") if p.is_file())


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _find_by_names(root: Path, names: Sequence[str]) -> list[Path]:
    wanted = {n.lower() for n in names}
    return [p for p in _iter_files(root) if p.name.lower() in wanted]


def _find_name_contains(root: Path, fragments: Sequence[str], suffixes: Sequence[str] | None = None) -> list[Path]:
    suffixes_lower = tuple(s.lower() for s in suffixes or ())
    out: list[Path] = []
    for path in _iter_files(root):
        name = path.name.lower()
        if suffixes_lower and not name.endswith(suffixes_lower):
            continue
        if all(fragment.lower() in name for fragment in fragments):
            out.append(path)
    return out


def _json_values(obj: Any) -> Iterable[Any]:
    if isinstance(obj, dict):
        for value in obj.values():
            yield value
            yield from _json_values(value)
    elif isinstance(obj, list):
        for value in obj:
            yield value
            yield from _json_values(value)


def _json_text_blob(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(obj)


def _visible_html_text(path: Path) -> str:
    parser = _VisibleTextParser()
    try:
        parser.feed(_safe_read_text(path))
    except Exception:
        return ""
    return parser.text


def _looks_like_msn_republisher_metadata(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("the independent", "original source", "visible source", "google street view", "source credit", "publisher"))


def _article_check(root: Path) -> AcceptanceCheck:
    html_files = _find_by_names(root, ["rendered-page.html"])
    article_json = _find_name_contains(root, ["article"], [".json"])
    evidence: list[str] = []
    if html_files:
        best = html_files[0]
        raw = _safe_read_text(best, limit=500_000)
        text = _visible_html_text(best)
        raw_lower = raw.lower()
        text_lower = text.lower()
        evidence.append(f"{_relative(best, root)} visible_text_chars={len(text)} raw_chars={len(raw)}")
        has_visible_body = len(text) >= 400
        has_substantial_rendered_html = len(raw) >= 4_000 and any(
            token in raw_lower for token in ("<html", "<body", "article", "msn", "news")
        )
        has_urlish = "http" in raw_lower or "msn.com" in raw_lower
        has_articleish = any(
            token in text_lower or token in raw_lower
            for token in ("article", "headline", "published", "author", "news", "the independent", "publisher")
        )
        if (has_visible_body or has_substantial_rendered_html) and (has_urlish or has_articleish):
            return AcceptanceCheck(
                "article_extraction",
                "Article extraction / rendered article",
                CheckStatus.PASS,
                "Rendered article HTML exists and contains substantial captured article content/source traces.",
                tuple(evidence),
            )
        return AcceptanceCheck(
            "article_extraction",
            "Article extraction / rendered article",
            CheckStatus.PARTIAL,
            "rendered-page.html exists, but article body/source traces were only partially confirmed by the checker.",
            tuple(evidence),
        )
    if article_json:
        evidence.extend(_relative(p, root) for p in article_json[:5])
        return AcceptanceCheck(
            "article_extraction",
            "Article extraction / rendered article",
            CheckStatus.PARTIAL,
            "Article JSON-like sidecars exist, but rendered-page.html was not found or was not assessable.",
            tuple(evidence),
        )
    return AcceptanceCheck(
        "article_extraction",
        "Article extraction / rendered article",
        CheckStatus.FAIL,
        "No rendered-page.html or article JSON sidecar was found.",
    )
def _comments_profile_check(root: Path) -> AcceptanceCheck:
    comments = _find_name_contains(root, ["comments"], [".json", ".txt", ".md", ".html"])
    profile_files = _find_name_contains(root, ["profile"], [".json", ".csv", ".txt", ".html"])
    accepted = _find_name_contains(root, ["msn", "comments", "profile"], [".json", ".txt", ".html", ".md"])
    evidence = [_relative(p, root) for p in (comments[:4] + profile_files[:4] + accepted[:4])]
    if comments and profile_files:
        return AcceptanceCheck(
            "comments_profiles",
            "Comments and profile exports",
            CheckStatus.PASS,
            "Comment exports and profile exports are both present.",
            tuple(dict.fromkeys(evidence)),
        )
    if comments or profile_files or accepted:
        return AcceptanceCheck(
            "comments_profiles",
            "Comments and profile exports",
            CheckStatus.PARTIAL,
            "Some MSN comments/profile artifacts exist, but both sides were not confirmed together.",
            tuple(dict.fromkeys(evidence)),
        )
    return AcceptanceCheck(
        "comments_profiles",
        "Comments and profile exports",
        CheckStatus.FAIL,
        "No MSN comments/profile export artifacts were found.",
    )


def _offline_viewer_check(root: Path) -> AcceptanceCheck:
    viewer = _find_by_names(root, ["open_local_viewer.cmd", "local-viewer.html", "index.html"])
    rendered = _find_by_names(root, ["rendered-page.html"])
    manifest = _find_by_names(root, ["capture-manifest.json", "manifest.json", "validation.json"])
    evidence = [_relative(p, root) for p in (viewer[:3] + rendered[:3] + manifest[:3])]
    if viewer and rendered:
        return AcceptanceCheck(
            "offline_viewer",
            "Offline webpage viewer",
            CheckStatus.PASS,
            "Local viewer entry point and rendered article page are both present.",
            tuple(evidence),
        )
    if rendered or viewer:
        return AcceptanceCheck(
            "offline_viewer",
            "Offline webpage viewer",
            CheckStatus.PARTIAL,
            "A rendered page or viewer exists, but the pair was not confirmed together.",
            tuple(evidence),
        )
    return AcceptanceCheck("offline_viewer", "Offline webpage viewer", CheckStatus.FAIL, "No offline viewer/rendered page artifacts were found.")


def _archive_replay_check(root: Path) -> AcceptanceCheck:
    warcs = [p for p in _iter_files(root) if p.name.lower().endswith((".warc", ".warc.gz"))]
    waczs = [p for p in _iter_files(root) if p.name.lower().endswith(".wacz")]
    evidence = [_relative(p, root) for p in (warcs[:4] + waczs[:4])]
    strict_notes = " ".join(_safe_read_text(p, limit=200_000).lower() for p in _find_by_names(root, ["validation.json", "capture-manifest.json"]))
    has_experimental_label = any(token in strict_notes for token in ("experimental", "possibly unsupported", "strict wacz", "unknown package profile"))
    if warcs and waczs and has_experimental_label:
        return AcceptanceCheck(
            "archive_replay",
            "WARC/WACZ replay artifacts",
            CheckStatus.PARTIAL,
            "WARC and WACZ artifacts exist and WACZ uncertainty is labelled honestly; manual ReplayWeb validation is still required.",
            tuple(evidence),
            operator_note="Treat WARC.GZ as useful/partial and strict WACZ as experimental unless a compatible WACZ smoke passes.",
        )
    if warcs:
        return AcceptanceCheck(
            "archive_replay",
            "WARC/WACZ replay artifacts",
            CheckStatus.PARTIAL,
            "A WARC/WARC.GZ artifact exists; WACZ replay success was not confirmed.",
            tuple(evidence),
        )
    if waczs:
        return AcceptanceCheck(
            "archive_replay",
            "WARC/WACZ replay artifacts",
            CheckStatus.PARTIAL,
            "A WACZ artifact exists, but no WARC/WARC.GZ fallback was found.",
            tuple(evidence),
        )
    return AcceptanceCheck("archive_replay", "WARC/WACZ replay artifacts", CheckStatus.FAIL, "No WARC/WACZ archive artifact was found.")


def _media_check(root: Path) -> AcceptanceCheck:
    media_reports = _find_name_contains(root, ["media"], [".json", ".csv", ".md"])
    media_files = [
        p
        for p in _iter_files(root)
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".m3u8", ".mpd"}
    ]
    evidence = [_relative(p, root) for p in (media_reports[:5] + media_files[:5])]
    blob = "\n".join(_safe_read_text(p, limit=200_000) for p in media_reports[:10]).lower()
    has_candidate = any(token in blob for token in ("candidate", "media_url", "image", "video", "poster", "stream"))
    has_hash = any(token in blob for token in ("sha256", "checksum", "hash"))
    has_blocked_status = any(token in blob for token in ("blocked", "external", "stream", "unavailable", "dry_run", "not_downloaded"))
    if media_files and has_hash:
        return AcceptanceCheck(
            "media_registration",
            "Image/video/media download registration",
            CheckStatus.PASS,
            "Media files and hash/checksum metadata are present.",
            tuple(evidence),
        )
    if media_reports and (has_candidate or has_blocked_status):
        return AcceptanceCheck(
            "media_registration",
            "Image/video/media download registration",
            CheckStatus.PARTIAL,
            "Media candidates/status sidecars are present, but downloaded hashed media was not confirmed.",
            tuple(evidence),
            operator_note="This is acceptable when MSN exposes streamed/external video only, but a manual review should confirm the status label.",
        )
    if media_files:
        return AcceptanceCheck(
            "media_registration",
            "Image/video/media download registration",
            CheckStatus.PARTIAL,
            "Media files exist, but no manifest/hash status sidecar was confirmed.",
            tuple(evidence),
        )
    return AcceptanceCheck(
        "media_registration",
        "Image/video/media download registration",
        CheckStatus.FAIL,
        "No media files or media registration sidecars were found.",
    )


def _video_check(root: Path) -> AcceptanceCheck:
    media_reports = _find_name_contains(root, ["media"], [".json", ".csv", ".md"])
    blob = "\n".join(_safe_read_text(p, limit=200_000) for p in media_reports[:10]).lower()
    evidence = [_relative(p, root) for p in media_reports[:5]]
    has_video = any(token in blob for token in ("video", "player", "poster", ".m3u8", ".mpd", "stream"))
    if has_video and any(token in blob for token in ("external", "stream", "blocked", "downloaded", "poster")):
        return AcceptanceCheck(
            "video_status",
            "Video/poster/stream status",
            CheckStatus.PASS,
            "Video/poster/stream candidates have explicit status metadata.",
            tuple(evidence),
            required=False,
        )
    if has_video:
        return AcceptanceCheck(
            "video_status",
            "Video/poster/stream status",
            CheckStatus.PARTIAL,
            "Video-like candidates exist, but their capture/download status is incomplete.",
            tuple(evidence),
            required=False,
        )
    return AcceptanceCheck(
        "video_status",
        "Video/poster/stream status",
        CheckStatus.NOT_APPLICABLE,
        "No video-like candidate was detected in the existing output folder.",
        tuple(evidence),
        required=False,
    )


def _source_provenance_check(root: Path) -> AcceptanceCheck:
    candidate_files = [
        p for p in _iter_files(root)
        if p.suffix.lower() in {".json", ".md", ".txt"}
        and any(token in p.name.lower() for token in ("manifest", "provenance", "source", "readiness", "release", "validation", "done", "media"))
    ]
    evidence = [_relative(p, root) for p in candidate_files[:8]]
    blob = "\n".join(_safe_read_text(p, limit=250_000) for p in candidate_files[:20]).lower()
    role_terms = ["source_role", "primary_source_status", "source_chain_gap"]
    has_roles = all(term in blob for term in role_terms)
    has_msn_distinction = any(term in blob for term in ("republisher", "secondary", "secondary_framing_only", "visible source", "claimed original", "original_source"))
    if has_roles and has_msn_distinction:
        return AcceptanceCheck(
            "source_provenance",
            "Source-role and media source-chain provenance",
            CheckStatus.PASS,
            "Source-role/status fields exist and MSN republisher/source-credit distinction is represented.",
            tuple(evidence),
        )
    if has_roles:
        return AcceptanceCheck(
            "source_provenance",
            "Source-role and media source-chain provenance",
            CheckStatus.PARTIAL,
            "Core source-role/status fields exist, but republisher/original-source distinction was not clearly detected.",
            tuple(evidence),
        )
    return AcceptanceCheck(
        "source_provenance",
        "Source-role and media source-chain provenance",
        CheckStatus.FAIL,
        "Source-role/status/source-chain fields were not found in manifest/report sidecars.",
        tuple(evidence),
    )


def _report_chain_check(root: Path) -> AcceptanceCheck:
    names = [
        "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json",
        "MSN_ADAPTER_FINAL_VALIDATION_REPORT.md",
        "MSN_SOURCE_ADAPTER_READINESS_REPORT.json",
        "MSN_SOURCE_ADAPTER_RELEASE_REPORT.json",
        "MSN_SOURCE_ADAPTER_DONE_GATE_REPORT.json",
        "MSN_SOURCE_ADAPTER_TOTAL_PACKAGE_INDEX.md",
    ]
    found = _find_by_names(root, names)
    evidence = [_relative(p, root) for p in found[:8]]
    if len(found) >= 3:
        return AcceptanceCheck(
            "report_chain",
            "Readiness/release/final/done reports",
            CheckStatus.PASS,
            "Multiple MSN adapter report artifacts are present for review.",
            tuple(evidence),
        )
    if found:
        return AcceptanceCheck(
            "report_chain",
            "Readiness/release/final/done reports",
            CheckStatus.PARTIAL,
            "Some MSN adapter report artifacts are present, but the full report chain was not confirmed.",
            tuple(evidence),
        )
    return AcceptanceCheck("report_chain", "Readiness/release/final/done reports", CheckStatus.FAIL, "No MSN readiness/release/final/done report artifacts were found.")


def build_acceptance_report(root: Path) -> AcceptanceReport:
    root = root.resolve()
    checks = (
        _article_check(root),
        _comments_profile_check(root),
        _offline_viewer_check(root),
        _archive_replay_check(root),
        _media_check(root),
        _video_check(root),
        _source_provenance_check(root),
        _report_chain_check(root),
    )
    pass_count = sum(c.status == CheckStatus.PASS for c in checks)
    partial_count = sum(c.status == CheckStatus.PARTIAL for c in checks)
    fail_count = sum(c.status == CheckStatus.FAIL for c in checks)
    not_applicable_count = sum(c.status == CheckStatus.NOT_APPLICABLE for c in checks)
    required_failures = tuple(c.check_id for c in checks if c.required and c.status == CheckStatus.FAIL)
    required_partials = tuple(c.check_id for c in checks if c.required and c.status == CheckStatus.PARTIAL)

    if required_failures:
        acceptance = AcceptanceStatus.BLOCKED
        summary = "Required MSN adapter areas are missing. Do not mark this MSN capture complete."
    elif required_partials:
        acceptance = AcceptanceStatus.CONFIDENT_WITH_MANUAL_REVIEW
        summary = "No required area failed, but one or more areas need manual review before final acceptance."
    else:
        acceptance = AcceptanceStatus.ACCEPTED
        summary = "Required MSN adapter areas passed from the available output-folder evidence."

    return AcceptanceReport(
        adapter_name="msn_source_adapter",
        source_platform="MSN",
        assessed_root=str(root),
        generated_at_utc=_utc_now(),
        acceptance_status=acceptance,
        checks=checks,
        pass_count=pass_count,
        partial_count=partial_count,
        fail_count=fail_count,
        not_applicable_count=not_applicable_count,
        required_failures=required_failures,
        required_partials=required_partials,
        summary=summary,
    )


def write_acceptance_report(report: AcceptanceReport, output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.md"
    csv_path = output_dir / "MSN_SOURCE_ADAPTER_ACCEPTANCE_CHECKS.csv"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_acceptance_markdown(report), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["check_id", "title", "status", "required", "summary", "evidence", "operator_note"])
        writer.writeheader()
        for check in report.checks:
            writer.writerow({
                "check_id": check.check_id,
                "title": check.title,
                "status": check.status.value,
                "required": str(check.required).lower(),
                "summary": check.summary,
                "evidence": " | ".join(check.evidence),
                "operator_note": check.operator_note,
            })
    return json_path, md_path, csv_path


def render_acceptance_markdown(report: AcceptanceReport) -> str:
    lines = [
        "# MSN Source Adapter Acceptance Report",
        "",
        f"Adapter: `{report.adapter_name}`",
        f"Platform: `{report.source_platform}`",
        f"Assessed root: `{report.assessed_root}`",
        f"Generated UTC: `{report.generated_at_utc}`",
        f"Acceptance status: **{report.acceptance_status.value}**",
        "",
        report.summary,
        "",
        "## Counts",
        "",
        f"- PASS: {report.pass_count}",
        f"- PARTIAL: {report.partial_count}",
        f"- FAIL: {report.fail_count}",
        f"- NOT_APPLICABLE: {report.not_applicable_count}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.extend([
            f"### {check.title}",
            "",
            f"- ID: `{check.check_id}`",
            f"- Status: **{check.status.value}**",
            f"- Required: `{str(check.required).lower()}`",
            f"- Summary: {check.summary}",
        ])
        if check.operator_note:
            lines.append(f"- Operator note: {check.operator_note}")
        if check.evidence:
            lines.append("- Evidence:")
            lines.extend(f"  - `{item}`" for item in check.evidence)
        lines.append("")
    lines.extend([
        "## Acceptance rule",
        "",
        "The adapter can be treated as complete for an MSN output folder only when required areas do not fail. PARTIAL areas must remain visible as manual-review limitations, especially WARC/WACZ replay and externally hosted/streamed video.",
        "",
    ])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create MSN source adapter acceptance reports for an existing output folder.")
    parser.add_argument("--root", required=True, help="Existing MSN output/capture folder to assess.")
    parser.add_argument("--output", default=None, help="Output directory for acceptance reports. Defaults to <root>/reports.")
    parser.add_argument("--json", action="store_true", help="Print report JSON to stdout.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    output = Path(args.output) if args.output else root / "reports"
    report = build_acceptance_report(root)
    json_path, md_path, csv_path = write_acceptance_report(report, output)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"MSN source adapter acceptance status: {report.acceptance_status.value}")
        print(f"JSON: {json_path}")
        print(f"Markdown: {md_path}")
        print(f"CSV: {csv_path}")
    return 0 if report.acceptance_status != AcceptanceStatus.BLOCKED else 2


if __name__ == "__main__":
    raise SystemExit(main())
