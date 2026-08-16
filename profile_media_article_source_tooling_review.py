"""Offline decision matrix for article/source extraction references.

V76K2 restricts article tooling to extractors that gather structural metadata.
It explicitly excludes FEVER/AVeriTeC/MICE-style verdict/benchmark logic from
product classification.  Extraction tools can collect title/byline/date/text/
canonical URL/outbound links, but source role remains a structural source-
criticism decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PROFILE_MEDIA_ARTICLE_TOOLING_REVIEW_SCHEMA_VERSION = "profile-media-article-source-tooling-review-v76k2"


@dataclass(frozen=True)
class ArticleSourceToolCandidate:
    name: str
    repository: str
    pinned_commit: str
    role: str
    useful_for: tuple[str, ...]
    limits: tuple[str, ...]
    integration_position: str = "baseline_extractor"
    offline_default: bool = True
    schema_version: str = PROFILE_MEDIA_ARTICLE_TOOLING_REVIEW_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExcludedBenchmarkFramework:
    name: str
    reason: str
    schema_version: str = PROFILE_MEDIA_ARTICLE_TOOLING_REVIEW_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArticleSourceToolingReview:
    status: str
    candidates: tuple[ArticleSourceToolCandidate, ...]
    excluded_frameworks: tuple[ExcludedBenchmarkFramework, ...]
    recommended_integration_order: tuple[str, ...]
    source_role_decision_rule: str
    image_claim_affiliation_rule: str
    folder_scan_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    schema_version: str = PROFILE_MEDIA_ARTICLE_TOOLING_REVIEW_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["candidates"] = [item.to_dict() for item in self.candidates]
        payload["excluded_frameworks"] = [item.to_dict() for item in self.excluded_frameworks]
        return payload


def build_article_source_tooling_review() -> ArticleSourceToolingReview:
    candidates = (
        ArticleSourceToolCandidate(
            name="trafilatura",
            repository="adbar/trafilatura",
            pinned_commit="a397f890f75bd3f1df216915617839523010fae8",
            role="article body and metadata extractor",
            useful_for=("main text", "title", "author/byline where available", "date", "canonical/url metadata", "offline HTML parsing"),
            limits=("does not decide Primary/Secondary/Tertiary", "does not solve repeated-source-chain bias", "site layouts still need review"),
        ),
        ArticleSourceToolCandidate(
            name="newspaper4k",
            repository="AndyTheFactory/newspaper4k",
            pinned_commit="b53a81fc01ff54601faaeae68d6b4a6d2f18efcb",
            role="article text/title/byline/date fallback",
            useful_for=("headline", "authors", "publish date", "top image", "article body"),
            limits=("not a provenance classifier", "metadata can reflect publisher tags rather than original sourcing"),
        ),
        ArticleSourceToolCandidate(
            name="metadata_parser",
            repository="jvanasco/metadata_parser",
            pinned_commit="2330c059ff223e5d7182adcc750ceefa9ae475a3",
            role="OpenGraph/schema/canonical metadata extractor",
            useful_for=("canonical URL", "OpenGraph title/description", "publisher/site metadata", "image metadata"),
            limits=("does not extract full article evidence chain", "does not verify claim affiliation"),
        ),
    )
    excluded = (
        ExcludedBenchmarkFramework(
            name="FEVER",
            reason="Excluded as product logic because verdict/evidence benchmark labels do not model the user's structural source-chain criticism.",
        ),
        ExcludedBenchmarkFramework(
            name="AVeriTeC",
            reason="Excluded as product logic because quality-control booleans and web evidence tasks do not establish original-source chain, affiliation, or bias markings.",
        ),
        ExcludedBenchmarkFramework(
            name="MICE multimodal benchmark framing",
            reason="Excluded as product logic because image/text examples can miss whether the pictured person is affiliated with the claim; the app must mark affiliation explicitly.",
        ),
    )
    return ArticleSourceToolingReview(
        status="extractors_only_benchmark_verdict_logic_excluded",
        candidates=candidates,
        excluded_frameworks=excluded,
        recommended_integration_order=("metadata_parser", "trafilatura", "newspaper4k"),
        source_role_decision_rule=(
            "Article extractors gather structural fields only.  Primary/Secondary/Tertiary/Internal depends on direct authorship, "
            "witness observation, propagated report chain, or user-created/internal media; it is not auto-decided by the extractor."
        ),
        image_claim_affiliation_rule=(
            "When an image shows a person, the app must record whether that person is affiliated with the evaluated claim. "
            "If affiliation is absent, visual evidence is marked as an affiliation gap, not as support for the claim."
        ),
    )


def render_article_source_tooling_review_text(review: ArticleSourceToolingReview | None = None) -> str:
    review = review or build_article_source_tooling_review()
    lines = [
        "Profile/Media Article Source Tooling Review",
        f"Status: {review.status}",
        "",
        "Extractor order:",
    ]
    for item in review.recommended_integration_order:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Included extractors:")
    for candidate in review.candidates:
        lines.append(f"- {candidate.name}: {candidate.role}; repo={candidate.repository}; commit={candidate.pinned_commit}")
    lines.append("")
    lines.append("Excluded benchmark/verdict frameworks:")
    for item in review.excluded_frameworks:
        lines.append(f"- {item.name}: {item.reason}")
    lines.append("")
    lines.append("Source role rule:")
    lines.append(review.source_role_decision_rule)
    lines.append("")
    lines.append("Image/claim affiliation rule:")
    lines.append(review.image_claim_affiliation_rule)
    lines.append("")
    lines.append("Safety:")
    lines.append(f"- Folder scan performed: {review.folder_scan_performed}")
    lines.append(f"- Media download performed: {review.media_download_performed}")
    lines.append(f"- Automatic classification performed: {review.automatic_classification_performed}")
    lines.append(f"- Sensitive identifier inference performed: {review.sensitive_identifier_inference_performed}")
    return "\n".join(lines)
