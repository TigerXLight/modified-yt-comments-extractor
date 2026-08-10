"""Final done-gate scanner for MSN source adapter output folders.

The validator is deliberately filesystem/report based. It does not run live capture and
it does not assume the publisher page is the primary/original source. It reads an
existing MSN output bundle and emits a human reviewable status report across the
adapter goals:

1. Article extraction.
2. Comments/profile extraction.
3. Offline webpage/archive viewer.
4. Media discovery/download registration.
5. Source-role and media source-chain provenance.
6. Manual validation evidence.

The output status is intentionally conservative. A folder can be structurally strong
while still requiring manual review for WACZ replay, JavaScript-heavy page fidelity,
or external/streamed video assets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

STATUS_PASS = "PASS"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAIL = "FAIL"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_UNKNOWN = "UNKNOWN"

OVERALL_READY = "READY_FOR_MSN_OPERATOR_USE"
OVERALL_CONFIDENT = "CONFIDENT_WITH_MANUAL_REVIEW"
OVERALL_PARTIAL = "PARTIAL_NEEDS_FOLLOW_UP"
OVERALL_NOT_READY = "NOT_READY"

SOURCE_STATUS_LABELS = {
    "PRIMARY_SOURCE_LOCATED",
    "PRIMARY_SOURCE_NOT_LOCATED",
    "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED",
    "PRIMARY_SOURCE_DISPUTED",
    "SECONDARY_FRAMING_ONLY",
    "TERTIARY_PROPAGATED_CLAIM",
    "MANUAL_SOURCE_NOTE",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi"}
STREAM_EXTENSIONS = {".m3u8", ".mpd"}
ARCHIVE_EXTENSIONS = {".warc", ".wacz", ".gz"}


@dataclass(frozen=True)
class EvidenceSignal:
    """A single filesystem/report signal used by the done gate."""

    name: str
    path: str | None = None
    detail: str = ""
    value: Any = None


@dataclass
class GateSection:
    """Status for one adapter capability area."""

    name: str
    status: str
    summary: str
    signals: list[EvidenceSignal] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "signals": [asdict(s) for s in self.signals],
            "missing": list(self.missing),
            "warnings": list(self.warnings),
        }


@dataclass
class DoneGateReport:
    """Complete MSN adapter done-gate report."""

    bundle_dir: str
    output_dir: str
    overall_status: str
    sections: list[GateSection]
    files_scanned: int
    source_role_rule: str
    generated_files: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "bundle_dir": self.bundle_dir,
            "output_dir": self.output_dir,
            "overall_status": self.overall_status,
            "files_scanned": self.files_scanned,
            "source_role_rule": self.source_role_rule,
            "sections": [s.as_dict() for s in self.sections],
            "generated_files": list(self.generated_files),
        }


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _iter_files(root: Path) -> Iterator[Path]:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def _lower_rel_files(root: Path) -> dict[str, Path]:
    return {_rel(path, root).lower(): path for path in _iter_files(root)}


def _find_by_name(files: Mapping[str, Path], *needles: str) -> list[Path]:
    lowered = [n.lower() for n in needles]
    return [path for rel, path in files.items() if all(n in rel for n in lowered)]


def _find_by_suffix(files: Mapping[str, Path], *suffixes: str) -> list[Path]:
    wanted = tuple(s.lower() for s in suffixes)
    return [path for rel, path in files.items() if rel.endswith(wanted)]


def _safe_read_text(path: Path, limit: int = 2_000_000) -> str:
    try:
        with path.open("rb") as fh:
            data = fh.read(limit)
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _safe_read_json(path: Path) -> Any | None:
    text = _safe_read_text(path)
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _walk_json(value: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, sub in value.items():
            yield str(key), sub
            yield from _walk_json(sub)
    elif isinstance(value, list):
        for sub in value:
            yield from _walk_json(sub)


def _json_has_key(data: Any, keys: set[str]) -> bool:
    keys_lower = {k.lower() for k in keys}
    for key, value in _walk_json(data):
        if key.lower() in keys_lower and value not in (None, "", [], {}):
            return True
    return False


def _json_has_value(data: Any, values: set[str]) -> bool:
    values_lower = {v.lower() for v in values}
    for _key, value in _walk_json(data):
        if isinstance(value, str) and value.lower() in values_lower:
            return True
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.lower() in values_lower:
                    return True
    return False


def _count_json_items(data: Any, likely_keys: Sequence[str]) -> int:
    keys = {k.lower() for k in likely_keys}
    best = 0
    for key, value in _walk_json(data):
        if key.lower() in keys and isinstance(value, list):
            best = max(best, len(value))
    if best:
        return best
    if isinstance(data, list):
        return len(data)
    return 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _html_text_signal(path: Path) -> tuple[int, bool, bool]:
    text = _safe_read_text(path, limit=500_000)
    stripped = re.sub(r"<[^>]+>", " ", text)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    has_title = "<title" in text.lower() or re.search(r"<h1\b", text, flags=re.I) is not None
    has_image = "<img" in text.lower() or "og:image" in text.lower()
    return len(stripped), has_title, has_image


def evaluate_article(bundle_dir: Path, files: Mapping[str, Path]) -> GateSection:
    signals: list[EvidenceSignal] = []
    warnings: list[str] = []
    missing: list[str] = []
    htmls = _find_by_name(files, "rendered-page.html") or _find_by_name(files, "article", ".html")
    article_jsons = _find_by_name(files, "article", ".json")
    manifest_jsons = _find_by_name(files, "manifest", ".json") + _find_by_name(files, "validation", ".json")

    best_html = htmls[0] if htmls else None
    if best_html:
        text_len, has_title, has_image = _html_text_signal(best_html)
        signals.append(EvidenceSignal("rendered_html", _rel(best_html, bundle_dir), "Best human-viewable page candidate", text_len))
        if text_len < 600:
            warnings.append("Rendered HTML text is small; article body may be incomplete.")
        if not has_title:
            warnings.append("Rendered HTML title/H1 was not detected.")
        if not has_image:
            warnings.append("Rendered HTML hero/OpenGraph image was not detected.")
    else:
        missing.append("rendered-page.html or article HTML")

    for path in article_jsons[:5]:
        data = _safe_read_json(path)
        if data is not None:
            signals.append(EvidenceSignal("article_json", _rel(path, bundle_dir), "Article JSON sidecar present", _count_json_items(data, ["paragraphs", "items", "sections"])))
            if _json_has_key(data, {"title", "headline", "source_url", "canonical_url", "body", "article_body"}):
                break

    if manifest_jsons:
        signals.append(EvidenceSignal("manifest_or_validation_json", _rel(manifest_jsons[0], bundle_dir), "Manifest/validation sidecar present"))
    else:
        warnings.append("No manifest/validation JSON found for article extraction metadata.")

    if best_html and not any(missing):
        status = STATUS_PASS if not warnings else STATUS_PARTIAL
        summary = "Article extraction has a viewable rendered HTML artifact."
    else:
        status = STATUS_FAIL
        summary = "Article extraction artifact is missing."
    return GateSection("article_extraction", status, summary, signals, missing, warnings)


def evaluate_comments_profiles(bundle_dir: Path, files: Mapping[str, Path]) -> GateSection:
    signals: list[EvidenceSignal] = []
    warnings: list[str] = []
    missing: list[str] = []
    comments = _find_by_name(files, "comments", ".json") + _find_by_name(files, "msn-comments", ".json")
    profiles = _find_by_name(files, "profiles", ".json") + _find_by_name(files, "profile-stats", ".json")
    htmls = _find_by_name(files, "comments", ".html")
    txts = _find_by_name(files, "comments", ".txt")

    max_comments = 0
    voted = 0
    deleted = 0
    for path in comments[:10]:
        data = _safe_read_json(path)
        count = _count_json_items(data, ["comments", "items", "threads", "results"]) if data is not None else 0
        max_comments = max(max_comments, count)
        if data is not None:
            for key, value in _walk_json(data):
                key_lower = key.lower()
                if key_lower in {"like_count", "likes", "comment_likes", "dislikes", "comment_dislikes"} and value not in (None, "", 0):
                    voted += 1
                if isinstance(value, str) and "deleted" in value.lower() and "guidelines" in value.lower():
                    deleted += 1
        signals.append(EvidenceSignal("comments_json", _rel(path, bundle_dir), "Comments JSON candidate", count))

    max_profiles = 0
    profile_stats = False
    for path in profiles[:10]:
        data = _safe_read_json(path)
        count = _count_json_items(data, ["profiles", "items", "results"]) if data is not None else 0
        max_profiles = max(max_profiles, count)
        if data is not None and _json_has_key(data, {"account_comments", "account_likes", "account_followers", "profile_cid", "canonical_url"}):
            profile_stats = True
        signals.append(EvidenceSignal("profiles_json", _rel(path, bundle_dir), "Profiles JSON candidate", count))

    if htmls:
        signals.append(EvidenceSignal("comments_html", _rel(htmls[0], bundle_dir), "Comments HTML viewer/export present"))
    if txts:
        signals.append(EvidenceSignal("comments_txt", _rel(txts[0], bundle_dir), "Readable comments TXT present"))
    if voted:
        signals.append(EvidenceSignal("comment_votes", None, "Comment vote fields observed", voted))
    if deleted:
        signals.append(EvidenceSignal("deleted_placeholders", None, "Deleted placeholder text observed", deleted))

    if not comments:
        missing.append("comments JSON/export")
    if not profiles:
        missing.append("profiles JSON/export")
    if profiles and not profile_stats:
        warnings.append("Profiles exist but account comments/likes/followers fields were not detected.")

    if comments and profiles:
        status = STATUS_PASS if profile_stats else STATUS_PARTIAL
        summary = "Comments/profile exports are present."
    elif comments:
        status = STATUS_PARTIAL
        summary = "Comments exist but profile exports are incomplete or missing."
    else:
        status = STATUS_FAIL
        summary = "Comments/profile export evidence is missing."
    return GateSection("comments_profile_extraction", status, summary, signals, missing, warnings)


def evaluate_offline_archive(bundle_dir: Path, files: Mapping[str, Path]) -> GateSection:
    signals: list[EvidenceSignal] = []
    warnings: list[str] = []
    missing: list[str] = []
    rendered = _find_by_name(files, "rendered-page.html")
    viewer = _find_by_name(files, "open_local_viewer.cmd") + _find_by_name(files, "local_viewer", "index")
    warc = [p for rel, p in files.items() if rel.endswith(".warc") or rel.endswith(".warc.gz")]
    wacz = [p for rel, p in files.items() if rel.endswith(".wacz")]
    compatible = [p for p in wacz if "compatible" in p.name.lower() or "replayweb" in p.name.lower()]
    strict = [p for p in wacz if p not in compatible]

    if rendered:
        signals.append(EvidenceSignal("best_viewable_html", _rel(rendered[0], bundle_dir), "Best viewable offline article page"))
    else:
        missing.append("rendered-page.html")
    if viewer:
        signals.append(EvidenceSignal("local_viewer", _rel(viewer[0], bundle_dir), "Local viewer entry point present"))
    else:
        missing.append("local viewer entry point")
    if warc:
        signals.append(EvidenceSignal("warc_gz", _rel(warc[0], bundle_dir), "ReplayWeb partial archive candidate"))
    else:
        missing.append("rendered-page.warc.gz or WARC archive")
    if strict:
        signals.append(EvidenceSignal("strict_wacz", _rel(strict[0], bundle_dir), "Strict/current WACZ candidate; manual validation required"))
        warnings.append("Strict WACZ must remain labelled experimental unless ReplayWeb validation succeeds.")
    if compatible:
        signals.append(EvidenceSignal("replayweb_compatible_wacz", _rel(compatible[0], bundle_dir), "ReplayWeb-compatible WACZ candidate present"))
    else:
        warnings.append("ReplayWeb-compatible WACZ candidate was not detected.")

    if rendered and viewer and warc:
        status = STATUS_PASS if compatible else STATUS_PARTIAL
        summary = "Offline viewer/archive artifacts are present; ReplayWeb WACZ remains a manual validation area."
    else:
        status = STATUS_FAIL
        summary = "Offline viewer/archive artifacts are missing required pieces."
    return GateSection("offline_webpage_viewer", status, summary, signals, missing, warnings)


def evaluate_media(bundle_dir: Path, files: Mapping[str, Path]) -> GateSection:
    signals: list[EvidenceSignal] = []
    warnings: list[str] = []
    missing: list[str] = []
    inventory = _find_by_name(files, "media", "inventory", ".json") + _find_by_name(files, "media", "inventory", ".csv")
    results = _find_by_name(files, "media", "download", ".json") + _find_by_name(files, "media", "results", ".json")
    images = [p for rel, p in files.items() if Path(rel).suffix.lower() in IMAGE_EXTENSIONS]
    videos = [p for rel, p in files.items() if Path(rel).suffix.lower() in VIDEO_EXTENSIONS]
    streams = [p for rel, p in files.items() if Path(rel).suffix.lower() in STREAM_EXTENSIONS]

    if inventory:
        signals.append(EvidenceSignal("media_inventory", _rel(inventory[0], bundle_dir), "Media candidates registered"))
    else:
        missing.append("media inventory JSON/CSV")
    if results:
        signals.append(EvidenceSignal("media_download_results", _rel(results[0], bundle_dir), "Media download/status results present"))
    else:
        warnings.append("Media download results/status sidecar was not detected.")
    if images:
        signals.append(EvidenceSignal("downloaded_images", None, "Image files present", len(images)))
    if videos:
        signals.append(EvidenceSignal("downloaded_videos", None, "Video files present", len(videos)))
    if streams:
        signals.append(EvidenceSignal("stream_manifests", None, "HLS/DASH manifest files present", len(streams)))

    hashed = 0
    for path in images[:5] + videos[:5] + streams[:5]:
        try:
            if path.stat().st_size > 0:
                hashed += 1
        except OSError:
            pass
    if hashed:
        signals.append(EvidenceSignal("local_media_hash_ready", None, "Local media files can be hashed", hashed))

    # Inspect JSON results for blocked/external/streamed status so non-downloadable video is still documented.
    status_values = set()
    for path in results[:5] + [p for p in inventory[:5] if p.suffix.lower() == ".json"]:
        data = _safe_read_json(path)
        if data is None:
            continue
        for key, value in _walk_json(data):
            if key.lower() in {"status", "download_status", "media_status", "availability_status"} and isinstance(value, str):
                status_values.add(value.upper())
    if status_values:
        signals.append(EvidenceSignal("media_status_values", None, "Registered media statuses", sorted(status_values)))

    if inventory and (results or images or videos or streams):
        status = STATUS_PASS
        summary = "Media candidates and download/status evidence are present."
    elif inventory:
        status = STATUS_PARTIAL
        summary = "Media candidates are registered, but download/status outputs are incomplete."
    else:
        status = STATUS_FAIL
        summary = "Media discovery/download registration is missing."
    return GateSection("media_download_registration", status, summary, signals, missing, warnings)


def evaluate_provenance(bundle_dir: Path, files: Mapping[str, Path]) -> GateSection:
    signals: list[EvidenceSignal] = []
    warnings: list[str] = []
    missing: list[str] = []
    jsons = _find_by_suffix(files, ".json")
    source_role_found = False
    primary_status_found = False
    source_chain_found = False
    republisher_distinction = False
    evidence_files = []
    for path in jsons[:80]:
        data = _safe_read_json(path)
        if data is None:
            continue
        has_role = _json_has_key(data, {"source_role", "claim_source_role", "media_source_role"}) or _json_has_value(data, {"primary/original authored source", "secondary/outside perspective source", "tertiary/propagated source"})
        has_status = _json_has_key(data, {"primary_source_status"}) or _json_has_value(data, SOURCE_STATUS_LABELS)
        has_chain = _json_has_key(data, {"source_chain_gap", "visible_source_credit", "claimed_original_source", "original_source_url", "publisher_framing_summary", "media_observed_on_url"})
        has_repub = _json_has_key(data, {"publisher_name", "publisher_page_url", "source_platform", "visible_source_credit", "claimed_original_source"})
        if has_role or has_status or has_chain or has_repub:
            evidence_files.append(path)
        source_role_found = source_role_found or has_role
        primary_status_found = primary_status_found or has_status
        source_chain_found = source_chain_found or has_chain
        republisher_distinction = republisher_distinction or has_repub

    for path in evidence_files[:8]:
        signals.append(EvidenceSignal("provenance_json", _rel(path, bundle_dir), "Source-role/source-chain metadata present"))
    if source_role_found:
        signals.append(EvidenceSignal("source_role", None, "Source role fields detected"))
    else:
        missing.append("source_role or claim_source_role fields")
    if primary_status_found:
        signals.append(EvidenceSignal("primary_source_status", None, "Primary-source status fields/labels detected"))
    else:
        missing.append("primary_source_status labels")
    if source_chain_found:
        signals.append(EvidenceSignal("media_source_chain", None, "Media/source-chain fields detected"))
    else:
        missing.append("media source-chain fields")
    if republisher_distinction:
        signals.append(EvidenceSignal("republisher_distinction", None, "Publisher/platform/source-credit separation detected"))
    else:
        warnings.append("No explicit publisher/platform/source-credit separation detected.")

    if source_role_found and primary_status_found and source_chain_found:
        status = STATUS_PASS if republisher_distinction else STATUS_PARTIAL
        summary = "Source-role and source-chain provenance are represented."
    else:
        status = STATUS_FAIL
        summary = "Source-role/source-chain provenance is incomplete."
    return GateSection("source_role_provenance", status, summary, signals, missing, warnings)


def evaluate_manual_validation(bundle_dir: Path, files: Mapping[str, Path]) -> GateSection:
    signals: list[EvidenceSignal] = []
    warnings: list[str] = []
    missing: list[str] = []
    result_jsons = _find_by_name(files, "manual", "validation", ".json") + _find_by_name(files, "operator", "validation", ".json")
    templates = _find_by_name(files, "manual", "validation", ".md") + _find_by_name(files, "operator", "steps", ".md")
    status_values: list[str] = []
    for path in result_jsons[:10]:
        data = _safe_read_json(path)
        if data is None:
            continue
        signals.append(EvidenceSignal("manual_validation_json", _rel(path, bundle_dir), "Manual/operator validation result present"))
        for key, value in _walk_json(data):
            if key.lower().endswith("status") and isinstance(value, str):
                status_values.append(value.upper())
    if templates:
        signals.append(EvidenceSignal("manual_validation_template", _rel(templates[0], bundle_dir), "Manual validation checklist/template present"))
    if status_values:
        signals.append(EvidenceSignal("manual_status_values", None, "Manual status values observed", sorted(set(status_values))))

    if result_jsons and any(v == STATUS_FAIL for v in status_values):
        status = STATUS_FAIL
        summary = "Manual validation result contains a failure."
    elif result_jsons and any(v in {STATUS_PASS, "CONFIRMED", "COMPLETE"} for v in status_values):
        status = STATUS_PASS
        summary = "Manual validation result is present."
    elif templates:
        status = STATUS_PARTIAL
        summary = "Manual validation checklist exists but completed result was not detected."
        warnings.append("Run manual validation on a real MSN article before declaring live confidence.")
    else:
        status = STATUS_PARTIAL
        summary = "Manual validation evidence is not present."
        missing.append("manual validation checklist/result")
    return GateSection("manual_live_validation", status, summary, signals, missing, warnings)


def evaluate_release_outputs(bundle_dir: Path, files: Mapping[str, Path]) -> GateSection:
    signals: list[EvidenceSignal] = []
    warnings: list[str] = []
    missing: list[str] = []
    final_reports = _find_by_name(files, "final", "validation", ".json") + _find_by_name(files, "msn_adapter_final_validation_report", ".json")
    readiness = _find_by_name(files, "readiness", ".json")
    release = _find_by_name(files, "release", "report", ".json")
    total_package = _find_by_name(files, "total", "package", ".json") + _find_by_name(files, "package", "manifest", ".json")
    markdown = _find_by_name(files, "final", "validation", ".md") + _find_by_name(files, "release", "report", ".md")

    for name, paths in [
        ("final_validation_report", final_reports),
        ("readiness_report", readiness),
        ("release_report", release),
        ("total_package_manifest", total_package),
        ("human_markdown_report", markdown),
    ]:
        if paths:
            signals.append(EvidenceSignal(name, _rel(paths[0], bundle_dir), f"{name} present"))
        else:
            missing.append(name)

    if final_reports and total_package:
        status = STATUS_PASS if not missing else STATUS_PARTIAL
        summary = "Release/final validation outputs are present."
    else:
        status = STATUS_PARTIAL
        summary = "Release/final validation outputs are not yet complete."
    return GateSection("release_reporting", status, summary, signals, missing, warnings)


def determine_overall(sections: Sequence[GateSection]) -> str:
    by_name = {s.name: s for s in sections}
    core_names = ["article_extraction", "comments_profile_extraction", "offline_webpage_viewer", "source_role_provenance"]
    core = [by_name[name].status for name in core_names]
    media = by_name["media_download_registration"].status
    manual = by_name["manual_live_validation"].status
    release = by_name["release_reporting"].status

    if all(s == STATUS_PASS for s in core) and media == STATUS_PASS and manual == STATUS_PASS and release in {STATUS_PASS, STATUS_PARTIAL}:
        return OVERALL_READY
    if all(s in {STATUS_PASS, STATUS_PARTIAL} for s in core) and media in {STATUS_PASS, STATUS_PARTIAL}:
        return OVERALL_CONFIDENT
    if any(s == STATUS_PASS for s in core) and media in {STATUS_PASS, STATUS_PARTIAL, STATUS_FAIL}:
        return OVERALL_PARTIAL
    return OVERALL_NOT_READY


def build_done_gate_report(bundle_dir: str | Path, output_dir: str | Path | None = None) -> DoneGateReport:
    bundle_path = Path(bundle_dir).resolve()
    if output_dir is None:
        output_path = bundle_path / "reports"
    else:
        output_path = Path(output_dir).resolve()
    files = _lower_rel_files(bundle_path)
    sections = [
        evaluate_article(bundle_path, files),
        evaluate_comments_profiles(bundle_path, files),
        evaluate_offline_archive(bundle_path, files),
        evaluate_media(bundle_path, files),
        evaluate_provenance(bundle_path, files),
        evaluate_manual_validation(bundle_path, files),
        evaluate_release_outputs(bundle_path, files),
    ]
    return DoneGateReport(
        bundle_dir=str(bundle_path),
        output_dir=str(output_path),
        overall_status=determine_overall(sections),
        sections=sections,
        files_scanned=len(files),
        source_role_rule=(
            "MSN/publisher pages are captured surfaces and outside framing unless the artifact itself is "
            "the original authored source; primary/source-chain status remains claim/item scoped."
        ),
    )


def _status_symbol(status: str) -> str:
    return {
        STATUS_PASS: "PASS",
        STATUS_PARTIAL: "PARTIAL",
        STATUS_FAIL: "FAIL",
        STATUS_NOT_APPLICABLE: "N/A",
        STATUS_UNKNOWN: "UNKNOWN",
    }.get(status, status)


def render_markdown(report: DoneGateReport) -> str:
    lines = [
        "# MSN Adapter Done Gate Report",
        "",
        f"**Overall status:** `{report.overall_status}`",
        f"**Bundle:** `{report.bundle_dir}`",
        f"**Files scanned:** {report.files_scanned}",
        "",
        "## Source-role rule",
        "",
        report.source_role_rule,
        "",
        "## Capability matrix",
        "",
        "| Area | Status | Summary |",
        "| --- | --- | --- |",
    ]
    for section in report.sections:
        lines.append(f"| `{section.name}` | `{_status_symbol(section.status)}` | {section.summary} |")
    lines.extend(["", "## Details", ""])
    for section in report.sections:
        lines.extend([f"### {section.name}", "", f"Status: `{section.status}`", "", section.summary, ""])
        if section.signals:
            lines.append("Signals:")
            for signal in section.signals:
                path = f" — `{signal.path}`" if signal.path else ""
                value = f" — `{signal.value}`" if signal.value not in (None, "") else ""
                detail = f": {signal.detail}" if signal.detail else ""
                lines.append(f"- {signal.name}{path}{value}{detail}")
            lines.append("")
        if section.missing:
            lines.append("Missing:")
            for item in section.missing:
                lines.append(f"- {item}")
            lines.append("")
        if section.warnings:
            lines.append("Warnings:")
            for item in section.warnings:
                lines.append(f"- {item}")
            lines.append("")
    lines.extend([
        "## Interpretation",
        "",
        "`READY_FOR_MSN_OPERATOR_USE` requires completed live/manual evidence. `CONFIDENT_WITH_MANUAL_REVIEW` means the adapter structure is strong but real MSN output still needs operator confirmation, especially for ReplayWeb/WACZ and media/video availability.",
        "",
    ])
    return "\n".join(lines)


def write_done_gate_report(report: DoneGateReport) -> DoneGateReport:
    output_path = Path(report.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "MSN_ADAPTER_DONE_GATE_REPORT.json"
    md_path = output_path / "MSN_ADAPTER_DONE_GATE_REPORT.md"
    tmp_report = report.as_dict()
    json_path.write_text(json.dumps(tmp_report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    report.generated_files = [str(json_path), str(md_path)]
    json_path.write_text(json.dumps(report.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def run_done_gate(bundle_dir: str | Path, output_dir: str | Path | None = None) -> DoneGateReport:
    report = build_done_gate_report(bundle_dir, output_dir)
    return write_done_gate_report(report)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the final MSN adapter done gate on an existing output folder.")
    parser.add_argument("--bundle-dir", required=True, help="Existing MSN output/bundle directory to scan.")
    parser.add_argument("--output-dir", default=None, help="Directory for JSON/Markdown reports. Defaults to bundle/reports.")
    parser.add_argument("--json", action="store_true", help="Print the full report JSON to stdout.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = run_done_gate(args.bundle_dir, args.output_dir)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"MSN adapter done gate status: {report.overall_status}")
        for path in report.generated_files:
            print(path)
    return 0 if report.overall_status in {OVERALL_READY, OVERALL_CONFIDENT, OVERALL_PARTIAL} else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
