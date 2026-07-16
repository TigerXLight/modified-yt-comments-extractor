from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from capture_article import ArticleExtractionResult, extract_article_text_from_html
from capture_browser import BrowserPageSnapshot
from capture_contracts import (
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_FINAL_DOM,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    ARTIFACT_TYPE_SCREENSHOT,
    CaptureArtifact,
    build_capture_artifact,
)
from capture_page_outline import PageOutlineResult, build_page_outline_from_html
from capture_status import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL_UNKNOWN,
    FIDELITY_FAITHFUL,
    FIDELITY_STRUCTURED_EXTRACTION,
)


SNAPSHOT_SCOPE = (
    "local snapshot artifact builder only; consumes supplied browser/HTML data and does not "
    "fetch, run a browser, capture screenshots, download, archive, call providers, or use credentials"
)


@dataclass(frozen=True)
class PageEvidenceSnapshot:
    source_url: str
    article: ArticleExtractionResult
    outline: PageOutlineResult
    artifacts: tuple[CaptureArtifact, ...]
    warnings: tuple[str, ...] = ()
    scope: str = SNAPSHOT_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "article": self.article.to_dict(),
            "outline": self.outline.to_dict(),
            "scope": self.scope,
            "source_url": self.source_url,
            "warnings": list(self.warnings),
        }


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(bytes(value or b"")).hexdigest()


def build_page_evidence_snapshot(
    *,
    session_id: str,
    source_url: str,
    html: str,
    screenshot_png: bytes = b"",
    created_at_utc: str = "",
    title_hint: str = "",
) -> PageEvidenceSnapshot:
    article = extract_article_text_from_html(html, source_url=source_url)
    outline = build_page_outline_from_html(html, source_url=source_url)
    artifacts: list[CaptureArtifact] = [
        build_capture_artifact(
            session_id=session_id,
            source_url=source_url,
            artifact_type=ARTIFACT_TYPE_FINAL_DOM,
            capture_method="supplied_html_snapshot",
            relative_path="page/final_dom.html",
            sha256=sha256_text(html),
            completeness=COMPLETENESS_COMPLETE,
            fidelity=FIDELITY_FAITHFUL,
            created_at_utc=created_at_utc,
            metadata={"title_hint": title_hint},
        ),
        build_capture_artifact(
            session_id=session_id,
            source_url=source_url,
            artifact_type=ARTIFACT_TYPE_ARTICLE_TEXT,
            capture_method=article.method,
            relative_path="article/article.txt",
            sha256=sha256_text(article.text),
            completeness=COMPLETENESS_COMPLETE if article.text else COMPLETENESS_PARTIAL_UNKNOWN,
            fidelity=FIDELITY_STRUCTURED_EXTRACTION,
            created_at_utc=created_at_utc,
            warnings=article.warnings,
            metadata={"confidence": article.confidence, "status": article.status},
        ),
        build_capture_artifact(
            session_id=session_id,
            source_url=source_url,
            artifact_type=ARTIFACT_TYPE_PAGE_OUTLINE,
            capture_method="html_outline_parser",
            relative_path="page/outline.json",
            sha256=sha256_text(json.dumps(outline.to_dict(), sort_keys=True)),
            completeness=COMPLETENESS_COMPLETE,
            fidelity=FIDELITY_STRUCTURED_EXTRACTION,
            created_at_utc=created_at_utc,
            warnings=outline.warnings,
        ),
    ]
    if screenshot_png:
        artifacts.append(
            build_capture_artifact(
                session_id=session_id,
                source_url=source_url,
                artifact_type=ARTIFACT_TYPE_SCREENSHOT,
                capture_method="supplied_browser_screenshot",
                relative_path="screenshots/page.png",
                sha256=sha256_bytes(screenshot_png),
                completeness=COMPLETENESS_COMPLETE,
                fidelity=FIDELITY_FAITHFUL,
                created_at_utc=created_at_utc,
                size_bytes=len(screenshot_png),
            )
        )
    warnings = tuple(dict.fromkeys(article.warnings + outline.warnings))
    return PageEvidenceSnapshot(
        source_url=source_url,
        article=article,
        outline=outline,
        artifacts=tuple(artifacts),
        warnings=warnings,
    )


def build_page_evidence_snapshot_from_browser(
    *,
    session_id: str,
    snapshot: BrowserPageSnapshot,
    created_at_utc: str = "",
) -> PageEvidenceSnapshot:
    return build_page_evidence_snapshot(
        session_id=session_id,
        source_url=snapshot.final_url or snapshot.url,
        html=snapshot.html,
        screenshot_png=snapshot.screenshot_png,
        created_at_utc=created_at_utc,
        title_hint=snapshot.title,
    )
