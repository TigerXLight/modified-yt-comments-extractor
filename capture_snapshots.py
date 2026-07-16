from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from capture_article import ArticleExtractionResult, extract_article_text_from_html
from capture_browser import BrowserPageSnapshot
from capture_contracts import (
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_ACCESSIBILITY_TREE,
    ARTIFACT_TYPE_DOM_SNAPSHOT,
    ARTIFACT_TYPE_FINAL_DOM,
    ARTIFACT_TYPE_MHTML,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_SCREENSHOT,
    CaptureArtifact,
    build_capture_artifact,
)
from capture_page_outline import PageOutlineResult, build_page_outline_from_html
from capture_status import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL_UNKNOWN,
    FIDELITY_DERIVED,
    FIDELITY_FAITHFUL,
    FIDELITY_RAW,
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


def _stable_json_digest(value: Any) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _metadata_placeholder_digest(*parts: object) -> str:
    return sha256_text("::".join(str(part or "") for part in parts))


def _snapshot_text_from_outline(outline: PageOutlineResult) -> str:
    return "\n".join(outline.outline_lines) or outline.text_sample


def build_page_evidence_snapshot(
    *,
    session_id: str,
    source_url: str,
    html: str,
    final_dom_html: str = "",
    dom_text: str = "",
    accessibility_text: str = "",
    screenshot_png: bytes = b"",
    screenshot_kind: str = "faithful",
    screenshot_transformations: tuple[dict[str, Any], ...] = (),
    created_at_utc: str = "",
    title_hint: str = "",
) -> PageEvidenceSnapshot:
    final_html = final_dom_html or html
    article = extract_article_text_from_html(final_html, source_url=source_url)
    outline = build_page_outline_from_html(final_html, source_url=source_url)
    dom_snapshot_text = dom_text or _snapshot_text_from_outline(outline)
    accessibility_snapshot_text = accessibility_text or _snapshot_text_from_outline(outline)
    artifacts: list[CaptureArtifact] = [
        build_capture_artifact(
            session_id=session_id,
            source_url=source_url,
            artifact_type=ARTIFACT_TYPE_RAW_HTML,
            capture_method="supplied_raw_html_snapshot",
            relative_path="page/raw.html",
            sha256=sha256_text(html),
            completeness=COMPLETENESS_COMPLETE,
            fidelity=FIDELITY_RAW,
            created_at_utc=created_at_utc,
            metadata={"source": "supplied_html", "derivation": "original_supplied_fixture_input"},
        ),
        build_capture_artifact(
            session_id=session_id,
            source_url=source_url,
            artifact_type=ARTIFACT_TYPE_FINAL_DOM,
            capture_method="supplied_html_snapshot",
            relative_path="page/final_dom.html",
            sha256=sha256_text(final_html),
            completeness=COMPLETENESS_COMPLETE,
            fidelity=FIDELITY_RAW,
            created_at_utc=created_at_utc,
            metadata={
                "derivation": "supplied_final_dom" if final_dom_html else "raw_html_used_as_final_dom",
                "source": "supplied_html",
                "title_hint": title_hint,
            },
        ),
        build_capture_artifact(
            session_id=session_id,
            source_url=source_url,
            artifact_type=ARTIFACT_TYPE_MHTML,
            capture_method="mhtml_placeholder_metadata",
            relative_path="page/page.mhtml",
            sha256=_metadata_placeholder_digest(source_url, "mhtml_placeholder", html),
            completeness=COMPLETENESS_PARTIAL_UNKNOWN,
            fidelity=FIDELITY_RAW,
            created_at_utc=created_at_utc,
            warnings=("MHTML placeholder metadata only; no browser MHTML capture performed.",),
            metadata={"placeholder": True, "execution": "not captured"},
        ),
        build_capture_artifact(
            session_id=session_id,
            source_url=source_url,
            artifact_type=ARTIFACT_TYPE_DOM_SNAPSHOT,
            capture_method="supplied_html_dom_text_snapshot",
            relative_path="page/dom_snapshot.json",
            sha256=_stable_json_digest({"dom_text": dom_snapshot_text}),
            completeness=COMPLETENESS_COMPLETE if dom_snapshot_text else COMPLETENESS_PARTIAL_UNKNOWN,
            fidelity=FIDELITY_STRUCTURED_EXTRACTION,
            created_at_utc=created_at_utc,
            metadata={"derivation": "text_from_supplied_dom"},
        ),
        build_capture_artifact(
            session_id=session_id,
            source_url=source_url,
            artifact_type=ARTIFACT_TYPE_ACCESSIBILITY_TREE,
            capture_method="supplied_html_accessibility_text_snapshot",
            relative_path="page/accessibility_tree.json",
            sha256=_stable_json_digest({"accessibility_text": accessibility_snapshot_text}),
            completeness=COMPLETENESS_COMPLETE
            if accessibility_snapshot_text
            else COMPLETENESS_PARTIAL_UNKNOWN,
            fidelity=FIDELITY_STRUCTURED_EXTRACTION,
            created_at_utc=created_at_utc,
            metadata={"derivation": "accessibility_style_text_from_supplied_dom"},
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
        if screenshot_kind == "derived" and not screenshot_transformations:
            raise ValueError("Derived screenshot metadata requires at least one transformation")
        if screenshot_kind not in {"faithful", "derived"}:
            raise ValueError("screenshot_kind must be faithful or derived")
        screenshot_fidelity = FIDELITY_DERIVED if screenshot_kind == "derived" else FIDELITY_FAITHFUL
        screenshot_metadata = (
            {
                "fixture_or_supplied_local_input": True,
                "normal_user_appearance_claim": "faithful for supplied fixture/local input only",
                "screenshot_kind": "faithful",
            }
            if screenshot_kind == "faithful"
            else {
                "derived_label_visible": True,
                "fixture_or_supplied_local_input": True,
                "screenshot_kind": "derived",
                "transformation_count": len(screenshot_transformations),
            }
        )
        artifacts.append(
            build_capture_artifact(
                session_id=session_id,
                source_url=source_url,
                artifact_type=ARTIFACT_TYPE_SCREENSHOT,
                capture_method="supplied_browser_screenshot",
                relative_path="screenshots/page.png",
                sha256=sha256_bytes(screenshot_png),
                completeness=COMPLETENESS_COMPLETE,
                fidelity=screenshot_fidelity,
                created_at_utc=created_at_utc,
                size_bytes=len(screenshot_png),
                transformations=screenshot_transformations,
                metadata=screenshot_metadata,
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
