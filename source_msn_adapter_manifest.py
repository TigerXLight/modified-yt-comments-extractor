from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from capture_media_discovery import (
    MEDIA_RESOURCE_KIND_BLOB,
    MEDIA_RESOURCE_KIND_IMAGE,
    MEDIA_RESOURCE_KIND_MANIFEST,
    MEDIA_RESOURCE_KIND_VIDEO,
    MediaResource,
    discover_media_resources_from_html,
    discover_media_resources_from_request_log,
)
from capture_media_download import MediaDownloadResult
from evidence_schema import (
    AccessMode,
    CaptureMethod,
    ClaimEvidenceNote,
    CurrentnessStatus,
    EvidenceProvenance,
    MediaSourceChainNote,
    PrimarySourceStatus,
    SourceRole,
    utc_now_iso,
)
from total_export_manifest import (
    ASSET_ARCHIVE_RESULT,
    ASSET_HTML_SNAPSHOT,
    ASSET_JSON_EXPORT,
    ASSET_MANIFEST,
    ASSET_MEDIA,
    ASSET_RAW_SIDECAR,
    ASSET_TEXT_EXPORT,
    ExportAsset,
    TotalExportManifest,
    manifest_filename,
    safe_package_id,
    sha256_for_file,
)


MSN_SOURCE_ADAPTER_SCHEMA_VERSION = "msn_source_adapter_bundle_v1"
MSN_SOURCE_ADAPTER_NAME = "msn_source_adapter"
MSN_SOURCE_PLATFORM = "MSN"
MSN_PUBLISHER_SECONDARY_NOTE = (
    "MSN page/publisher framing is preserved separately from the original authored source. "
    "Do not substitute MSN, a reposting outlet, an agency loop, an authority statement, or a family "
    "statement for the primary/original source unless the primary source is independently located."
)


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


def _clean_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()
    return text


def _host(url: str) -> str:
    return (urlsplit(str(url or "")).hostname or "").lower()


def _relative_asset_path(path: str | Path, *, package_root: str | Path | None = None, fallback_prefix: str = "metadata") -> str:
    candidate = Path(path)
    if package_root:
        try:
            return candidate.resolve().relative_to(Path(package_root).resolve()).as_posix()
        except (OSError, ValueError):
            pass
    return f"{fallback_prefix}/{candidate.name}"


def _read_text_if_file(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_file():
        return ""
    return candidate.read_text(encoding="utf-8", errors="replace")


def _asset_from_path(
    path: str | Path,
    *,
    asset_type: str,
    description: str,
    source_url: str,
    mime_type: str = "",
    package_root: str | Path | None = None,
) -> ExportAsset:
    candidate = Path(path)
    return ExportAsset(
        asset_type=asset_type,
        path=_relative_asset_path(candidate, package_root=package_root, fallback_prefix="metadata"),
        description=description,
        source_url=source_url,
        sha256=sha256_for_file(str(candidate)),
        mime_type=mime_type,
        size_bytes=candidate.stat().st_size if candidate.is_file() else 0,
    )


class _ArticleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.publisher = ""
        self.author = ""
        self.published_or_age = ""
        self.read_time = ""
        self.hero_image_url = ""
        self.hero_image_alt = ""
        self.visible_source_credit = ""
        self.article_lines: list[str] = []
        self.links: list[dict[str, str]] = []
        self._tag_stack: list[str] = []
        self._capture_text_for: str = ""
        self._current_link: dict[str, str] | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        self._tag_stack.append(lowered)
        attrs_map = {key.lower(): value or "" for key, value in attrs}
        if lowered == "meta":
            prop = attrs_map.get("property") or attrs_map.get("name")
            content = attrs_map.get("content", "")
            if prop in {"og:title", "twitter:title"} and not self.title:
                self.title = _clean_text(content)
            if prop in {"og:site_name", "application-name"} and not self.publisher:
                self.publisher = _clean_text(content)
            if prop in {"author", "article:author"} and not self.author:
                self.author = _clean_text(content)
            if prop in {"og:image", "twitter:image"} and not self.hero_image_url:
                self.hero_image_url = _clean_text(content)
        elif lowered in {"h1", "title"}:
            self._capture_text_for = lowered
        elif lowered == "img":
            src = attrs_map.get("src") or attrs_map.get("data-src") or ""
            alt = attrs_map.get("alt") or attrs_map.get("title") or ""
            if src and not self.hero_image_url:
                self.hero_image_url = src
                self.hero_image_alt = _clean_text(alt)
        elif lowered == "a":
            href = attrs_map.get("href", "")
            self._current_link = {"url": href, "text": ""}
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == self._capture_text_for:
            self._capture_text_for = ""
        if lowered == "a" and self._current_link is not None:
            self._current_link["text"] = _clean_text(" ".join(self._link_text))
            if self._current_link.get("url") or self._current_link.get("text"):
                self.links.append(self._current_link)
            self._current_link = None
            self._link_text = []
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        text = _clean_text(data)
        if not text:
            return
        if self._current_link is not None:
            self._link_text.append(text)
        if self._capture_text_for == "h1" and not self.title:
            self.title = text
        elif self._capture_text_for == "title" and not self.title:
            self.title = text
        if text in {"The Independent", "Associated Press", "Reuters", "PA Media"} and not self.publisher:
            self.publisher = text
        if text.startswith("Story by ") and not self.author:
            author = text.removeprefix("Story by ").split("•", 1)[0].strip()
            self.author = _clean_text(author)
        if " min read" in text and not self.read_time:
            self.read_time = text
        if "Google Street View" in text and not self.visible_source_credit:
            self.visible_source_credit = "Google Street View"
        if len(text) > 24 and not text.lower().startswith(("advert", "sponsored", "privacy ", "terms ")):
            self.article_lines.append(text)


@dataclass(frozen=True)
class MsnArticleExtraction:
    source_url: str
    canonical_url: str = ""
    title: str = ""
    publisher_name: str = ""
    author: str = ""
    published_or_age: str = ""
    read_time: str = ""
    hero_image_url: str = ""
    hero_image_alt: str = ""
    visible_source_credit: str = ""
    article_text: str = ""
    article_body_lines: tuple[str, ...] = ()
    extracted_links: tuple[Mapping[str, str], ...] = ()
    source_role: SourceRole = SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE
    primary_source_status: PrimarySourceStatus = PrimarySourceStatus.SECONDARY_FRAMING_ONLY
    source_chain_gap: bool = True
    verification_notes: str = MSN_PUBLISHER_SECONDARY_NOTE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnAdapterMediaRecord:
    resource: Mapping[str, Any]
    observed_on_url: str
    publisher_name: str = ""
    publisher_headline_or_caption: str = ""
    visible_source_credit: str = ""
    claimed_original_source: str = ""
    original_source_url: str = ""
    source_role: SourceRole = SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE
    primary_source_status: PrimarySourceStatus = PrimarySourceStatus.PRIMARY_SOURCE_NOT_LOCATED
    source_chain_gap: bool = True
    local_media_path: str = ""
    local_file_hash: str = ""
    download_status: str = ""
    verification_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnSourceAdapterBundle:
    source_url: str
    article: MsnArticleExtraction
    media_records: tuple[MsnAdapterMediaRecord, ...] = ()
    manifest: TotalExportManifest = field(default_factory=TotalExportManifest)
    schema_version: str = MSN_SOURCE_ADAPTER_SCHEMA_VERSION
    adapter_name: str = MSN_SOURCE_ADAPTER_NAME
    media_download_performed_by_tool: bool = False
    live_network_request_performed_by_tool: bool = False
    browser_automation_performed_by_tool: bool = False
    manual_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def extract_msn_article_from_html(html: str, *, source_url: str = "", canonical_url: str = "") -> MsnArticleExtraction:
    parser = _ArticleTextParser()
    try:
        parser.feed(html or "")
    except Exception:
        pass
    lines = tuple(dict.fromkeys(parser.article_lines))
    publisher = parser.publisher or ("MSN" if _host(source_url).endswith("msn.com") else "")
    role = SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE
    status = PrimarySourceStatus.SECONDARY_FRAMING_ONLY
    source_gap = True
    if publisher and publisher.upper() == "MSN":
        status = PrimarySourceStatus.PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED
    return MsnArticleExtraction(
        source_url=source_url,
        canonical_url=canonical_url or source_url,
        title=parser.title,
        publisher_name=publisher,
        author=parser.author,
        published_or_age=parser.published_or_age,
        read_time=parser.read_time,
        hero_image_url=parser.hero_image_url,
        hero_image_alt=parser.hero_image_alt,
        visible_source_credit=parser.visible_source_credit,
        article_text="\n".join(lines),
        article_body_lines=lines,
        extracted_links=tuple(link for link in parser.links if link.get("url") or link.get("text")),
        source_role=role,
        primary_source_status=status,
        source_chain_gap=source_gap,
        verification_notes=(
            f"{MSN_PUBLISHER_SECONDARY_NOTE} Publisher detected: {publisher or 'unknown'}."
        ),
    )


def extract_msn_article_from_html_path(path: str | Path, *, source_url: str = "", canonical_url: str = "") -> MsnArticleExtraction:
    return extract_msn_article_from_html(_read_text_if_file(path), source_url=source_url, canonical_url=canonical_url)


def _media_download_by_resource_id(
    media_download_results: Iterable[Mapping[str, Any] | MediaDownloadResult],
) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for result in media_download_results or ():
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        resource_id = str(data.get("resource_id") or data.get("selected_resource_id") or "")
        if resource_id:
            output[resource_id] = data
    return output


def _media_status_note(resource: MediaResource, download_data: Mapping[str, Any] | None) -> str:
    if download_data and download_data.get("output_path"):
        return "Media was explicitly selected and captured locally; preserve source-chain limits separately."
    if resource.kind in {MEDIA_RESOURCE_KIND_MANIFEST, MEDIA_RESOURCE_KIND_BLOB} or resource.requires_playback:
        return "Media is streamed/blob/manifest/playback-dependent; preserve URL/poster/metadata/status rather than claiming a full video file was captured."
    if resource.kind == MEDIA_RESOURCE_KIND_VIDEO:
        return "Direct video candidate discovered; download requires explicit operator selection and should not imply original-source status."
    if resource.kind == MEDIA_RESOURCE_KIND_IMAGE:
        return "Image candidate discovered; do not assume MSN or the republishing outlet is the original image source."
    return "Media candidate discovered; source-chain review is required."


def build_msn_media_records(
    *,
    article: MsnArticleExtraction,
    html: str = "",
    request_log_entries: Iterable[Mapping[str, Any]] = (),
    media_download_results: Iterable[Mapping[str, Any] | MediaDownloadResult] = (),
) -> tuple[MsnAdapterMediaRecord, ...]:
    discovered = list(discover_media_resources_from_html(html, source_url=article.source_url).resources)
    if request_log_entries:
        discovered.extend(discover_media_resources_from_request_log(request_log_entries, source_url=article.source_url).resources)
    seen: set[tuple[str, str]] = set()
    downloads = _media_download_by_resource_id(media_download_results)
    records: list[MsnAdapterMediaRecord] = []
    for resource in discovered:
        key = (resource.kind, resource.url)
        if key in seen:
            continue
        seen.add(key)
        download_data = downloads.get(resource.resource_id) or {}
        local_path = str(download_data.get("output_path") or "")
        local_hash = str(download_data.get("sha256") or "")
        source_role = SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE
        status = PrimarySourceStatus.PRIMARY_SOURCE_NOT_LOCATED
        if article.visible_source_credit and article.visible_source_credit.lower() in resource.display_name.lower():
            status = PrimarySourceStatus.PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED
        records.append(
            MsnAdapterMediaRecord(
                resource=resource.to_dict(),
                observed_on_url=article.source_url,
                publisher_name=article.publisher_name,
                publisher_headline_or_caption=article.title or resource.display_name,
                visible_source_credit=article.visible_source_credit,
                claimed_original_source=article.visible_source_credit,
                original_source_url="",
                source_role=source_role,
                primary_source_status=status,
                source_chain_gap=True,
                local_media_path=local_path,
                local_file_hash=local_hash,
                download_status=str(download_data.get("status") or ("not_selected" if resource.downloadable else "metadata_only")),
                verification_notes=_media_status_note(resource, download_data),
            )
        )
    return tuple(records)


def _article_provenance(article: MsnArticleExtraction, *, capture_session_id: str = "", rendered_html_path: str = "") -> EvidenceProvenance:
    return EvidenceProvenance(
        source_url=article.source_url,
        canonical_url=article.canonical_url,
        source_platform=MSN_SOURCE_PLATFORM,
        adapter_name=MSN_SOURCE_ADAPTER_NAME,
        access_mode=AccessMode.PUBLIC_ACCESS,
        capture_method=CaptureMethod.BROWSER,
        capture_purpose="MSN article extraction with source-role provenance",
        source_role=article.source_role,
        primary_source_status=article.primary_source_status,
        source_chain_gap=article.source_chain_gap,
        author_display_name=article.author,
        extracted_text_path=_relative_asset_path(rendered_html_path, fallback_prefix="page_capture") if rendered_html_path else "",
        capture_session_id=capture_session_id,
        verification_notes=article.verification_notes,
    )


def _comment_provenance(comment: Mapping[str, Any], *, source_url: str, capture_session_id: str = "") -> EvidenceProvenance:
    return EvidenceProvenance(
        source_url=source_url,
        canonical_url=source_url,
        source_platform=MSN_SOURCE_PLATFORM,
        adapter_name=MSN_SOURCE_ADAPTER_NAME,
        access_mode=AccessMode.PUBLIC_ACCESS,
        capture_method=CaptureMethod.BROWSER,
        capture_purpose="MSN user comment/profile extraction",
        source_role=SourceRole.PRIMARY_ORIGINAL_AUTHORED,
        primary_source_status=PrimarySourceStatus.PRIMARY_SOURCE_LOCATED,
        source_chain_gap=False,
        item_id=str(comment.get("human_id") or comment.get("source_comment_id") or ""),
        parent_id=str(comment.get("parent_human_id") or ""),
        author_display_name=str(comment.get("author") or ""),
        author_profile_id=str(comment.get("author_profile_cid") or ""),
        posted_at=str(comment.get("date") or ""),
        permalink=str(comment.get("permalink") or ""),
        capture_session_id=capture_session_id,
        verification_notes=(
            "MSN comment item is primary/original authored evidence only for that commenter's own visible statement/profile metadata; "
            "it must not be substituted as primary evidence for unrelated article/event claims."
        ),
    )


def _walk_comments(comments: Iterable[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
    for item in comments or ():
        yield item
        yield from _walk_comments(item.get("replies") or ())


def _media_provenance(record: MsnAdapterMediaRecord, *, capture_session_id: str = "") -> EvidenceProvenance:
    resource = record.resource
    return EvidenceProvenance(
        source_url=record.observed_on_url,
        canonical_url=record.observed_on_url,
        source_platform=MSN_SOURCE_PLATFORM,
        adapter_name=MSN_SOURCE_ADAPTER_NAME,
        access_mode=AccessMode.PUBLIC_ACCESS,
        capture_method=CaptureMethod.BROWSER,
        capture_purpose="MSN media discovery/download registration",
        source_role=record.source_role,
        primary_source_status=record.primary_source_status,
        source_chain_gap=record.source_chain_gap,
        item_id=str(resource.get("resource_id") or ""),
        media_url=str(resource.get("url") or ""),
        local_media_path=record.local_media_path,
        local_file_hash=record.local_file_hash,
        capture_session_id=capture_session_id,
        verification_notes=record.verification_notes,
    )


def _media_chain_note(record: MsnAdapterMediaRecord) -> MediaSourceChainNote:
    resource = record.resource
    return MediaSourceChainNote(
        media_observed_on_url=str(resource.get("url") or ""),
        publisher_page_url=record.observed_on_url,
        publisher_name=record.publisher_name,
        publisher_headline_or_caption=record.publisher_headline_or_caption,
        publisher_framing_summary=(
            "MSN may repost from a publisher such as The Independent; preserve MSN/page framing separately from original media/source status."
        ),
        visible_source_credit=record.visible_source_credit,
        claimed_original_source=record.claimed_original_source,
        original_source_url=record.original_source_url,
        media_hash=record.local_file_hash,
        notes_on_context_dispute=(
            "Do not assume the MSN page or republishing outlet is the original media source. "
            "Record gaps, visible credits, captions, and later corrections separately."
        ),
        confidence_or_verification_notes=record.verification_notes,
    )


def _article_claim_note(article: MsnArticleExtraction) -> ClaimEvidenceNote:
    return ClaimEvidenceNote(
        claim_text=article.title,
        claim_type="msn_article_publisher_claim",
        claim_source_role=article.source_role,
        source_role_scope="MSN/publisher page is evidence of its own published framing and the article text visible at capture time.",
        source_role_limitation=(
            "This does not make MSN/the republishing outlet the primary source for each incident fact, media file, authority statement, or witness claim."
        ),
        currentness_status=CurrentnessStatus.UNKNOWN,
        primary_source_status=article.primary_source_status,
        source_chain_gap=article.source_chain_gap,
        closed_loop_reporting_flag=False,
        verification_notes=article.verification_notes,
    )


def build_msn_source_adapter_bundle(
    *,
    source_url: str,
    rendered_html_path: str | Path = "",
    rendered_html: str = "",
    comments_export: Mapping[str, Any] | None = None,
    comments_export_files: Mapping[str, Any] | None = None,
    offline_archive_dir: str | Path = "",
    request_log_entries: Iterable[Mapping[str, Any]] = (),
    media_download_results: Iterable[Mapping[str, Any] | MediaDownloadResult] = (),
    package_id: str = "",
    capture_session_id: str = "",
) -> MsnSourceAdapterBundle:
    html = rendered_html or (_read_text_if_file(rendered_html_path) if rendered_html_path else "")
    article = extract_msn_article_from_html(html, source_url=source_url)
    media_records = build_msn_media_records(
        article=article,
        html=html,
        request_log_entries=request_log_entries,
        media_download_results=media_download_results,
    )
    safe_id = safe_package_id(package_id or "msn_source_adapter")
    archive_dir = Path(offline_archive_dir) if offline_archive_dir else None
    assets: list[ExportAsset] = []
    if rendered_html_path and Path(rendered_html_path).is_file():
        assets.append(
            _asset_from_path(
                rendered_html_path,
                asset_type=ASSET_HTML_SNAPSHOT,
                description="MSN best viewable rendered HTML article backup",
                source_url=source_url,
                mime_type="text/html; charset=utf-8",
                package_root=archive_dir,
            )
        )
    if archive_dir:
        for name, description in (
            ("rendered-page.warc.gz", "MSN partial ReplayWeb WARC.GZ archive"),
            ("archive.viewable-live-capture.wacz", "MSN strict WACZ artifact, experimental/possibly unsupported"),
            ("archive.replayweb-compatible.wacz", "MSN ReplayWeb-compatible WACZ candidate when present"),
            ("capture-manifest.json", "MSN live capture manifest"),
            ("validation.json", "MSN live capture validation metadata"),
            ("local_viewer/index.html", "MSN local offline viewer index"),
            ("local_viewer/open_local_viewer.cmd", "MSN local offline viewer launcher"),
        ):
            candidate = archive_dir / name
            if candidate.is_file():
                assets.append(
                    _asset_from_path(
                        candidate,
                        asset_type=ASSET_ARCHIVE_RESULT if candidate.suffix not in {".html", ".cmd"} else ASSET_RAW_SIDECAR,
                        description=description,
                        source_url=source_url,
                        mime_type="application/json" if candidate.suffix == ".json" else "",
                        package_root=archive_dir,
                    )
                )
    for key, path in (comments_export_files or {}).items():
        if isinstance(path, str) and path and Path(path).is_file():
            asset_type = ASSET_JSON_EXPORT if path.lower().endswith(".json") else ASSET_TEXT_EXPORT
            assets.append(
                _asset_from_path(
                    path,
                    asset_type=asset_type,
                    description=f"MSN comments/profile export file: {key}",
                    source_url=source_url,
                    package_root=Path(path).parent,
                )
            )
    for record in media_records:
        if record.local_media_path and Path(record.local_media_path).is_file():
            assets.append(
                _asset_from_path(
                    record.local_media_path,
                    asset_type=ASSET_MEDIA,
                    description="MSN explicitly selected local media asset",
                    source_url=str(record.resource.get("url") or source_url),
                    package_root=Path(record.local_media_path).parent,
                )
            )

    provenance_records = [_article_provenance(article, capture_session_id=capture_session_id, rendered_html_path=str(rendered_html_path or ""))]
    if comments_export:
        for item in _walk_comments(comments_export.get("comments") or ()):
            provenance_records.append(_comment_provenance(item, source_url=source_url, capture_session_id=capture_session_id))
    provenance_records.extend(_media_provenance(record, capture_session_id=capture_session_id) for record in media_records)
    claim_notes = [_article_claim_note(article)]
    media_chain_notes = [_media_chain_note(record) for record in media_records]
    manifest = TotalExportManifest(
        package_id=safe_id,
        source_urls=[source_url],
        capture_options=[
            "msn_article_extraction",
            "msn_comments_profile_extraction" if comments_export else "msn_comments_profile_not_supplied",
            "msn_offline_archive_viewer" if archive_dir else "msn_offline_archive_not_supplied",
            "msn_media_discovery",
            "msn_source_role_provenance",
            "manual_review_required",
        ],
        assets=assets + [
            ExportAsset(
                asset_type=ASSET_MANIFEST,
                path=f"metadata/{manifest_filename(safe_id)}",
                description="MSN source adapter Total Export manifest",
                source_url=source_url,
                mime_type="application/json",
            )
        ],
        provenance_records=provenance_records,
        claim_notes=claim_notes,
        media_source_chain_notes=media_chain_notes,
        notes=(
            "MSN source adapter bundle links article extraction, comments/profile exports, offline archive/viewer artifacts, "
            "media discovery/download registration, and source-role provenance. Manual review remains required."
        ),
        app_version=MSN_SOURCE_ADAPTER_SCHEMA_VERSION,
    )
    return MsnSourceAdapterBundle(
        source_url=source_url,
        article=article,
        media_records=media_records,
        manifest=manifest,
        media_download_performed_by_tool=any(bool(record.local_media_path) for record in media_records),
    )


def write_msn_source_adapter_bundle_json(bundle: MsnSourceAdapterBundle, output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)
