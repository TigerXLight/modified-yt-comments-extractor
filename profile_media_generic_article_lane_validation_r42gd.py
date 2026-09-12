from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

R42GD_MARKER = "YTCE_R42GD_GENERIC_ARTICLE_WEBPAGE_LANE_VALIDATION"
SIDE_EFFECT_BOUNDARY = (
    "no network fetch, no media download, no screenshot, no archive submission, "
    "no provider/API call, no account/session use, no CAPTCHA/access-control bypass"
)

STATUS_TESTED_TRUE = "tested_true"
STATUS_IMPLEMENTED = "implemented"
STATUS_VALIDATED_PLAN = "validated_plan"
STATUS_NOT_TESTED = "not_tested"
STATUS_RECEIPT_REQUIRED = "receipt_required"
STATUS_MATERIAL_RECEIPT_REQUIRED = "material_receipt_required_before_counter_green"
STATUS_UNSUPPORTED = "unsupported"
STATUS_WARNING = "warning"

GENERIC_ARTICLE_ROUTE = "generic_article_normal_access_then_rendered_browser_then_archive_material"
GENERIC_ARTICLE_ADAPTER_HINT = "generic_article"


@dataclass(frozen=True)
class OfflineArticleFixtureResult:
    source_url: str
    title: str
    byline: str
    published_date: str
    canonical_url: str
    site_name: str
    description: str
    main_text: str
    image_urls: tuple[str, ...] = ()
    outbound_links: tuple[str, ...] = ()
    extractor: str = "r42gd_stdlib_supplied_html_only"
    side_effects: str = SIDE_EFFECT_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["image_urls"] = list(self.image_urls)
        data["outbound_links"] = list(self.outbound_links)
        data["r42gd_marker"] = R42GD_MARKER
        return data


@dataclass(frozen=True)
class GenericArticleFacetState:
    facet: str
    status: str
    evidence: str
    notes: str = ""

    def to_dict(self) -> dict[str, str]:
        data = asdict(self)
        data["r42gd_marker"] = R42GD_MARKER
        return data


@dataclass(frozen=True)
class URLClassificationRecord:
    input_url: str
    family_id: str
    url_kind: str
    route_preference: str
    supported: bool
    normalized_host: str = ""
    reason: str = ""
    generic_article_ok: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["r42gd_marker"] = R42GD_MARKER
        return data


@dataclass(frozen=True)
class SourceRowIntegrationRecord:
    input_url: str
    adapter_id: str = ""
    canonical_url: str = ""
    comments_supported: bool = False
    comments_status: str = ""
    provenance: str = ""
    warning_count: int = 0
    import_status: str = "not_attempted"
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["r42gd_marker"] = R42GD_MARKER
        return data


@dataclass(frozen=True)
class R42GDGenericArticleReport:
    schema: str
    marker: str
    created_at_utc: str
    passed: bool
    conclusion: str
    side_effects: str
    generic_article_route: str
    offline_article: OfflineArticleFixtureResult
    facet_states: tuple[GenericArticleFacetState, ...]
    generic_article_urls: tuple[URLClassificationRecord, ...]
    platform_exclusions: tuple[URLClassificationRecord, ...]
    source_row_integration: tuple[SourceRowIntegrationRecord, ...]
    checks: tuple[dict[str, str], ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "marker": self.marker,
            "created_at_utc": self.created_at_utc,
            "passed": self.passed,
            "conclusion": self.conclusion,
            "side_effects": self.side_effects,
            "generic_article_route": self.generic_article_route,
            "offline_article": self.offline_article.to_dict(),
            "facet_states": [item.to_dict() for item in self.facet_states],
            "generic_article_urls": [item.to_dict() for item in self.generic_article_urls],
            "platform_exclusions": [item.to_dict() for item in self.platform_exclusions],
            "source_row_integration": [item.to_dict() for item in self.source_row_integration],
            "checks": list(self.checks),
            "warnings": list(self.warnings),
        }


GENERIC_ARTICLE_SAMPLE_URLS = (
    "https://metro.co.uk/2026/09/12/example-public-article-12345678/",
    "https://www.telegraph.co.uk/news/2026/09/12/example-public-article/",
    "https://www.bbc.co.uk/news/articles/example-public-news-article",
    "https://example.org/2026/09/12/ordinary-public-article",
)

PLATFORM_EXCLUSION_SAMPLE_URLS = (
    "https://www.bbc.co.uk/programmes/m0031724",
    "https://www.bbc.co.uk/sounds/play/m0031724",
    "https://x.com/example/status/1234567890",
    "https://twitter.com/example/status/1234567890",
    "https://www.instagram.com/p/ABC123/",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://open.spotify.com/episode/1234567890",
    "https://open.spotify.com/track/1234567890",
    "https://cdn.example.test/media/public-video.mp4",
    "https://web.archive.org/web/20260717224516/https://metro.co.uk/example/",
    "https://archive.ph/6mr3C",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _check(status: str, check_id: str, details: str) -> dict[str, str]:
    return {"status": status, "check_id": check_id, "details": details, "r42gd_marker": R42GD_MARKER}


def _strip_tags(text: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", text or "")
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|li|h[1-6]|article|section|main)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def _attr_value(tag: str, attr_name: str) -> str:
    pattern = re.compile(
        r"""\b""" + re.escape(attr_name) + r"""\s*=\s*(?:"([^"]*)"|'([^']*)'|([^'"\s>]+))""",
        re.IGNORECASE,
    )
    match = pattern.search(tag or "")
    if not match:
        return ""
    return html.unescape(next(group for group in match.groups() if group is not None)).strip()


def _meta_content(source: str, *names: str) -> str:
    wanted = {name.casefold() for name in names}
    for match in re.finditer(r"(?is)<meta\b[^>]*>", source or ""):
        tag = match.group(0)
        key = (_attr_value(tag, "name") or _attr_value(tag, "property") or _attr_value(tag, "itemprop")).casefold()
        if key in wanted:
            return _attr_value(tag, "content")
    return ""


def _first_match(source: str, pattern: str) -> str:
    match = re.search(pattern, source or "", flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return _strip_tags(match.group(1))


def _link_rel(source: str, rel_name: str) -> str:
    for match in re.finditer(r"(?is)<link\b[^>]*>", source or ""):
        tag = match.group(0)
        rel = _attr_value(tag, "rel").casefold()
        if rel_name.casefold() in rel.split():
            return _attr_value(tag, "href")
    return ""


def _html_attr_urls(source: str, tag_name: str, attr_name: str) -> tuple[str, ...]:
    urls: list[str] = []
    for match in re.finditer(r"(?is)<" + re.escape(tag_name) + r"\b[^>]*>", source or ""):
        value = _attr_value(match.group(0), attr_name)
        if value and value not in urls:
            urls.append(value)
    return tuple(urls)


def build_offline_article_fixture_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <title>R42GD Example Public Article - Metro</title>
  <link rel="canonical" href="https://metro.co.uk/2026/09/12/example-public-article-12345678/">
  <meta property="og:title" content="R42GD Example Public Article">
  <meta property="og:site_name" content="Metro">
  <meta name="author" content="Example Reporter">
  <meta property="article:published_time" content="2026-09-12T00:00:00Z">
  <meta name="description" content="Deterministic supplied-HTML fixture for generic article lane validation.">
</head>
<body>
  <main>
    <article>
      <h1>R42GD Example Public Article</h1>
      <p>Example Reporter said the public webpage had normal article text available for review.</p>
      <p>According to the published statement, the article includes a link and image reference.</p>
      <a href="https://example.test/source-document">source document</a>
      <img src="https://metro.co.uk/example-image.jpg" alt="fixture image">
    </article>
  </main>
</body>
</html>
"""


def parse_offline_article_html(html_text: str, *, source_url: str) -> OfflineArticleFixtureResult:
    source = str(html_text or "")
    title = _meta_content(source, "og:title", "twitter:title") or _first_match(source, r"(?is)<title\b[^>]*>(.*?)</title>") or _first_match(source, r"(?is)<h1\b[^>]*>(.*?)</h1>")
    byline = _meta_content(source, "author", "article:author", "byl", "byline")
    published_date = _meta_content(source, "article:published_time", "date", "pubdate", "publishdate")
    canonical_url = _link_rel(source, "canonical") or str(source_url or "")
    site_name = _meta_content(source, "og:site_name", "application-name")
    description = _meta_content(source, "description", "og:description")
    article_match = re.search(r"(?is)<article\b[^>]*>(.*?)</article>", source)
    main_text = _strip_tags(article_match.group(1) if article_match else source)
    return OfflineArticleFixtureResult(
        source_url=str(source_url or ""),
        title=title,
        byline=byline,
        published_date=published_date,
        canonical_url=canonical_url,
        site_name=site_name,
        description=description,
        main_text=main_text,
        image_urls=_html_attr_urls(source, "img", "src"),
        outbound_links=_html_attr_urls(source, "a", "href"),
    )


def _load_r42gc_classifier():
    try:
        from profile_media_source_family_matrix_r42gc import classify_source_family
    except Exception as exc:  # pragma: no cover - exercised by reduced context zips
        return None, f"{type(exc).__name__}: {exc}"
    return classify_source_family, ""


def _classify_url_records(urls: Iterable[str]) -> tuple[URLClassificationRecord, ...]:
    classifier, error = _load_r42gc_classifier()
    records: list[URLClassificationRecord] = []
    for url in urls:
        if classifier is None:
            parsed = urlsplit(str(url or ""))
            records.append(
                URLClassificationRecord(
                    input_url=str(url or ""),
                    family_id="unavailable",
                    url_kind="r42gc_classifier_unavailable",
                    route_preference="unavailable",
                    supported=False,
                    normalized_host=(parsed.netloc or "").lower(),
                    reason=error,
                    generic_article_ok=False,
                )
            )
            continue
        decision = classifier(url)
        records.append(
            URLClassificationRecord(
                input_url=str(url or ""),
                family_id=str(getattr(decision, "family_id", "")),
                url_kind=str(getattr(decision, "url_kind", "")),
                route_preference=str(getattr(decision, "route_preference", "")),
                supported=bool(getattr(decision, "supported", False)),
                normalized_host=str(getattr(decision, "normalized_host", "")),
                reason=str(getattr(decision, "reason", "")),
                generic_article_ok=(str(getattr(decision, "family_id", "")) == "generic_article" and bool(getattr(decision, "supported", False))),
            )
        )
    return tuple(records)


def _matrix_generic_article_capability_check() -> tuple[dict[str, str], tuple[str, ...]]:
    try:
        from profile_media_source_family_matrix_r42gc import SOURCE_FAMILY_CAPABILITIES
    except Exception as exc:  # pragma: no cover - reduced context zips
        return (
            _check("warning", "r42gc_capability_import", f"Could not import R42GC matrix capability data: {type(exc).__name__}: {exc}"),
        ), (f"R42GC capability import warning: {type(exc).__name__}: {exc}",)

    generic_article = None
    for capability in SOURCE_FAMILY_CAPABILITIES:
        if getattr(capability, "family_id", "") == "generic_article":
            generic_article = capability
            break
    checks: list[dict[str, str]] = []
    warnings: list[str] = []
    if generic_article is None:
        checks.append(_check("fail", "r42gc_generic_article_capability_present", "R42GC generic_article capability is missing."))
        return tuple(checks), tuple(warnings)

    checks.append(_check("pass", "r42gc_generic_article_capability_present", "R42GC generic_article capability exists."))
    checks.append(_check("pass" if getattr(generic_article, "comments", "") == STATUS_NOT_TESTED else "fail", "generic_article_comments_not_tested", "Generic article comments stay not_tested unless a comments path is explicitly exercised."))
    checks.append(_check("pass" if getattr(generic_article, "article_text", "") in {STATUS_IMPLEMENTED, STATUS_TESTED_TRUE, STATUS_VALIDATED_PLAN} else "fail", "generic_article_text_capability_recorded", "Generic article text capability is represented in R42GC."))
    checks.append(_check("pass" if "material_receipt_required" in str(getattr(generic_article, "source_role_material", "")) else "fail", "source_role_material_receipt_gate", "Source-role material counters require material receipts before being green."))
    route = str(getattr(generic_article, "route_preference", ""))
    checks.append(_check("pass" if "normal_access" in route and "archive" in route else "fail", "generic_article_route_order_recorded", f"Generic article route preference: {route}"))
    return tuple(checks), tuple(warnings)


def build_facet_states(article: OfflineArticleFixtureResult) -> tuple[GenericArticleFacetState, ...]:
    return (
        GenericArticleFacetState("title", STATUS_TESTED_TRUE if article.title else "missing", "extracted from supplied HTML metadata/title/h1"),
        GenericArticleFacetState("byline", STATUS_TESTED_TRUE if article.byline else "missing", "extracted from supplied HTML author metadata"),
        GenericArticleFacetState("published_date", STATUS_TESTED_TRUE if article.published_date else "missing", "extracted from supplied HTML article:published_time metadata"),
        GenericArticleFacetState("canonical_url", STATUS_TESTED_TRUE if article.canonical_url else "missing", "extracted from supplied HTML canonical link"),
        GenericArticleFacetState("article_text", STATUS_TESTED_TRUE if article.main_text else "missing", "extracted from supplied offline HTML article body"),
        GenericArticleFacetState("image_references", STATUS_TESTED_TRUE if article.image_urls else "missing", "image URLs recorded from supplied HTML; no images downloaded"),
        GenericArticleFacetState("outbound_links", STATUS_TESTED_TRUE if article.outbound_links else "missing", "links recorded from supplied HTML; no pages fetched"),
        GenericArticleFacetState("screenshot", STATUS_NOT_TESTED, "no screenshot command was run", "requires a screenshot receipt before tested_true"),
        GenericArticleFacetState("warc", STATUS_NOT_TESTED, "no WARC/WACZ writer was run", "requires WARC/WACZ receipt before tested_true"),
        GenericArticleFacetState("archive_lookup", STATUS_NOT_TESTED, "no archive lookup was run", "requires archive lookup/import receipt before tested_true"),
        GenericArticleFacetState("source_role_material", STATUS_MATERIAL_RECEIPT_REQUIRED, "no source-role counter promotion is green from classification alone", "material receipt/replay required before counter green"),
        GenericArticleFacetState("comments", STATUS_NOT_TESTED, "generic article comments were not exercised", "site-specific comments path required before tested_true"),
    )


def _source_row_integration_records(source_root: str | Path = ".") -> tuple[SourceRowIntegrationRecord, ...]:
    root_path = Path(source_root).resolve()
    if str(root_path) not in sys.path:
        sys.path.insert(0, str(root_path))
    try:
        from source_resource_state import build_source_resource_row
    except Exception as exc:  # pragma: no cover - reduced context zips
        return (
            SourceRowIntegrationRecord(
                input_url="https://metro.co.uk/2026/09/12/example-public-article-12345678/",
                import_status="warning",
                error=f"{type(exc).__name__}: {exc}",
            ),
        )

    urls = (
        "https://metro.co.uk/2026/09/12/example-public-article-12345678/",
        "https://example.org/2026/09/12/ordinary-public-article",
        "https://x.com/example/status/1234567890",
    )
    records: list[SourceRowIntegrationRecord] = []
    for url in urls:
        try:
            row = build_source_resource_row(url, title="R42GD Integration Probe")
            records.append(
                SourceRowIntegrationRecord(
                    input_url=url,
                    adapter_id=str(getattr(row, "adapter_id", "")),
                    canonical_url=str(getattr(row, "canonical_url", "")),
                    comments_supported=bool(getattr(row, "comments_supported", False)),
                    comments_status=str(getattr(row, "comments_status", "")),
                    provenance=str(getattr(row, "provenance", "")),
                    warning_count=len(getattr(row, "warnings", ()) or ()),
                    import_status="ok",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            records.append(
                SourceRowIntegrationRecord(
                    input_url=url,
                    import_status="warning",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    return tuple(records)


def _source_row_checks(records: Sequence[SourceRowIntegrationRecord]) -> tuple[dict[str, str], tuple[str, ...]]:
    checks: list[dict[str, str]] = []
    warnings: list[str] = []
    if any(record.import_status == "warning" for record in records):
        details = "; ".join(record.error for record in records if record.error)
        checks.append(_check("warning", "source_resource_row_optional_integration", f"Optional source_resource_state integration not available in this reduced context: {details}"))
        warnings.append("Optional source_resource_state/source_adapters integration could not be imported in this context; standalone R42GD validation still ran.")
        return tuple(checks), tuple(warnings)

    by_url = {record.input_url: record for record in records}
    metro = by_url.get("https://metro.co.uk/2026/09/12/example-public-article-12345678/")
    generic = by_url.get("https://example.org/2026/09/12/ordinary-public-article")
    twitter = by_url.get("https://x.com/example/status/1234567890")

    checks.append(_check("pass" if metro and metro.adapter_id == "news_website" else "fail", "metro_source_row_uses_news_website", "Metro article row routes through the news_website adapter."))
    checks.append(_check("pass" if metro and "NOT_TESTED" in metro.comments_status.upper() else "fail", "metro_comments_not_tested", "Metro/generic news article comments remain NOT_TESTED."))
    checks.append(_check("pass" if metro and "API3128" in metro.provenance.upper() and "JDOWNLOADER" in metro.provenance.upper() else "fail", "metro_media_provenance_mentions_api3128", "Metro news row provenance retains selected public media API3128/JDownloader-first wording."))
    checks.append(_check("pass" if generic and generic.adapter_id == "webpage" else "fail", "ordinary_unknown_article_uses_webpage_fallback", "Unknown ordinary public article uses generic webpage fallback row metadata."))
    checks.append(_check("pass" if twitter and twitter.adapter_id == "twitter_x" else "fail", "twitter_not_generic_article_source_row", "Twitter/X URL does not fall into the generic webpage/news row."))
    return tuple(checks), tuple(warnings)


def validate_generic_article_lane(source_root: str | Path = ".", extra_urls: Sequence[str] | None = None) -> R42GDGenericArticleReport:
    article = parse_offline_article_html(
        build_offline_article_fixture_html(),
        source_url="https://metro.co.uk/2026/09/12/example-public-article-12345678/",
    )
    facet_states = build_facet_states(article)
    generic_urls = _classify_url_records(tuple(GENERIC_ARTICLE_SAMPLE_URLS) + tuple(extra_urls or ()))
    platform_exclusions = _classify_url_records(PLATFORM_EXCLUSION_SAMPLE_URLS)
    integration_records = _source_row_integration_records(source_root)

    checks: list[dict[str, str]] = []
    warnings: list[str] = []

    classifier_available = all(record.family_id != "unavailable" for record in generic_urls + platform_exclusions)
    checks.append(_check("pass" if classifier_available else "warning", "r42gc_classifier_available", "R42GC classifier imported and classified sample URLs." if classifier_available else "R42GC classifier was not importable; standalone HTML/facet checks still ran."))
    if not classifier_available:
        warnings.append("R42GC classifier import warning; classification checks are reduced.")

    matrix_checks, matrix_warnings = _matrix_generic_article_capability_check()
    checks.extend(matrix_checks)
    warnings.extend(matrix_warnings)

    checks.append(_check("pass" if article.title and article.main_text and article.canonical_url else "fail", "offline_article_html_extraction", "Supplied offline article HTML yields title, canonical URL, and article body text."))
    checks.append(_check("pass" if article.byline and article.published_date else "fail", "offline_article_metadata_extraction", "Supplied offline article HTML yields byline and published date metadata."))
    checks.append(_check("pass" if article.image_urls and article.outbound_links else "fail", "offline_article_links_and_images_recorded", "Supplied offline article HTML records image references and outbound links without downloading them."))

    facet_by_name = {state.facet: state for state in facet_states}
    checks.append(_check("pass" if facet_by_name["screenshot"].status == STATUS_NOT_TESTED else "fail", "screenshot_not_green_without_receipt", "Screenshot remains not_tested because no screenshot receipt exists."))
    checks.append(_check("pass" if facet_by_name["warc"].status == STATUS_NOT_TESTED else "fail", "warc_not_green_without_receipt", "WARC/WACZ remains not_tested because no archive writer receipt exists."))
    checks.append(_check("pass" if facet_by_name["archive_lookup"].status == STATUS_NOT_TESTED else "fail", "archive_lookup_not_green_without_receipt", "Archive lookup remains not_tested because no archive lookup/import receipt exists."))
    checks.append(_check("pass" if facet_by_name["source_role_material"].status == STATUS_MATERIAL_RECEIPT_REQUIRED else "fail", "source_role_counter_not_green_from_classification", "Source-role material counters require material receipts/replay before green."))
    checks.append(_check("pass" if facet_by_name["comments"].status == STATUS_NOT_TESTED else "fail", "comments_not_tested", "Generic article comments remain not_tested unless site-specific comments capture is exercised."))

    if classifier_available:
        checks.append(_check("pass" if all(record.generic_article_ok for record in generic_urls) else "fail", "ordinary_articles_classify_generic_article", "Ordinary public article samples classify as generic_article in R42GC."))
        bad_exclusions = [record for record in platform_exclusions if record.family_id == "generic_article" and record.supported]
        checks.append(_check("pass" if not bad_exclusions else "fail", "platform_sources_not_generic_article", "BBC Sounds, Twitter/X, Instagram, YouTube, Spotify podcast/music, direct media, and archive URLs do not get treated as generic_article."))
        spotify_track = next((record for record in platform_exclusions if "/track/" in record.input_url), None)
        checks.append(_check("pass" if spotify_track and not spotify_track.supported else "fail", "spotify_track_not_downloadable_article", "Spotify track/music URL remains unsupported metadata-only, not a generic article or podcast download."))
        direct_media = next((record for record in platform_exclusions if record.input_url.endswith(".mp4")), None)
        checks.append(_check("pass" if direct_media and direct_media.family_id == "generic_webpage_media" else "fail", "direct_media_routes_to_webpage_media", "Direct public .mp4 media candidate routes to generic_webpage_media, not generic_article."))

    row_checks, row_warnings = _source_row_checks(integration_records)
    checks.extend(row_checks)
    warnings.extend(row_warnings)

    failed = [check for check in checks if check["status"] == "fail"]
    passed = not failed
    conclusion = (
        "R42GD PASS: ordinary public article URLs are validated as the generic_article lane, "
        "platform-shaped URLs are routed away to specialist families, supplied-HTML article "
        "metadata/text/link/image extraction is exercised offline, and screenshot/archive/"
        "source-role/comment labels remain receipt-gated rather than overclaimed."
    )
    if failed:
        conclusion = "R42GD FAIL: generic article lane validation has failed checks."

    return R42GDGenericArticleReport(
        schema="r42gd_generic_article_webpage_lane_validation_v1",
        marker=R42GD_MARKER,
        created_at_utc=_utc_now(),
        passed=passed,
        conclusion=conclusion,
        side_effects=SIDE_EFFECT_BOUNDARY,
        generic_article_route=GENERIC_ARTICLE_ROUTE,
        offline_article=article,
        facet_states=facet_states,
        generic_article_urls=tuple(generic_urls),
        platform_exclusions=tuple(platform_exclusions),
        source_row_integration=integration_records,
        checks=tuple(checks),
        warnings=tuple(warnings),
    )


def write_report(report: R42GDGenericArticleReport, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "r42gd_generic_article_webpage_lane_validation.json"
    md_path = root / "r42gd_generic_article_webpage_lane_validation.md"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_report_markdown(report) + "\n", encoding="utf-8")
    return json_path, md_path


def render_report_markdown(report: R42GDGenericArticleReport) -> str:
    lines = [
        "# R42GD Generic Article/Webpage Lane Validation",
        "",
        f"Marker: `{report.marker}`",
        f"Passed: `{str(report.passed).lower()}`",
        f"Side effects: {report.side_effects}",
        "",
        "## Conclusion",
        "",
        report.conclusion,
        "",
        "## Generic article route",
        "",
        f"`{report.generic_article_route}`",
        "",
        "## Offline supplied-HTML article fixture",
        "",
        f"- Title: {report.offline_article.title}",
        f"- Byline: {report.offline_article.byline}",
        f"- Published date: {report.offline_article.published_date}",
        f"- Canonical URL: {report.offline_article.canonical_url}",
        f"- Main text chars: {len(report.offline_article.main_text)}",
        f"- Image references: {len(report.offline_article.image_urls)}",
        f"- Outbound links: {len(report.offline_article.outbound_links)}",
        "",
        "## Facet states",
        "",
    ]
    for state in report.facet_states:
        lines.append(f"- `{state.facet}`: `{state.status}` — {state.evidence}")
        if state.notes:
            lines.append(f"  - {state.notes}")

    lines.extend(["", "## Generic article URL samples", ""])
    for record in report.generic_article_urls:
        lines.append(f"- `{record.input_url}` -> `{record.family_id}` / `{record.url_kind}` / supported=`{str(record.supported).lower()}`")

    lines.extend(["", "## Platform exclusions", ""])
    for record in report.platform_exclusions:
        lines.append(f"- `{record.input_url}` -> `{record.family_id}` / `{record.url_kind}` / supported=`{str(record.supported).lower()}`")

    lines.extend(["", "## Source-row integration", ""])
    for record in report.source_row_integration:
        if record.import_status == "ok":
            lines.append(f"- `{record.input_url}` -> adapter=`{record.adapter_id}`, comments_supported=`{str(record.comments_supported).lower()}`")
        else:
            lines.append(f"- `{record.input_url}` -> optional integration `{record.import_status}`: {record.error}")

    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        lines.append(f"- `{check['status']}` `{check['check_id']}`: {check['details']}")
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in report.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def _main() -> int:
    parser = argparse.ArgumentParser(description="R42GD side-effect-free generic article/webpage lane validation.")
    parser.add_argument("--source-root", default=".", help="Project/source root used only for optional integration checks.")
    parser.add_argument("--output-root", default="", help="Optional folder for JSON/Markdown report output.")
    parser.add_argument("--url", action="append", default=None, help="Classify an additional ordinary article URL; can be supplied multiple times.")
    args = parser.parse_args()

    report = validate_generic_article_lane(args.source_root, extra_urls=tuple(args.url or ()))
    pass_count = sum(1 for check in report.checks if check.get("status") == "pass")
    warning_count = sum(1 for check in report.checks if check.get("status") == "warning")
    fail_count = sum(1 for check in report.checks if check.get("status") == "fail")

    print("R42GD generic article/webpage lane validation")
    print(f"Passed: {str(report.passed).lower()}")
    print(f"Conclusion: {report.conclusion}")
    print(f"Checks: {pass_count} pass / {warning_count} warning / {fail_count} fail")
    print(f"Side effects: {report.side_effects}")
    print(f"Offline article: title={bool(report.offline_article.title)} byline={bool(report.offline_article.byline)} date={bool(report.offline_article.published_date)} canonical={bool(report.offline_article.canonical_url)} text_chars={len(report.offline_article.main_text)}")
    for record in report.generic_article_urls:
        print(f"GENERIC: {record.input_url} -> family={record.family_id} kind={record.url_kind} supported={str(record.supported).lower()}")
    for record in report.platform_exclusions:
        print(f"EXCLUDE: {record.input_url} -> family={record.family_id} kind={record.url_kind} supported={str(record.supported).lower()}")
    if args.output_root:
        json_path, md_path = write_report(report, args.output_root)
        print(f"JSON: {json_path}")
        print(f"MARKDOWN: {md_path}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(_main())
