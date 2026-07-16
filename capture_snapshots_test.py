from urllib.request import urlopen

from capture_browser import BrowserPageSnapshot
from capture_contracts import (
    ARTIFACT_TYPE_ACCESSIBILITY_TREE,
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_DOM_SNAPSHOT,
    ARTIFACT_TYPE_FINAL_DOM,
    ARTIFACT_TYPE_MHTML,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_SCREENSHOT,
)
from capture_fixture_server import CaptureFixtureServer
from capture_snapshots import (
    build_page_evidence_snapshot,
    build_page_evidence_snapshot_from_browser,
    sha256_bytes,
    sha256_text,
)
from capture_status import CAPTURE_STATUS_SUCCESS


def test_page_evidence_snapshot_builds_artifacts_from_supplied_html() -> None:
    html = (
        "<html><head><title>Fixture</title></head><body>"
        "<article><h1>Fixture</h1><p>Article body.</p></article>"
        "</body></html>"
    )

    evidence = build_page_evidence_snapshot(
        session_id="session_1",
        source_url="http://127.0.0.1/article/static",
        html=html,
        screenshot_png=b"png",
        created_at_utc="2026-07-16T00:00:00Z",
    )

    assert evidence.article.text == "Fixture\n\nArticle body."
    assert [artifact.artifact_type for artifact in evidence.artifacts] == [
        ARTIFACT_TYPE_RAW_HTML,
        ARTIFACT_TYPE_FINAL_DOM,
        ARTIFACT_TYPE_MHTML,
        ARTIFACT_TYPE_DOM_SNAPSHOT,
        ARTIFACT_TYPE_ACCESSIBILITY_TREE,
        ARTIFACT_TYPE_ARTICLE_TEXT,
        ARTIFACT_TYPE_PAGE_OUTLINE,
        ARTIFACT_TYPE_SCREENSHOT,
    ]
    assert evidence.artifacts[0].sha256 == sha256_text(html)
    assert evidence.artifacts[2].metadata["placeholder"] is True
    assert evidence.artifacts[3].metadata["derivation"] == "text_from_supplied_dom"
    assert evidence.artifacts[-1].sha256 == sha256_bytes(b"png")
    assert evidence.artifacts[-1].size_bytes == 3
    assert evidence.artifacts[-1].fidelity == "FAITHFUL"
    assert evidence.artifacts[-1].metadata["screenshot_kind"] == "faithful"


def test_page_evidence_snapshot_from_browser_preserves_fake_browser_fields() -> None:
    snapshot = BrowserPageSnapshot(
        status=CAPTURE_STATUS_SUCCESS,
        url="http://127.0.0.1/article/static",
        final_url="http://127.0.0.1/article/static",
        title="Browser Fixture",
        html="<html><body><main><h1>Browser Fixture</h1><p>Body.</p></main></body></html>",
        text="Browser Fixture Body.",
        screenshot_png=b"fake-screenshot",
        status_code=200,
        engine="fake_playwright",
    )

    evidence = build_page_evidence_snapshot_from_browser(
        session_id="session_2",
        snapshot=snapshot,
        created_at_utc="2026-07-16T00:00:00Z",
    )

    assert evidence.source_url == snapshot.final_url
    assert evidence.outline.headings[0].text == "Browser Fixture"
    assert evidence.artifacts[1].metadata["title_hint"] == "Browser Fixture"
    assert "fetch(" not in repr(evidence.to_dict())
    assert "requests.get" not in repr(evidence.to_dict())


def test_page_evidence_snapshot_works_with_localhost_fixture_html() -> None:
    with CaptureFixtureServer() as server:
        source_url = server.url_for_fixture("article_static")
        with urlopen(source_url, timeout=5) as response:
            html = response.read().decode("utf-8")

    evidence = build_page_evidence_snapshot(
        session_id="session_3",
        source_url=source_url,
        html=html,
        created_at_utc="2026-07-16T00:00:00Z",
    )

    assert evidence.article.status == "extracted"
    assert "Alpha article paragraph" in evidence.article.text
    assert evidence.outline.title == "Static Fixture Article"
    assert [artifact.artifact_type for artifact in evidence.artifacts] == [
        ARTIFACT_TYPE_RAW_HTML,
        ARTIFACT_TYPE_FINAL_DOM,
        ARTIFACT_TYPE_MHTML,
        ARTIFACT_TYPE_DOM_SNAPSHOT,
        ARTIFACT_TYPE_ACCESSIBILITY_TREE,
        ARTIFACT_TYPE_ARTICLE_TEXT,
        ARTIFACT_TYPE_PAGE_OUTLINE,
    ]


def test_derived_screenshot_requires_and_records_transformations() -> None:
    html = "<html><body><article><h1>Fixture</h1><p>Article body.</p></article></body></html>"
    transformations = (
        {
            "type": "highlight_region",
            "selector": "article",
            "reason": "fixture evidence emphasis",
        },
    )

    evidence = build_page_evidence_snapshot(
        session_id="session_4",
        source_url="http://127.0.0.1/article/static",
        html=html,
        screenshot_png=b"derived-png",
        screenshot_kind="derived",
        screenshot_transformations=transformations,
        created_at_utc="2026-07-16T00:00:00Z",
    )

    screenshot = evidence.artifacts[-1]
    assert screenshot.artifact_type == ARTIFACT_TYPE_SCREENSHOT
    assert screenshot.fidelity == "DERIVED"
    assert screenshot.transformations == transformations
    assert screenshot.metadata["derived_label_visible"] is True
    assert screenshot.metadata["transformation_count"] == 1

    try:
        build_page_evidence_snapshot(
            session_id="session_5",
            source_url="http://127.0.0.1/article/static",
            html=html,
            screenshot_png=b"derived-png",
            screenshot_kind="derived",
        )
    except ValueError as exc:
        assert "requires at least one transformation" in str(exc)
    else:
        raise AssertionError("derived screenshots must require transformation metadata")


def run_self_test() -> None:
    test_page_evidence_snapshot_builds_artifacts_from_supplied_html()
    test_page_evidence_snapshot_from_browser_preserves_fake_browser_fields()
    test_page_evidence_snapshot_works_with_localhost_fixture_html()
    test_derived_screenshot_requires_and_records_transformations()


if __name__ == "__main__":
    run_self_test()
    print("Capture snapshots self-test passed.")
