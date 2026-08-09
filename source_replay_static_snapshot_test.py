from __future__ import annotations

import gzip
import html
import tempfile
from pathlib import Path

from source_replay_static_snapshot import (
    STATIC_EVIDENCE_HTML_READY,
    STATIC_EVIDENCE_WARC_READY,
    REPLAYWEB_RUNTIME_PARTIAL_RENDER,
    STATIC_EVIDENCE_VIEW_READY,
    STATIC_EVIDENCE_WARNING,
    STATIC_PAGE_VIEW_HTML_READY,
    STATIC_PAGE_VIEW_READY,
    STATIC_PAGE_VIEW_WARNING,
    STATIC_PAGE_VIEW_WARC_READY,
    StaticReplayCommentItem,
    StaticReplayCommentsEvidence,
    StaticReplayEvidenceInput,
    StaticReplayEvidenceReference,
    StaticReplayPageViewInput,
    build_static_archived_page_view,
    build_static_evidence_url,
    build_static_page_view_url,
    build_static_page_view_warc,
    build_static_replay_evidence_page,
    build_static_replay_evidence_warc,
    validate_static_replay_evidence_html,
    validate_static_page_view_html,
    write_static_page_view_standalone_outputs,
    write_static_replay_standalone_outputs,
)


SOURCE_URL = "https://www.msn.com/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o?ocid=edgemobile&PC=EMMX01#comments"


def test_static_evidence_page_is_no_js_no_iframe_and_contains_required_sections() -> None:
    result = build_static_replay_evidence_page(
        StaticReplayEvidenceInput(
            source_url=SOURCE_URL,
            title="MSN evidence fallback",
            capture_timestamp="2026-08-09T00:00:00Z",
            original_wacz_sha256="a" * 64,
            normalized_wacz_sha256="b" * 64,
            warc_record_count=174,
            replay_runtime_status=REPLAYWEB_RUNTIME_PARTIAL_RENDER,
            replay_runtime_notes=(
                "Normalized WACZ article entry click: Archived Page Not Found.",
                "Normalized raw WARC opened partial runtime replay but MSN was slow and broken.",
            ),
            comments_evidence=StaticReplayCommentsEvidence(
                status="COMMENTS_EVIDENCE_VERIFIED",
                comments_json_count=25,
                declared_comment_count=25,
                top_level_comment_count=16,
                reply_count=9,
                comments_complete=True,
            ),
            captured_text_snippet="Fixture article snippet.",
            screenshot_references=(
                StaticReplayEvidenceReference(label="faithful screenshot", name="faithful.png", sha256="c" * 64),
            ),
            manifest_references=(
                StaticReplayEvidenceReference(label="manifest", name="manifest.json", sha256="d" * 64),
            ),
        )
    )

    assert result.status == STATIC_EVIDENCE_VIEW_READY
    assert result.errors == ()
    assert result.contains_script_tag is False
    assert result.contains_iframe_tag is False
    assert result.contains_remote_runtime_dependency is False
    assert "<script" not in result.html.lower()
    assert "<iframe" not in result.html.lower()
    assert STATIC_EVIDENCE_WARNING in result.html
    assert "Source URL" in result.html
    assert html.escape(SOURCE_URL, quote=True) in result.html
    assert "Original ReplayWeb runtime result" in result.html
    assert "Archived Page Not Found" in result.html
    assert "Evidence integrity" in result.html
    assert "Comments evidence" in result.html
    assert "COMMENTS_EVIDENCE_VERIFIED" in result.html
    assert "Fixture article snippet." in result.html


def test_static_evidence_url_uses_msn_article_slug() -> None:
    assert (
        build_static_evidence_url(SOURCE_URL, site_hint="msn")
        == "https://source-evidence.local/replay/msn/ar-AA29207o/static-evidence.html"
    )


def test_static_page_view_url_uses_msn_article_slug() -> None:
    assert (
        build_static_page_view_url(SOURCE_URL, site_hint="msn")
        == "https://source-evidence.local/replay/msn/ar-AA29207o/static-page-view.html"
    )


def test_static_evidence_validator_rejects_runtime_dependencies() -> None:
    errors = validate_static_replay_evidence_html(
        '<!doctype html><html><body><script src="https://example.test/a.js"></script><iframe src="x"></iframe></body></html>'
    )

    assert "Static evidence page must not contain script tags." in errors
    assert "Static evidence page must not contain iframe tags." in errors
    assert "Static evidence page must not contain remote runtime dependencies." in errors


def test_static_page_view_is_no_js_and_renders_article_comments_and_visual_refs() -> None:
    result = build_static_archived_page_view(
        StaticReplayPageViewInput(
            source_url=SOURCE_URL,
            title="Arrest made after shot fired outside York mosque",
            capture_timestamp="2026-08-09T00:00:00Z",
            article_text="First captured paragraph.\n\nSecond captured paragraph.",
            replay_runtime_notes=("Archived Page Not Found.",),
            comments_evidence=StaticReplayCommentsEvidence(
                status="COMMENTS_COMPLETE",
                declared_comment_count=25,
                comments_json_count=25,
                comments_jsonl_count=21,
                top_level_comment_count=16,
                reply_count=9,
                comments_complete=True,
            ),
            comment_items=(
                StaticReplayCommentItem(
                    comment_id="root-1",
                    author="Fixture author",
                    timestamp="2026-07-30T10:02:22Z",
                    text="Fixture top-level comment.",
                    depth=0,
                    order=1,
                ),
                StaticReplayCommentItem(
                    comment_id="reply-1",
                    parent_id="root-1",
                    author="Fixture reply author",
                    timestamp="2026-07-30T10:03:22Z",
                    text="Fixture reply text.",
                    depth=1,
                    order=2,
                ),
            ),
            screenshot_references=(
                StaticReplayEvidenceReference(label="faithful comments", name="faithful_comments_visible.png", sha256="a" * 64),
                StaticReplayEvidenceReference(label="derived comments", name="derived_comments_full_thread.png", sha256="b" * 64),
            ),
            evidence_report_path="static-evidence.html",
        )
    )

    assert result.status == STATIC_PAGE_VIEW_READY
    assert result.errors == ()
    assert result.contains_script_tag is False
    assert result.contains_iframe_tag is False
    assert result.contains_remote_runtime_dependency is False
    assert "<script" not in result.html.lower()
    assert "<iframe" not in result.html.lower()
    assert STATIC_PAGE_VIEW_WARNING in result.html
    assert "Arrest made after shot fired outside York mosque" in result.html
    assert html.escape(SOURCE_URL, quote=True) in result.html
    assert "2026-08-09T00:00:00Z" in result.html
    assert "First captured paragraph." in result.html
    assert "Comments section" in result.html
    assert "Declared comment count" in result.html
    assert ">25<" in result.html
    assert "Fixture top-level comment." in result.html
    assert "Fixture reply text." in result.html
    assert "faithful_comments_visible.png" in result.html
    assert "Archived Page Not Found" in result.html
    assert "static-evidence.html" in result.html


def test_static_page_view_missing_article_body_does_not_invent_content() -> None:
    result = build_static_archived_page_view(
        StaticReplayPageViewInput(
            source_url=SOURCE_URL,
            title="Fixture title",
            captured_text_snippet="",
        )
    )

    assert "Captured article body text was not available in the local manifest" in result.html
    assert "Fixture invented paragraph" not in result.html


def test_static_page_view_validator_rejects_runtime_dependencies() -> None:
    errors = validate_static_page_view_html(
        '<!doctype html><html><body><script src="https://example.test/a.js"></script><iframe src="x"></iframe></body></html>'
    )

    assert "Static page view must not contain script tags." in errors
    assert "Static page view must not contain iframe tags." in errors
    assert "Static page view must not contain remote runtime dependencies." in errors


def test_static_evidence_warc_contains_replayweb_loadable_request_and_response() -> None:
    input_data = StaticReplayEvidenceInput(
        source_url=SOURCE_URL,
        title="MSN evidence fallback",
        capture_timestamp="2026-08-09T00:00:00Z",
        replay_runtime_notes=("Archived Page Not Found.",),
        comments_evidence=StaticReplayCommentsEvidence(status="COMMENTS_EVIDENCE_VERIFIED", comments_json_count=25),
    )

    page, warc_gz = build_static_replay_evidence_warc(input_data, gzip_output=True)
    raw_warc = gzip.decompress(warc_gz).decode("utf-8", errors="replace")

    assert page.static_url == "https://source-evidence.local/replay/msn/ar-AA29207o/static-evidence.html"
    assert "WARC-Target-URI: https://source-evidence.local/replay/msn/ar-AA29207o/static-evidence.html" in raw_warc
    assert "GET /replay/msn/ar-AA29207o/static-evidence.html HTTP/1.1" in raw_warc
    assert "HTTP/1.1 200 OK" in raw_warc
    assert "Content-Type: text/html; charset=utf-8" in raw_warc
    assert "<script" not in raw_warc.lower()
    assert "<iframe" not in raw_warc.lower()
    assert "COMMENTS_EVIDENCE_VERIFIED" in raw_warc


def test_static_page_view_warc_contains_replayweb_loadable_request_and_response() -> None:
    input_data = StaticReplayPageViewInput(
        source_url=SOURCE_URL,
        title="MSN static page fallback",
        capture_timestamp="2026-08-09T00:00:00Z",
        article_text="Captured article paragraph.",
        replay_runtime_notes=("Archived Page Not Found.",),
        comments_evidence=StaticReplayCommentsEvidence(status="COMMENTS_COMPLETE", comments_json_count=25),
    )

    page, warc_gz = build_static_page_view_warc(input_data, gzip_output=True)
    raw_warc = gzip.decompress(warc_gz).decode("utf-8", errors="replace")

    assert page.static_url == "https://source-evidence.local/replay/msn/ar-AA29207o/static-page-view.html"
    assert "WARC-Target-URI: https://source-evidence.local/replay/msn/ar-AA29207o/static-page-view.html" in raw_warc
    assert "GET /replay/msn/ar-AA29207o/static-page-view.html HTTP/1.1" in raw_warc
    assert "HTTP/1.1 200 OK" in raw_warc
    assert "Content-Type: text/html; charset=utf-8" in raw_warc
    assert "<script" not in raw_warc.lower()
    assert "<iframe" not in raw_warc.lower()
    assert "Captured article paragraph." in raw_warc
    assert "COMMENTS_COMPLETE" in raw_warc
    assert "REPLAY_VISUALLY_VERIFIED" not in raw_warc


def test_static_evidence_standalone_outputs_write_requested_files_without_overwrite() -> None:
    input_data = StaticReplayEvidenceInput(
        source_url=SOURCE_URL,
        title="MSN evidence fallback",
        capture_timestamp="2026-08-09T00:00:00Z",
        replay_runtime_notes=("Archived Page Not Found.",),
        comments_evidence=StaticReplayCommentsEvidence(status="COMMENTS_EVIDENCE_VERIFIED", comments_json_count=25),
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        result = write_static_replay_standalone_outputs(
            input_data,
            html_path=root / "static-evidence.html",
            warc_gz_path=root / "static-evidence.warc.gz",
            warc_path=root / "static-evidence.warc",
        )

        assert STATIC_EVIDENCE_HTML_READY in result.status
        assert STATIC_EVIDENCE_WARC_READY in result.status
        assert result.static_html_sha256
        assert result.static_warc_gz_sha256
        assert result.static_warc_sha256
        html_text = (root / "static-evidence.html").read_text(encoding="utf-8")
        assert STATIC_EVIDENCE_WARNING in html_text
        assert "<script" not in html_text.lower()
        assert "<iframe" not in html_text.lower()
        raw_warc = gzip.decompress((root / "static-evidence.warc.gz").read_bytes()).decode(
            "utf-8",
            errors="replace",
        )
        assert "GET /replay/msn/ar-AA29207o/static-evidence.html HTTP/1.1" in raw_warc
        assert "HTTP/1.1 200 OK" in raw_warc

        blocked = write_static_replay_standalone_outputs(
            input_data,
            html_path=root / "static-evidence.html",
        )
        assert blocked.status == "STATIC_EVIDENCE_OUTPUT_FAILED"
        assert "will not be overwritten" in blocked.errors[0]


def test_static_page_view_standalone_outputs_write_requested_files_without_overwrite() -> None:
    input_data = StaticReplayPageViewInput(
        source_url=SOURCE_URL,
        title="MSN static page fallback",
        capture_timestamp="2026-08-09T00:00:00Z",
        article_text="Captured article paragraph.",
        replay_runtime_notes=("Archived Page Not Found.",),
        comments_evidence=StaticReplayCommentsEvidence(status="COMMENTS_COMPLETE", comments_json_count=25),
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        result = write_static_page_view_standalone_outputs(
            input_data,
            html_path=root / "static-page-view.html",
            warc_gz_path=root / "static-page-view.warc.gz",
            warc_path=root / "static-page-view.warc",
        )

        assert STATIC_PAGE_VIEW_HTML_READY in result.status
        assert STATIC_PAGE_VIEW_WARC_READY in result.status
        assert result.static_page_view_html_sha256
        assert result.static_page_view_warc_gz_sha256
        assert result.static_page_view_warc_sha256
        html_text = (root / "static-page-view.html").read_text(encoding="utf-8")
        assert STATIC_PAGE_VIEW_WARNING in html_text
        assert "<script" not in html_text.lower()
        assert "<iframe" not in html_text.lower()
        raw_warc = gzip.decompress((root / "static-page-view.warc.gz").read_bytes()).decode(
            "utf-8",
            errors="replace",
        )
        assert "GET /replay/msn/ar-AA29207o/static-page-view.html HTTP/1.1" in raw_warc
        assert "HTTP/1.1 200 OK" in raw_warc

        blocked = write_static_page_view_standalone_outputs(
            input_data,
            html_path=root / "static-page-view.html",
        )
        assert blocked.status == "STATIC_PAGE_VIEW_OUTPUT_FAILED"
        assert "will not be overwritten" in blocked.errors[0]


def run_self_test() -> None:
    test_static_evidence_page_is_no_js_no_iframe_and_contains_required_sections()
    test_static_evidence_url_uses_msn_article_slug()
    test_static_page_view_url_uses_msn_article_slug()
    test_static_evidence_validator_rejects_runtime_dependencies()
    test_static_page_view_is_no_js_and_renders_article_comments_and_visual_refs()
    test_static_page_view_missing_article_body_does_not_invent_content()
    test_static_page_view_validator_rejects_runtime_dependencies()
    test_static_evidence_warc_contains_replayweb_loadable_request_and_response()
    test_static_page_view_warc_contains_replayweb_loadable_request_and_response()
    test_static_evidence_standalone_outputs_write_requested_files_without_overwrite()
    test_static_page_view_standalone_outputs_write_requested_files_without_overwrite()


if __name__ == "__main__":
    run_self_test()
    print("source_replay_static_snapshot.py: OK")
