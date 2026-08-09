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
    StaticReplayCommentsEvidence,
    StaticReplayEvidenceInput,
    StaticReplayEvidenceReference,
    build_static_evidence_url,
    build_static_replay_evidence_page,
    build_static_replay_evidence_warc,
    validate_static_replay_evidence_html,
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


def test_static_evidence_validator_rejects_runtime_dependencies() -> None:
    errors = validate_static_replay_evidence_html(
        '<!doctype html><html><body><script src="https://example.test/a.js"></script><iframe src="x"></iframe></body></html>'
    )

    assert "Static evidence page must not contain script tags." in errors
    assert "Static evidence page must not contain iframe tags." in errors
    assert "Static evidence page must not contain remote runtime dependencies." in errors


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


def run_self_test() -> None:
    test_static_evidence_page_is_no_js_no_iframe_and_contains_required_sections()
    test_static_evidence_url_uses_msn_article_slug()
    test_static_evidence_validator_rejects_runtime_dependencies()
    test_static_evidence_warc_contains_replayweb_loadable_request_and_response()
    test_static_evidence_standalone_outputs_write_requested_files_without_overwrite()


if __name__ == "__main__":
    run_self_test()
    print("source_replay_static_snapshot.py: OK")
