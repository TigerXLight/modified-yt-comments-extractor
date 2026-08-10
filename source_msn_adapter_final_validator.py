from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from source_msn_adapter_manifest import extract_msn_article_from_html_path


MSN_FINAL_VALIDATION_SCHEMA_VERSION = "msn_source_adapter_final_validation_v1"
MSN_FINAL_VALIDATION_REPORT_JSON = "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json"
MSN_FINAL_VALIDATION_REPORT_MD = "MSN_ADAPTER_FINAL_VALIDATION_REPORT.md"

STATUS_PASS = "PASS"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAIL = "FAIL"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"

OVERALL_CONFIDENT_WITH_MANUAL_REVIEW = "CONFIDENT_WITH_MANUAL_REVIEW"
OVERALL_PARTIAL_NEEDS_REVIEW = "PARTIAL_NEEDS_REVIEW"
OVERALL_NOT_READY = "NOT_READY"

_ARTICLE_HTML_NAMES = ("rendered-page.html", "article.html", "page.html")
_STRICT_WACZ_NAMES = ("archive.viewable-live-capture.wacz", "archive.wacz")
_COMPAT_WACZ_NAMES = ("archive.replayweb-compatible.wacz", "replayweb-compatible.wacz", "archive.compat.wacz")
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp", ".svg"}
_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi"}
_STREAM_EXTENSIONS = {".m3u8", ".mpd"}
_IGNORE_DIR_PARTS = {".git", "__pycache__", ".pytest_cache", "venv", ".venv", "node_modules"}


@dataclass(frozen=True)
class MsnFinalValidationArea:
    name: str
    status: str
    summary: str
    required: bool = True
    evidence_paths: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnFinalValidationReport:
    schema_version: str = MSN_FINAL_VALIDATION_SCHEMA_VERSION
    adapter_name: str = "msn_source_adapter"
    root_path: str = ""
    source_url: str = ""
    overall_status: str = OVERALL_NOT_READY
    areas: tuple[MsnFinalValidationArea, ...] = ()
    counts: Mapping[str, int] = field(default_factory=dict)
    output_paths: Mapping[str, str] = field(default_factory=dict)
    msn_republisher_note: str = ""
    manual_review_required: bool = True
    final_confidence_statement: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    def _generator() -> Iterable[Path]:
        for path in root.rglob("*"):
            if any(part in _IGNORE_DIR_PARTS for part in path.parts):
                continue
            if path.is_file():
                yield path
    return _generator()


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return data if isinstance(data, Mapping) else {}


def _find_named(root: Path, names: Sequence[str]) -> tuple[Path, ...]:
    lowered = {name.lower() for name in names}
    return tuple(path for path in _iter_files(root) if path.name.lower() in lowered)


def _find_by_name_contains(root: Path, *tokens: str, suffixes: Sequence[str] | None = None) -> tuple[Path, ...]:
    lowered_tokens = tuple(token.lower() for token in tokens if token)
    allowed_suffixes = {suffix.lower() for suffix in (suffixes or ())}
    matches: list[Path] = []
    for path in _iter_files(root):
        name = path.name.lower()
        if allowed_suffixes and path.suffix.lower() not in allowed_suffixes:
            continue
        if all(token in name for token in lowered_tokens):
            matches.append(path)
    return tuple(matches)


def _find_rendered_html(root: Path) -> Path | None:
    exact = _find_named(root, _ARTICLE_HTML_NAMES)
    if exact:
        return exact[0]
    htmls = [path for path in _iter_files(root) if path.suffix.lower() in {".html", ".htm"}]
    for path in htmls:
        if "viewer" not in path.name.lower() and "comment" not in path.name.lower():
            return path
    return None


def _load_first_comments_json(paths: Sequence[Path]) -> Mapping[str, Any]:
    for path in paths:
        data = _read_json(path)
        if isinstance(data.get("comments"), list) or isinstance(data.get("items"), list):
            return data
    return {}


def _count_comments(data: Mapping[str, Any]) -> int:
    comments = data.get("comments")
    if not isinstance(comments, list):
        comments = data.get("items")
    if not isinstance(comments, list):
        return 0

    def walk(items: Iterable[Any]) -> Iterable[Mapping[str, Any]]:
        for item in items:
            if isinstance(item, Mapping):
                yield item
                replies = item.get("replies")
                if isinstance(replies, list):
                    yield from walk(replies)

    return sum(1 for _ in walk(comments))


def _count_profiles(paths: Sequence[Path]) -> int:
    total = 0
    for path in paths:
        data = _read_json(path)
        profiles = data.get("profiles")
        if isinstance(profiles, list):
            total += len(profiles)
        elif isinstance(profiles, Mapping):
            total += len(profiles)
    return total


def _validation_json(root: Path) -> Mapping[str, Any]:
    candidates = _find_named(root, ("validation.json",))
    return _read_json(candidates[0]) if candidates else {}


def _existing_bundle_json(root: Path) -> Mapping[str, Any]:
    candidates = list(_find_by_name_contains(root, "bundle", suffixes=(".json",)))
    candidates += list(_find_by_name_contains(root, "source", "adapter", suffixes=(".json",)))
    for path in candidates:
        data = _read_json(path)
        if data.get("adapter_name") == "msn_source_adapter" or data.get("schema_version") == "msn_source_adapter_bundle_v1":
            return data
    return {}


def _existing_readiness_json(root: Path) -> Mapping[str, Any]:
    for path in _find_by_name_contains(root, "readiness", suffixes=(".json",)):
        data = _read_json(path)
        if str(data.get("schema_version") or "").startswith("msn_source_adapter_readiness"):
            return data
    return {}


def _asset_descriptions(bundle: Mapping[str, Any]) -> tuple[str, ...]:
    manifest = bundle.get("manifest")
    if not isinstance(manifest, Mapping):
        return ()
    descriptions: list[str] = []
    for asset in manifest.get("assets") or ():
        if isinstance(asset, Mapping):
            descriptions.append(str(asset.get("description") or ""))
    return tuple(descriptions)


def _provenance_records(bundle: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    manifest = bundle.get("manifest")
    if not isinstance(manifest, Mapping):
        return ()
    records = manifest.get("provenance_records") or ()
    return tuple(record for record in records if isinstance(record, Mapping))


def _media_source_chain_notes(bundle: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    manifest = bundle.get("manifest")
    if not isinstance(manifest, Mapping):
        return ()
    records = manifest.get("media_source_chain_notes") or ()
    return tuple(record for record in records if isinstance(record, Mapping))


def _article_area(root: Path, rendered_html: Path | None, source_url: str) -> tuple[MsnFinalValidationArea, Mapping[str, Any]]:
    if rendered_html is None:
        return MsnFinalValidationArea(
            name="article_extraction",
            status=STATUS_FAIL,
            summary="No rendered article HTML file was found.",
            limitations=("Cannot validate title, publisher, article body, or visible source credits without rendered HTML.",),
        ), {}
    article = extract_msn_article_from_html_path(rendered_html, source_url=source_url)
    article_data = article.to_dict()
    missing: list[str] = []
    if not article.title:
        missing.append("title")
    if not article.publisher_name:
        missing.append("publisher/source")
    if not article.article_body_lines:
        missing.append("article body")
    if not article.hero_image_url:
        missing.append("hero image")
    if article.title and article.publisher_name and article.article_body_lines:
        status = STATUS_PASS if article.hero_image_url else STATUS_PARTIAL
    else:
        status = STATUS_PARTIAL if article.title or article.article_body_lines else STATUS_FAIL
    summary = (
        f"Rendered article parsed from {_rel(rendered_html, root)} with title={bool(article.title)}, "
        f"publisher={article.publisher_name or 'unknown'}, body_lines={len(article.article_body_lines)}, "
        f"hero_image={bool(article.hero_image_url)}, visible_credit={article.visible_source_credit or 'none'}."
    )
    limitations = tuple(f"Missing or weak article field: {field_name}." for field_name in missing)
    return MsnFinalValidationArea(
        name="article_extraction",
        status=status,
        summary=summary,
        evidence_paths=(_rel(rendered_html, root),),
        limitations=limitations,
    ), article_data


def _comments_area(root: Path) -> tuple[MsnFinalValidationArea, int, int]:
    comment_jsons = tuple(
        path for path in _find_by_name_contains(root, "comment", suffixes=(".json",))
        if "final_validation" not in path.name.lower() and "readiness" not in path.name.lower() and "release" not in path.name.lower()
    )
    profile_files = tuple(path for path in _iter_files(root) if "profile" in path.name.lower() and path.suffix.lower() in {".json", ".csv", ".txt", ".html", ".md"})
    comments_data = _load_first_comments_json(comment_jsons)
    comments_count = _count_comments(comments_data)
    profiles_count = _count_profiles(tuple(path for path in profile_files if path.suffix.lower() == ".json"))
    if comments_count and profile_files:
        status = STATUS_PASS
    elif comments_count or profile_files:
        status = STATUS_PARTIAL
    else:
        status = STATUS_FAIL
    summary = f"Found {len(comment_jsons)} comment JSON candidate(s), {comments_count} comment/reply item(s), and {len(profile_files)} profile export file(s)."
    limitations = ()
    if status != STATUS_PASS:
        limitations = ("Expected MSN comments JSON plus separate profile export files for full confidence.",)
    return MsnFinalValidationArea(
        name="comments_profile_extraction",
        status=status,
        summary=summary,
        evidence_paths=tuple(_rel(path, root) for path in (*comment_jsons[:3], *profile_files[:5])),
        limitations=limitations,
    ), comments_count, profiles_count


def _offline_viewer_area(root: Path) -> MsnFinalValidationArea:
    html = _find_rendered_html(root)
    viewer_cmds = _find_named(root, ("open_local_viewer.cmd",))
    viewer_indexes = tuple(path for path in _find_named(root, ("index.html",)) if "local_viewer" in path.as_posix().lower())
    warcs = tuple(path for path in _iter_files(root) if path.name.lower().endswith(".warc.gz") or path.suffix.lower() == ".warc")
    strict_wacz = _find_named(root, _STRICT_WACZ_NAMES)
    compat_wacz = _find_named(root, _COMPAT_WACZ_NAMES)
    validation = _validation_json(root)
    strict_status = str(validation.get("strict_wacz_status") or validation.get("wacz_status") or "")
    has_honest_strict_label = bool(strict_status) or bool(strict_wacz)
    if html and viewer_cmds and warcs and has_honest_strict_label:
        status = STATUS_PASS
    elif html and (viewer_cmds or warcs):
        status = STATUS_PARTIAL
    else:
        status = STATUS_FAIL
    summary = (
        f"offline_html={bool(html)}, viewer_launcher={bool(viewer_cmds)}, viewer_index={bool(viewer_indexes)}, "
        f"warc_count={len(warcs)}, strict_wacz_count={len(strict_wacz)}, compatible_wacz_count={len(compat_wacz)}, "
        f"strict_wacz_status={strict_status or 'not recorded'}."
    )
    limitations = (
        "Raw WARC.GZ replay remains a partial/manual ReplayWeb check unless a visual replay smoke result is recorded.",
        "Strict WACZ must stay experimental/possibly unsupported unless a compatible ReplayWeb WACZ is validated.",
    )
    evidence = tuple(_rel(path, root) for path in [p for p in (html, *viewer_cmds[:1], *viewer_indexes[:1], *warcs[:2], *strict_wacz[:1], *compat_wacz[:1]) if p])
    return MsnFinalValidationArea(
        name="offline_webpage_viewer",
        status=status,
        summary=summary,
        evidence_paths=evidence,
        limitations=limitations,
    )


def _media_area(root: Path, article_data: Mapping[str, Any], bundle: Mapping[str, Any]) -> tuple[MsnFinalValidationArea, int, int, int]:
    media_candidates: list[str] = []
    media_candidates.extend(str(article_data.get(key) or "") for key in ("hero_image_url", "hero_image_alt", "visible_source_credit"))
    for record in bundle.get("media_records") or ():
        if isinstance(record, Mapping):
            resource = record.get("resource")
            if isinstance(resource, Mapping):
                media_candidates.append(str(resource.get("url") or ""))
    media_candidate_count = sum(1 for item in media_candidates if item)
    local_media_files = tuple(
        path for path in _iter_files(root)
        if path.suffix.lower() in (_IMAGE_EXTENSIONS | _VIDEO_EXTENSIONS | _STREAM_EXTENSIONS)
        and not path.name.lower().startswith("comments-region")
        and not path.name.lower().startswith("full-comments-thread")
    )
    stream_files = tuple(path for path in local_media_files if path.suffix.lower() in _STREAM_EXTENSIONS)
    video_files = tuple(path for path in local_media_files if path.suffix.lower() in _VIDEO_EXTENSIONS)
    image_files = tuple(path for path in local_media_files if path.suffix.lower() in _IMAGE_EXTENSIONS)
    if local_media_files:
        status = STATUS_PASS
    elif media_candidate_count:
        status = STATUS_PARTIAL
    else:
        status = STATUS_FAIL
    summary = (
        f"media_candidates={media_candidate_count}, local_media_files={len(local_media_files)}, "
        f"images={len(image_files)}, videos={len(video_files)}, stream_manifests={len(stream_files)}."
    )
    limitations = ()
    if status == STATUS_PARTIAL:
        limitations = (
            "Media candidates were detected or registered, but no explicit local media file was found in this output folder.",
            "For video, HLS/DASH/stream/blob candidates may be metadata-only and should not be reported as fully downloaded.",
        )
    elif status == STATUS_FAIL:
        limitations = ("No media candidates or local media files were detected; article images/video remain unvalidated.",)
    return MsnFinalValidationArea(
        name="media_discovery_download_registration",
        status=status,
        summary=summary,
        required=False,
        evidence_paths=tuple(_rel(path, root) for path in local_media_files[:10]),
        limitations=limitations,
    ), media_candidate_count, len(local_media_files), len(stream_files) + len(video_files)


def _provenance_area(root: Path, article_data: Mapping[str, Any], bundle: Mapping[str, Any]) -> MsnFinalValidationArea:
    provenance = _provenance_records(bundle)
    media_notes = _media_source_chain_notes(bundle)
    article_role = str(article_data.get("source_role") or "")
    primary_status = str(article_data.get("primary_source_status") or "")
    publisher = str(article_data.get("publisher_name") or "")
    visible_credit = str(article_data.get("visible_source_credit") or "")
    has_repost_separation = bool(publisher and publisher.upper() != "MSN" and ("SECONDARY" in primary_status or "SECONDARY" in article_role))
    has_media_chain = bool(media_notes or visible_credit)
    if provenance and has_repost_separation and has_media_chain:
        status = STATUS_PASS
    elif provenance or has_repost_separation or has_media_chain:
        status = STATUS_PARTIAL
    else:
        status = STATUS_FAIL
    summary = (
        f"provenance_records={len(provenance)}, media_source_chain_notes={len(media_notes)}, "
        f"publisher={publisher or 'unknown'}, article_role={article_role or 'unknown'}, primary_status={primary_status or 'unknown'}, "
        f"visible_media_credit={visible_credit or 'none'}."
    )
    limitations = (
        "MSN/The Independent/visible media credit/original uploader must remain separate; the validator checks structure but does not prove original source location.",
    )
    return MsnFinalValidationArea(
        name="source_role_and_media_source_chain",
        status=status,
        evidence_paths=tuple(_rel(path, root) for path in _find_by_name_contains(root, "bundle", suffixes=(".json",))[:3]),
        summary=summary,
        limitations=limitations,
    )


def _total_manifest_area(root: Path, bundle: Mapping[str, Any], readiness: Mapping[str, Any]) -> MsnFinalValidationArea:
    manifest_files = tuple(path for path in _iter_files(root) if "manifest" in path.name.lower() and path.suffix.lower() == ".json")
    release_files = tuple(path for path in _iter_files(root) if "release" in path.name.lower() and path.suffix.lower() in {".json", ".md"})
    readiness_files = tuple(path for path in _iter_files(root) if "readiness" in path.name.lower() and path.suffix.lower() == ".json")
    has_bundle_manifest = bool(bundle.get("manifest"))
    has_readiness = bool(readiness)
    if has_bundle_manifest and has_readiness and release_files:
        status = STATUS_PASS
    elif has_bundle_manifest or manifest_files or has_readiness or release_files:
        status = STATUS_PARTIAL
    else:
        status = STATUS_FAIL
    summary = (
        f"manifest_files={len(manifest_files)}, readiness_files={len(readiness_files)}, release_files={len(release_files)}, "
        f"embedded_bundle_manifest={has_bundle_manifest}."
    )
    limitations = () if status == STATUS_PASS else ("Expected bundle/readiness/release report outputs for complete MSN adapter release evidence.",)
    return MsnFinalValidationArea(
        name="total_export_manifest_and_release_outputs",
        status=status,
        evidence_paths=tuple(_rel(path, root) for path in (*manifest_files[:5], *readiness_files[:2], *release_files[:4])),
        summary=summary,
        limitations=limitations,
    )


def _overall_status(areas: Sequence[MsnFinalValidationArea]) -> str:
    required = [area for area in areas if area.required]
    if any(area.status == STATUS_FAIL for area in required):
        return OVERALL_NOT_READY
    if all(area.status == STATUS_PASS for area in required):
        optional = [area for area in areas if not area.required]
        if any(area.status == STATUS_FAIL for area in optional):
            return OVERALL_PARTIAL_NEEDS_REVIEW
        return OVERALL_CONFIDENT_WITH_MANUAL_REVIEW
    return OVERALL_PARTIAL_NEEDS_REVIEW


def build_msn_adapter_final_validation_report(root_path: str | Path, *, source_url: str = "") -> MsnFinalValidationReport:
    root = Path(root_path)
    rendered_html = _find_rendered_html(root)
    article_area, article_data = _article_area(root, rendered_html, source_url)
    comments_area, comments_count, profiles_count = _comments_area(root)
    offline_area = _offline_viewer_area(root)
    bundle = _existing_bundle_json(root)
    readiness = _existing_readiness_json(root)
    media_area, media_candidates, local_media, video_or_streams = _media_area(root, article_data, bundle)
    provenance_area = _provenance_area(root, article_data, bundle)
    total_manifest_area = _total_manifest_area(root, bundle, readiness)
    areas = (article_area, comments_area, offline_area, media_area, provenance_area, total_manifest_area)
    overall = _overall_status(areas)
    publisher = str(article_data.get("publisher_name") or "unknown")
    credit = str(article_data.get("visible_source_credit") or "none")
    republisher_note = (
        f"MSN must be treated as the captured platform/republishing surface. Detected publisher/source: {publisher}. "
        f"Visible media credit: {credit}. Do not treat MSN, a publisher repost, or a visible credit as the original primary source unless the original authored source is located."
    )
    if overall == OVERALL_CONFIDENT_WITH_MANUAL_REVIEW:
        final_statement = (
            "The MSN adapter output is structurally complete enough for confident manual operation: article, comments/profile, offline viewer, provenance, and release outputs are present. "
            "Manual live review is still required for ReplayWeb/WACZ behaviour and changing MSN media delivery."
        )
    elif overall == OVERALL_PARTIAL_NEEDS_REVIEW:
        final_statement = "The MSN adapter output is partially complete and needs manual review of the PARTIAL/FAIL areas before calling the capture complete."
    else:
        final_statement = "The MSN adapter output is not ready; one or more required areas failed validation."
    return MsnFinalValidationReport(
        root_path=str(root),
        source_url=source_url,
        overall_status=overall,
        areas=areas,
        counts={
            "comment_items": comments_count,
            "profile_records": profiles_count,
            "media_candidates": media_candidates,
            "local_media_files": local_media,
            "video_or_stream_candidates": video_or_streams,
            "areas_pass": sum(1 for area in areas if area.status == STATUS_PASS),
            "areas_partial": sum(1 for area in areas if area.status == STATUS_PARTIAL),
            "areas_fail": sum(1 for area in areas if area.status == STATUS_FAIL),
        },
        msn_republisher_note=republisher_note,
        final_confidence_statement=final_statement,
    )


def render_msn_adapter_final_validation_markdown(report: MsnFinalValidationReport | Mapping[str, Any]) -> str:
    data = report.to_dict() if hasattr(report, "to_dict") else report
    lines = [
        "# MSN Adapter Final Validation Report",
        "",
        f"Schema version: `{data.get('schema_version')}`",
        f"Adapter: `{data.get('adapter_name')}`",
        f"Root path: `{data.get('root_path')}`",
        f"Source URL: `{data.get('source_url') or 'not supplied'}`",
        f"Overall status: `{data.get('overall_status')}`",
        f"Manual review required: `{data.get('manual_review_required')}`",
        "",
        "## Final confidence statement",
        "",
        str(data.get("final_confidence_statement") or ""),
        "",
        "## MSN republisher/source-chain note",
        "",
        str(data.get("msn_republisher_note") or ""),
        "",
        "## Counts",
        "",
    ]
    for key, value in (data.get("counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Areas", ""])
    for area in data.get("areas") or []:
        lines.append(f"### {area.get('name')}")
        lines.append("")
        lines.append(f"Status: `{area.get('status')}`")
        lines.append(f"Required: `{area.get('required')}`")
        lines.append("")
        lines.append(str(area.get("summary") or ""))
        if area.get("evidence_paths"):
            lines.append("")
            lines.append("Evidence paths:")
            for path in area.get("evidence_paths") or []:
                lines.append(f"- `{path}`")
        if area.get("limitations"):
            lines.append("")
            lines.append("Limitations:")
            for limitation in area.get("limitations") or []:
                lines.append(f"- {limitation}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_msn_adapter_final_validation_outputs(
    root_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    source_url: str = "",
) -> dict[str, str]:
    report = build_msn_adapter_final_validation_report(root_path, source_url=source_url)
    output_root = Path(output_dir) if output_dir else Path(root_path)
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / MSN_FINAL_VALIDATION_REPORT_JSON
    md_path = output_root / MSN_FINAL_VALIDATION_REPORT_MD
    paths = {
        "final_validation_json": str(json_path),
        "final_validation_markdown": str(md_path),
    }
    report_with_paths = MsnFinalValidationReport(
        root_path=report.root_path,
        source_url=report.source_url,
        overall_status=report.overall_status,
        areas=report.areas,
        counts=report.counts,
        output_paths=paths,
        msn_republisher_note=report.msn_republisher_note,
        manual_review_required=report.manual_review_required,
        final_confidence_statement=report.final_confidence_statement,
    )
    json_path.write_text(json.dumps(report_with_paths.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_msn_adapter_final_validation_markdown(report_with_paths), encoding="utf-8")
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a completed MSN source adapter output folder.")
    parser.add_argument("root", help="MSN output/archive/export folder to validate")
    parser.add_argument("--source-url", default="", help="Original MSN source URL, if not already recorded in the folder")
    parser.add_argument("--output-dir", default="", help="Directory for MSN_ADAPTER_FINAL_VALIDATION_REPORT.*; defaults to root")
    parser.add_argument("--json", action="store_true", help="Print the final validation report JSON to stdout")
    args = parser.parse_args(list(argv) if argv is not None else None)
    paths = write_msn_adapter_final_validation_outputs(args.root, output_dir=args.output_dir or None, source_url=args.source_url)
    report = build_msn_adapter_final_validation_report(args.root, source_url=args.source_url)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"MSN final validation status: {report.overall_status}")
        print(f"JSON: {paths['final_validation_json']}")
        print(f"Markdown: {paths['final_validation_markdown']}")
    return 0 if report.overall_status != OVERALL_NOT_READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
