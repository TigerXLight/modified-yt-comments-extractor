"""Article extraction adapter for Profile/Media HOME.

V76L is the first implementation layer after the V76K2 HOME/source-criticism
rebase.  It can parse already supplied HTML through optional extractor
libraries inspired by the downloaded reference sources:

- metadata_parser for page/OpenGraph/schema metadata
- trafilatura for article body plus metadata
- newspaper4k for article text/title/byline/date fallback

The adapter is deliberately offline by default: it accepts HTML text or a local
HTML file supplied by the caller.  It never downloads pages, crawls websites,
copies media, classifies source roles as final, or infers sensitive identifiers.
When optional libraries are not installed, it falls back to a small stdlib HTML
extractor so tests and GUI plumbing remain deterministic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html import unescape
from html.parser import HTMLParser
import importlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urljoin, urlparse

from profile_media_database import utc_now_iso
from profile_media_source_criticism_model import (
    EVIDENCE_CORROBORATED_TEXT_CHAIN,
    EVIDENCE_IMAGE,
    build_evidence_marking,
    evaluate_structural_source_criticism,
)

PROFILE_MEDIA_ARTICLE_EXTRACTION_SCHEMA_VERSION = "profile-media-article-extraction-v76l"
WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW = "WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW"

DEFAULT_EXTRACTOR_ORDER = ("metadata_parser", "trafilatura", "newspaper4k", "stdlib_html")

ATTRIBUTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("court_or_legal_claim", r"\b(court|judge|jury|prosecutor|defence|defense|charged|convicted|sentenced|trial|inquest)\b"),
    ("police_or_authority_claim", r"\b(police|officers|detectives|psni|met police|spokesperson|authorities|officials)\b"),
    ("family_or_associate_claim", r"\b(family|relative|friend|neighbour|neighbor|mother|father|brother|sister)\b"),
    ("agency_or_publisher_chain", r"\b(according to|reported by|the statement said|press association|reuters|afp|ap news|agency)\b"),
    ("direct_quote_or_interview", r"\b(told|said|stated|wrote|posted|claimed|interviewed)\b"),
)


@dataclass(frozen=True)
class ArticleExtractionInput:
    html_text: str = ""
    source_url: str = ""
    local_path: str = ""
    reference_root: str = ""
    extractor_order: tuple[str, ...] = DEFAULT_EXTRACTOR_ORDER
    schema_version: str = PROFILE_MEDIA_ARTICLE_EXTRACTION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArticleExtractorRun:
    extractor_name: str
    status: str
    fields: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    external_tool_loaded: bool = False
    schema_version: str = PROFILE_MEDIA_ARTICLE_EXTRACTION_SCHEMA_VERSION
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    web_download_performed: bool = False
    crawling_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["fields"] = dict(self.fields)
        return payload


@dataclass(frozen=True)
class ArticleExtractionResult:
    status: str
    source_url: str = ""
    canonical_url: str = ""
    local_path: str = ""
    title: str = ""
    byline: str = ""
    published_date: str = ""
    site_name: str = ""
    description: str = ""
    main_text: str = ""
    outbound_links: tuple[str, ...] = ()
    image_urls: tuple[str, ...] = ()
    attribution_markings: tuple[str, ...] = ()
    source_basis_candidates: tuple[str, ...] = ()
    source_role_candidate: str = "REVIEW_REQUIRED"
    source_role_is_final: bool = False
    review_lanes: tuple[str, ...] = ()
    extractor_runs: tuple[ArticleExtractorRun, ...] = ()
    source_preview: Mapping[str, Any] = field(default_factory=dict)
    source_criticism_decision: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_ARTICLE_EXTRACTION_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    web_download_performed: bool = False
    crawling_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["outbound_links"] = list(self.outbound_links)
        payload["image_urls"] = list(self.image_urls)
        payload["attribution_markings"] = list(self.attribution_markings)
        payload["source_basis_candidates"] = list(self.source_basis_candidates)
        payload["review_lanes"] = list(self.review_lanes)
        payload["extractor_runs"] = [run.to_dict() for run in self.extractor_runs]
        payload["source_preview"] = dict(self.source_preview)
        payload["source_criticism_decision"] = dict(self.source_criticism_decision)
        payload["warnings"] = list(self.warnings)
        return payload


class _StdlibArticleHTMLParser(HTMLParser):
    def __init__(self, base_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self.images: list[str] = []
        self.meta: dict[str, str] = {}
        self.canonical_url = ""
        self._current_tag = ""
        self._capture_text_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {str(k).lower(): str(v or "") for k, v in attrs}
        self._current_tag = tag
        if tag == "title":
            self._capture_text_stack.append("title")
        elif tag == "h1":
            self._capture_text_stack.append("h1")
        elif tag in {"p", "blockquote", "li"}:
            self._capture_text_stack.append("text")
        elif tag == "meta":
            key = attrs_map.get("property") or attrs_map.get("name") or attrs_map.get("itemprop")
            content = attrs_map.get("content", "")
            if key and content:
                self.meta[key.lower()] = unescape(content.strip())
        elif tag == "link":
            rel = attrs_map.get("rel", "").lower()
            href = attrs_map.get("href", "")
            if "canonical" in rel and href:
                self.canonical_url = urljoin(self.base_url, href)
        elif tag == "a":
            href = attrs_map.get("href", "")
            if href:
                self.links.append(urljoin(self.base_url, href))
        elif tag == "img":
            src = attrs_map.get("src", "") or attrs_map.get("data-src", "")
            if src:
                self.images.append(urljoin(self.base_url, src))
            alt = attrs_map.get("alt", "")
            if alt:
                self.meta.setdefault("image_alt_text", alt)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"title", "h1", "p", "blockquote", "li"} and self._capture_text_stack:
            self._capture_text_stack.pop()
        self._current_tag = ""

    def handle_data(self, data: str) -> None:
        text = " ".join(str(data or "").split())
        if not text:
            return
        if not self._capture_text_stack:
            return
        bucket = self._capture_text_stack[-1]
        if bucket == "title":
            self.title_parts.append(text)
        elif bucket == "h1":
            self.h1_parts.append(text)
        else:
            self.text_parts.append(text)

    def fields(self) -> dict[str, Any]:
        title = _first_nonempty(
            self.meta.get("og:title", ""),
            self.meta.get("twitter:title", ""),
            self.meta.get("title", ""),
            " ".join(self.h1_parts),
            " ".join(self.title_parts),
        )
        return {
            "title": title,
            "canonical_url": self.canonical_url or self.meta.get("og:url", ""),
            "site_name": self.meta.get("og:site_name", "") or self.meta.get("application-name", ""),
            "description": self.meta.get("og:description", "") or self.meta.get("description", "") or self.meta.get("twitter:description", ""),
            "byline": self.meta.get("author", "") or self.meta.get("article:author", "") or self.meta.get("citation_author", ""),
            "published_date": self.meta.get("article:published_time", "") or self.meta.get("pubdate", "") or self.meta.get("date", "") or self.meta.get("dc.date", ""),
            "main_text": "\n\n".join(self.text_parts),
            "outbound_links": tuple(_dedupe(self.links)),
            "image_urls": tuple(_dedupe([*self.images, self.meta.get("og:image", ""), self.meta.get("twitter:image", "")]))
        }


def _coerce_order(order: Sequence[str] | None) -> tuple[str, ...]:
    requested = tuple(str(item).strip() for item in (order or DEFAULT_EXTRACTOR_ORDER) if str(item).strip())
    return requested or DEFAULT_EXTRACTOR_ORDER


def _dedupe(values: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _first_nonempty(*values: object) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _merge_unique_tuple(*sequences: Iterable[object]) -> tuple[str, ...]:
    items: list[str] = []
    for sequence in sequences:
        items.extend(_dedupe(sequence))
    return tuple(_dedupe(items))


def _clip_text(text: object, *, limit: int = 120000) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    return value[:limit]


def _prepare_reference_import_paths(reference_root: object) -> tuple[str, ...]:
    """Temporarily add downloaded reference repo roots to sys.path.

    The user's reference folder is not vendored or committed.  This helper only
    gives optional local libraries a chance to import if their dependencies are
    also present.  It is not a crawler and does not read the filesystem tree as
    database content.
    """

    root_text = str(reference_root or "").strip()
    if not root_text:
        return ()
    root = Path(os.path.expandvars(root_text)).expanduser()
    candidates = (
        root / "metadata_parser" / "src",
        root / "trafilatura",
        root / "newspaper4k",
    )
    added: list[str] = []
    for candidate in candidates:
        text = str(candidate)
        if candidate.exists() and text not in sys.path:
            sys.path.insert(0, text)
            added.append(text)
    return tuple(added)


def _safe_import(module_name: str) -> tuple[Any | None, str]:
    try:
        return importlib.import_module(module_name), ""
    except Exception as exc:  # pragma: no cover - depends on optional environment
        return None, f"{module_name}_unavailable:{type(exc).__name__}:{exc}"


def _run_stdlib_html(html_text: str, source_url: str) -> ArticleExtractorRun:
    parser = _StdlibArticleHTMLParser(source_url)
    try:
        parser.feed(_clip_text(html_text))
        return ArticleExtractorRun(
            extractor_name="stdlib_html",
            status="success",
            fields=parser.fields(),
            external_tool_loaded=False,
        )
    except Exception as exc:
        return ArticleExtractorRun(
            extractor_name="stdlib_html",
            status="failed",
            fields={},
            warnings=(f"stdlib_html_failed:{type(exc).__name__}:{exc}",),
            external_tool_loaded=False,
        )


def _run_metadata_parser(html_text: str, source_url: str, reference_root: str = "") -> ArticleExtractorRun:
    _prepare_reference_import_paths(reference_root)
    module, warning = _safe_import("metadata_parser")
    if module is None:
        return ArticleExtractorRun("metadata_parser", "skipped_unavailable", warnings=(warning,), external_tool_loaded=False)
    try:
        parser = module.MetadataParser(url=source_url or None, html=html_text, defer_fetch=True, force_parse=True, require_public_netloc=False)
        fields: dict[str, Any] = {}
        for output_key, metadata_keys in {
            "title": ("title", "og:title", "twitter:title"),
            "description": ("description", "og:description", "twitter:description"),
            "byline": ("author", "article:author", "citation_author"),
            "published_date": ("article:published_time", "date", "pubdate", "dc.date"),
            "site_name": ("og:site_name", "application-name"),
        }.items():
            for key in metadata_keys:
                try:
                    value = parser.get_metadatas(key)
                except Exception:
                    value = None
                text = _coerce_metadata_parser_value(value)
                if text:
                    fields[output_key] = text
                    break
        try:
            fields["canonical_url"] = _coerce_metadata_parser_value(parser.get_metadatas("canonical")) or parser.get_metadata_link("canonical") or ""
        except Exception:
            fields["canonical_url"] = ""
        try:
            image = parser.get_metadata_link("image") or parser.get_metadata_link("og:image") or ""
        except Exception:
            image = ""
        if image:
            fields["image_urls"] = (image,)
        return ArticleExtractorRun("metadata_parser", "success", fields=fields, external_tool_loaded=True)
    except Exception as exc:  # pragma: no cover - optional dependency behavior
        return ArticleExtractorRun("metadata_parser", "failed", warnings=(f"metadata_parser_failed:{type(exc).__name__}:{exc}",), external_tool_loaded=True)


def _coerce_metadata_parser_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for candidate in value.values():
            text = _coerce_metadata_parser_value(candidate)
            if text:
                return text
        return ""
    if isinstance(value, (list, tuple)):
        for candidate in value:
            text = _coerce_metadata_parser_value(candidate)
            if text:
                return text
        return ""
    return str(value).strip()


def _run_trafilatura(html_text: str, source_url: str, reference_root: str = "") -> ArticleExtractorRun:
    _prepare_reference_import_paths(reference_root)
    module, warning = _safe_import("trafilatura")
    if module is None:
        return ArticleExtractorRun("trafilatura", "skipped_unavailable", warnings=(warning,), external_tool_loaded=False)
    try:
        fields: dict[str, Any] = {}
        json_text = module.extract(
            html_text,
            url=source_url or None,
            output_format="json",
            with_metadata=True,
            include_comments=False,
            include_links=True,
            include_images=True,
        )
        if json_text:
            try:
                payload = json.loads(json_text)
            except Exception:
                payload = {}
            fields.update({
                "title": payload.get("title", "") or "",
                "byline": payload.get("author", "") or "",
                "published_date": payload.get("date", "") or "",
                "canonical_url": payload.get("url", "") or "",
                "site_name": payload.get("sitename", "") or "",
                "main_text": payload.get("text", "") or "",
                "description": payload.get("description", "") or "",
            })
        else:
            text = module.extract(html_text, url=source_url or None, include_comments=False)
            fields["main_text"] = text or ""
        status = "success" if any(str(v or "").strip() for v in fields.values() if not isinstance(v, (tuple, list, dict))) else "empty"
        return ArticleExtractorRun("trafilatura", status, fields=fields, external_tool_loaded=True)
    except Exception as exc:  # pragma: no cover - optional dependency behavior
        return ArticleExtractorRun("trafilatura", "failed", warnings=(f"trafilatura_failed:{type(exc).__name__}:{exc}",), external_tool_loaded=True)


def _run_newspaper4k(html_text: str, source_url: str, reference_root: str = "") -> ArticleExtractorRun:
    _prepare_reference_import_paths(reference_root)
    module, warning = _safe_import("newspaper")
    if module is None:
        return ArticleExtractorRun("newspaper4k", "skipped_unavailable", warnings=(warning,), external_tool_loaded=False)
    try:
        url = source_url or "https://example.invalid/local-article"
        article = module.article(url, input_html=html_text, language="en")
        fields = {
            "title": getattr(article, "title", "") or "",
            "byline": ", ".join(getattr(article, "authors", ()) or ()),
            "published_date": str(getattr(article, "publish_date", "") or ""),
            "main_text": getattr(article, "text", "") or "",
            "top_image": getattr(article, "top_image", "") or "",
        }
        if fields.get("top_image"):
            fields["image_urls"] = (fields["top_image"],)
        status = "success" if any(str(v or "").strip() for v in fields.values() if not isinstance(v, (tuple, list, dict))) else "empty"
        return ArticleExtractorRun("newspaper4k", status, fields=fields, external_tool_loaded=True)
    except Exception as exc:  # pragma: no cover - optional dependency behavior
        return ArticleExtractorRun("newspaper4k", "failed", warnings=(f"newspaper4k_failed:{type(exc).__name__}:{exc}",), external_tool_loaded=True)


def _run_named_extractor(name: str, html_text: str, source_url: str, reference_root: str) -> ArticleExtractorRun:
    key = str(name or "").strip().lower().replace("-", "_")
    if key == "metadata_parser":
        return _run_metadata_parser(html_text, source_url, reference_root)
    if key == "trafilatura":
        return _run_trafilatura(html_text, source_url, reference_root)
    if key in {"newspaper4k", "newspaper"}:
        return _run_newspaper4k(html_text, source_url, reference_root)
    if key in {"stdlib_html", "stdlib"}:
        return _run_stdlib_html(html_text, source_url)
    return ArticleExtractorRun(key or "unknown", "skipped_unknown_extractor", warnings=("unknown_extractor",), external_tool_loaded=False)


def _field_from_runs(runs: Sequence[ArticleExtractorRun], field_name: str) -> str:
    for run in runs:
        value = run.fields.get(field_name) if isinstance(run.fields, Mapping) else ""
        if isinstance(value, (tuple, list)):
            value = _first_nonempty(*value)
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _tuple_field_from_runs(runs: Sequence[ArticleExtractorRun], field_name: str) -> tuple[str, ...]:
    values: list[str] = []
    for run in runs:
        value = run.fields.get(field_name) if isinstance(run.fields, Mapping) else ""
        if isinstance(value, (tuple, list, set)):
            values.extend(str(item) for item in value)
        elif value:
            values.append(str(value))
    return tuple(_dedupe(values))


def _attribution_markings(text: str) -> tuple[str, ...]:
    haystack = str(text or "")[:25000].lower()
    markings: list[str] = []
    for name, pattern in ATTRIBUTION_PATTERNS:
        if re.search(pattern, haystack, flags=re.IGNORECASE):
            markings.append(name)
    return tuple(markings)


def _source_basis_candidates(markings: Sequence[str], *, byline: str, source_url: str, canonical_url: str) -> tuple[str, ...]:
    candidates: list[str] = []
    if byline:
        candidates.append("publisher_byline_present")
    if source_url or canonical_url:
        candidates.append("article_page_source_address_present")
    if "direct_quote_or_interview" in markings:
        candidates.append("contains_direct_quote_or_statement_language")
    if any(mark in markings for mark in ("court_or_legal_claim", "police_or_authority_claim", "family_or_associate_claim", "agency_or_publisher_chain")):
        candidates.append("contains_propagated_or_authority_claim_language")
    if not candidates:
        candidates.append("article_text_extracted_no_clear_source_basis")
    return tuple(candidates)


def _review_lanes(markings: Sequence[str], image_urls: Sequence[str], source_basis_candidates: Sequence[str]) -> tuple[str, ...]:
    lanes: list[str] = []
    if "contains_propagated_or_authority_claim_language" in source_basis_candidates:
        lanes.append("source_chain_basis_review")
    if image_urls:
        lanes.append("claim_subject_affiliation_review")
    if "article_text_extracted_no_clear_source_basis" in source_basis_candidates:
        lanes.append("missing_source_basis_marking")
    if not lanes:
        lanes.append("source_role_review")
    return tuple(_dedupe(lanes))


def build_article_source_preview(result: ArticleExtractionResult) -> dict[str, Any]:
    return {
        "schema_version": PROFILE_MEDIA_ARTICLE_EXTRACTION_SCHEMA_VERSION,
        "source_title": result.title or "Untitled article",
        "source_bucket": "Articles",
        "source_page": result.source_url or result.canonical_url or result.local_path,
        "canonical_url": result.canonical_url,
        "publisher_or_site": result.site_name,
        "byline": result.byline,
        "published_date": result.published_date,
        "description": result.description,
        "source_role": "UNKNOWN_SOURCE_ROLE",
        "source_role_candidate": result.source_role_candidate,
        "source_role_is_final": False,
        "claim_basis": "ARTICLE_EXTRACTION_STRUCTURAL_FIELDS_ONLY",
        "source_basis_candidates": list(result.source_basis_candidates),
        "attribution_markings": list(result.attribution_markings),
        "review_lanes": list(result.review_lanes),
        "source_chain_gap": "contains_propagated_or_authority_claim_language" in result.source_basis_candidates,
        "claim_subject_affiliation_gap": "claim_subject_affiliation_review" in result.review_lanes,
        "confidence_or_verification_notes": "Article extraction gathered structural metadata/text only; source role remains a review decision.",
        "folder_scan_performed": False,
        "media_download_performed": False,
        "web_download_performed": False,
        "crawling_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
    }


def _build_source_criticism_payload(result_without_source: Mapping[str, Any]) -> dict[str, Any]:
    markings = [
        build_evidence_marking(
            EVIDENCE_CORROBORATED_TEXT_CHAIN,
            description="Extracted article text and metadata fields from supplied HTML.",
            source_address=str(result_without_source.get("source_url") or result_without_source.get("canonical_url") or result_without_source.get("local_path") or ""),
            sustainable_marking="title/byline/date/canonical/text/outbound-links captured where present",
            bias_notes="Extractor output is structural only; original source chain and publisher bias require review.",
            directly_affiliated_with_claim=None,
            affiliation_note="Text extraction does not prove claim-subject affiliation.",
        )
    ]
    if result_without_source.get("image_urls"):
        markings.append(
            build_evidence_marking(
                EVIDENCE_IMAGE,
                description="Image URL or inline image detected in article metadata/body.",
                source_address=str(result_without_source.get("image_urls", ())[0]),
                sustainable_marking="image URL recorded, not downloaded",
                bias_notes="Visible/person affiliation with evaluated claim must be checked before using this as support.",
                directly_affiliated_with_claim=None,
                affiliation_note="Image affiliation not established by extraction alone.",
            )
        )
    payload = evaluate_structural_source_criticism(markings).to_dict()
    payload["source_role_candidate"] = "REVIEW_REQUIRED"
    payload["source_role_is_final"] = False
    notes = list(payload.get("structural_notes") or [])
    notes.append("Article extraction never upgrades evidence markings into a final or candidate source role without user/source-chain review.")
    payload["structural_notes"] = notes
    return payload


def extract_article_from_html(
    html_text: object,
    *,
    source_url: object = "",
    local_path: object = "",
    reference_root: object = "",
    extractor_order: Sequence[str] | None = None,
) -> ArticleExtractionResult:
    html = str(html_text or "")
    order = _coerce_order(extractor_order)
    url = str(source_url or "")
    path = str(local_path or "")
    warnings: list[str] = []
    if not html.strip():
        warnings.append("empty_html_text")
    runs = tuple(_run_named_extractor(name, html, url, str(reference_root or "")) for name in order)
    if not any(run.status == "success" for run in runs):
        warnings.append("no_extractor_success")
    for run in runs:
        warnings.extend(run.warnings)

    main_text = _field_from_runs(runs, "main_text")
    title = _field_from_runs(runs, "title")
    byline = _field_from_runs(runs, "byline")
    published_date = _field_from_runs(runs, "published_date")
    canonical_url = _field_from_runs(runs, "canonical_url")
    site_name = _field_from_runs(runs, "site_name")
    description = _field_from_runs(runs, "description")
    outbound_links = _tuple_field_from_runs(runs, "outbound_links")
    image_urls = _tuple_field_from_runs(runs, "image_urls")

    markings = _attribution_markings("\n".join([title, description, main_text]))
    basis = _source_basis_candidates(markings, byline=byline, source_url=url, canonical_url=canonical_url)
    lanes = _review_lanes(markings, image_urls, basis)
    temporary_payload = {
        "source_url": url,
        "canonical_url": canonical_url,
        "local_path": path,
        "image_urls": image_urls,
    }
    criticism_payload = _build_source_criticism_payload(temporary_payload)

    provisional = ArticleExtractionResult(
        status="success" if title or main_text or description else "needs_review_empty_extraction",
        source_url=url,
        canonical_url=canonical_url,
        local_path=path,
        title=title,
        byline=byline,
        published_date=published_date,
        site_name=site_name,
        description=description,
        main_text=main_text,
        outbound_links=outbound_links,
        image_urls=image_urls,
        attribution_markings=markings,
        source_basis_candidates=basis,
        source_role_candidate=str(criticism_payload.get("source_role_candidate") or "REVIEW_REQUIRED"),
        source_role_is_final=False,
        review_lanes=lanes,
        extractor_runs=runs,
        source_criticism_decision=criticism_payload,
        warnings=tuple(_dedupe(warnings)),
    )
    return ArticleExtractionResult(
        **{k: v for k, v in provisional.to_dict().items() if k not in {"source_preview", "extractor_runs", "outbound_links", "image_urls", "attribution_markings", "source_basis_candidates", "review_lanes", "warnings", "source_criticism_decision", "created_at_utc"}},
        outbound_links=provisional.outbound_links,
        image_urls=provisional.image_urls,
        attribution_markings=provisional.attribution_markings,
        source_basis_candidates=provisional.source_basis_candidates,
        review_lanes=provisional.review_lanes,
        extractor_runs=provisional.extractor_runs,
        source_preview=build_article_source_preview(provisional),
        source_criticism_decision=provisional.source_criticism_decision,
        warnings=provisional.warnings,
    )


def read_html_file(path: object, *, encoding: str = "utf-8") -> str:
    file_path = Path(os.path.expandvars(str(path or ""))).expanduser()
    return file_path.read_text(encoding=encoding, errors="replace")


def extract_article_from_file(
    html_file: object,
    *,
    source_url: object = "",
    reference_root: object = "",
    extractor_order: Sequence[str] | None = None,
) -> ArticleExtractionResult:
    path = str(html_file or "")
    return extract_article_from_html(
        read_html_file(path),
        source_url=source_url,
        local_path=path,
        reference_root=reference_root,
        extractor_order=extractor_order,
    )


def write_article_source_preview(result: ArticleExtractionResult, output_json: object, *, confirmation: object = "") -> dict[str, Any]:
    path = Path(os.path.expandvars(str(output_json or ""))).expanduser()
    confirmed = str(confirmation or "") == WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW
    payload = {
        "schema_version": PROFILE_MEDIA_ARTICLE_EXTRACTION_SCHEMA_VERSION,
        "status": "blocked_confirmation_required",
        "confirmation_required": WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW,
        "output_json": str(path),
        "file_write_performed": False,
        "folder_scan_performed": False,
        "folder_creation_performed": False,
        "folder_move_performed": False,
        "folder_rename_performed": False,
        "file_copy_performed": False,
        "media_download_performed": False,
        "web_download_performed": False,
        "crawling_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
        "warning_count": 0,
        "warnings": [],
    }
    if not confirmed:
        payload["warnings"] = ["write_blocked_confirmation_required"]
        payload["warning_count"] = 1
        return payload
    if not str(path):
        payload["status"] = "blocked_missing_output_path"
        payload["warnings"] = ["missing_output_json"]
        payload["warning_count"] = 1
        return payload
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.source_preview, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["status"] = "source_preview_written"
    payload["file_write_performed"] = True
    return payload


def render_article_extraction_text(result: ArticleExtractionResult) -> str:
    lines = [
        "Profile/Media Article Extraction Adapter",
        f"Status: {result.status}",
        f"Title: {result.title or '(missing)'}",
        f"Publisher/site: {result.site_name or '(missing)'}",
        f"Byline: {result.byline or '(missing)'}",
        f"Published date: {result.published_date or '(missing)'}",
        f"Source URL: {result.source_url or '(none)'}",
        f"Canonical URL: {result.canonical_url or '(missing)'}",
        f"Main text chars: {len(result.main_text)}",
        f"Outbound links: {len(result.outbound_links)}",
        f"Image URLs recorded, not downloaded: {len(result.image_urls)}",
        "",
        "Extractor runs:",
    ]
    for run in result.extractor_runs:
        loaded = "loaded" if run.external_tool_loaded else "not loaded"
        lines.append(f"- {run.extractor_name}: {run.status} ({loaded})")
    lines.extend([
        "",
        "Attribution/source-basis markings:",
    ])
    for item in result.attribution_markings or ("none",):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Source basis candidates:")
    for item in result.source_basis_candidates:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Review lanes:")
    for item in result.review_lanes:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Source role:",
        f"- Candidate: {result.source_role_candidate}",
        f"- Final: {result.source_role_is_final}",
        "",
        "Safety:",
        f"- Folder scan performed: {result.folder_scan_performed}",
        f"- Web download performed: {result.web_download_performed}",
        f"- Crawling performed: {result.crawling_performed}",
        f"- Media download performed: {result.media_download_performed}",
        f"- Automatic classification performed: {result.automatic_classification_performed}",
        f"- Sensitive identifier inference performed: {result.sensitive_identifier_inference_performed}",
    ])
    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)
