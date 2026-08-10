from __future__ import annotations

import json
from pathlib import Path

from source_msn_adapter_manifest import build_msn_source_adapter_bundle
from source_msn_adapter_readiness import READINESS_STRUCTURALLY_COMPLETE, evaluate_msn_source_adapter_readiness
from source_msn_adapter_release_report import (
    RELEASE_STATUS_READY_FOR_MANUAL_LIVE_VALIDATION,
    build_msn_source_adapter_release_report,
    render_msn_source_adapter_release_markdown,
    write_msn_source_adapter_release_outputs,
)


SOURCE_URL = "https://www.msn.com/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"


def _html() -> str:
    return """
    <!doctype html>
    <html>
    <head>
      <title>Arrest made after shot fired outside York mosque</title>
      <meta property="og:site_name" content="The Independent">
      <meta property="og:title" content="Arrest made after shot fired outside York mosque">
      <meta property="og:image" content="https://img-s-msn-com.akamaized.net/hero.jpg">
      <meta property="og:video" content="https://video.msn.com/clips/york-mosque.mp4">
      <meta name="twitter:player:stream" content="https://video.msn.com/clips/york-mosque/master.m3u8">
      <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "Arrest made after shot fired outside York mosque",
        "image": ["https://cdn.independent.co.uk/york-mosque-structured.jpg"],
        "video": {
          "@type": "VideoObject",
          "name": "York Mosque video candidate",
          "thumbnailUrl": "https://cdn.independent.co.uk/york-video-poster.jpg",
          "contentUrl": "https://cdn.independent.co.uk/york-video/master.m3u8"
        }
      }
      </script>
    </head>
    <body>
      <main>
        <section>The Independent <button>Follow</button></section>
        <h1>Arrest made after shot fired outside York mosque</h1>
        <p>Story by Tom Wilkinson • 1w • 1 min read</p>
        <figure>
          <img src="https://assets.msn.com/hero.jpg" alt="York Mosque">
          <figcaption>Screenshot 2025-07-31 at 07.50 copy © Google Street View</figcaption>
        </figure>
        <p>A 44-year-old man has been arrested after a firearm was discharged outside York Mosque and Islamic Centre.</p>
        <p>No one was injured in the incident, and the firearm is believed to have been an air weapon.</p>
        <p>IN FULL <a href="https://www.independent.co.uk/news/uk/example-source">Man arrested after incident outside York mosque</a></p>
      </main>
    </body>
    </html>
    """


def _comments_export() -> dict[str, object]:
    return {
        "comments": [
            {
                "human_id": "C0001",
                "source_comment_id": "comment-1",
                "author": "Commenter",
                "author_profile_cid": "cid-example",
                "date": "13 Jul",
                "text": "Visible authored comment.",
                "likes": "2",
                "dislikes": "0",
                "replies": [
                    {
                        "human_id": "R0001",
                        "parent_human_id": "C0001",
                        "source_comment_id": "reply-1",
                        "author": "Reply User",
                        "author_profile_cid": "cid-reply",
                        "date": "13 Jul",
                        "text": "Nested authored reply.",
                        "replies": [],
                    }
                ],
            }
        ]
    }


def _archive_dir(tmp_path: Path) -> Path:
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir(parents=True)
    (archive_dir / "rendered-page.html").write_text(_html(), encoding="utf-8")
    (archive_dir / "rendered-page.warc.gz").write_bytes(b"warc-fixture")
    (archive_dir / "archive.viewable-live-capture.wacz").write_bytes(b"strict-wacz-fixture")
    (archive_dir / "validation.json").write_text('{"strict_wacz_status":"STRICT_WACZ_EXPERIMENTAL_POSSIBLY_UNSUPPORTED"}', encoding="utf-8")
    (archive_dir / "capture-manifest.json").write_text("{}", encoding="utf-8")
    (archive_dir / "local_viewer").mkdir()
    (archive_dir / "local_viewer" / "open_local_viewer.cmd").write_text("@echo off\n", encoding="utf-8")
    (archive_dir / "local_viewer" / "index.html").write_text("<html>viewer</html>", encoding="utf-8")
    return archive_dir


def _bundle(tmp_path: Path):
    archive_dir = _archive_dir(tmp_path)
    comments_file = tmp_path / "msn-comments-v35-profile-stats.json"
    comments_file.write_text(json.dumps(_comments_export()), encoding="utf-8")
    preview = build_msn_source_adapter_bundle(
        source_url=SOURCE_URL,
        rendered_html_path=archive_dir / "rendered-page.html",
        comments_export=_comments_export(),
        comments_export_files={"json_path": str(comments_file)},
        offline_archive_dir=archive_dir,
        package_id="msn_release_adapter",
        capture_session_id="session-1",
    )
    assert any("json_ld" in record.resource["discovery_methods"] for record in preview.media_records)
    assert any("opengraph" in record.resource["discovery_methods"] for record in preview.media_records)
    first_resource_id = preview.media_records[0].resource["resource_id"]
    local_image = tmp_path / "hero.jpg"
    local_image.write_bytes(b"image-fixture")
    return build_msn_source_adapter_bundle(
        source_url=SOURCE_URL,
        rendered_html_path=archive_dir / "rendered-page.html",
        comments_export=_comments_export(),
        comments_export_files={"json_path": str(comments_file)},
        offline_archive_dir=archive_dir,
        media_download_results=(
            {
                "resource_id": first_resource_id,
                "status": "success",
                "output_path": str(local_image),
                "sha256": "fixture-hash",
            },
        ),
        package_id="msn_release_adapter",
        capture_session_id="session-1",
    )


def test_release_report_marks_structural_completion_as_ready_for_manual_live_validation(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    readiness = evaluate_msn_source_adapter_readiness(bundle)
    report = build_msn_source_adapter_release_report(bundle, readiness=readiness).to_dict()

    assert readiness.overall_status == READINESS_STRUCTURALLY_COMPLETE
    assert report["release_status"] == RELEASE_STATUS_READY_FOR_MANUAL_LIVE_VALIDATION
    assert report["manual_review_required"] is True
    assert any(area["name"] == "media_discovery_download" for area in report["areas"])
    assert any("The Independent" in item or "reposting" in item for item in report["manual_live_validation_checklist"])
    assert any("does not run browser automation" in item for item in report["limitations"])


def test_release_markdown_includes_manual_validation_and_source_role_scope(tmp_path: Path) -> None:
    report = build_msn_source_adapter_release_report(_bundle(tmp_path))
    text = render_msn_source_adapter_release_markdown(report)

    assert "# MSN Source Adapter Release Report" in text
    assert "READY_FOR_MANUAL_LIVE_VALIDATION" in text
    assert "Manual live validation checklist" in text
    assert "source-role" in text or "source role" in text
    assert "WARC.GZ" in text
    assert "strict WACZ" in text


def test_write_release_outputs(tmp_path: Path) -> None:
    paths = write_msn_source_adapter_release_outputs(bundle=_bundle(tmp_path), output_dir=tmp_path / "release")

    for path in paths.values():
        assert Path(path).exists(), path
    report_json = json.loads(Path(paths["release_report_json"]).read_text(encoding="utf-8"))
    report_md = Path(paths["release_report_markdown"]).read_text(encoding="utf-8")

    assert report_json["release_status"] == RELEASE_STATUS_READY_FOR_MANUAL_LIVE_VALIDATION
    assert "MSN Source Adapter Release Report" in report_md
    assert "Manual Live Validation" in Path(paths["manual_live_validation_markdown"]).read_text(encoding="utf-8")


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        test_release_report_marks_structural_completion_as_ready_for_manual_live_validation(Path(folder) / "ready")
    with tempfile.TemporaryDirectory() as folder:
        test_release_markdown_includes_manual_validation_and_source_role_scope(Path(folder) / "markdown")
    with tempfile.TemporaryDirectory() as folder:
        test_write_release_outputs(Path(folder) / "write")
    print("MSN source adapter release report self-test passed.")
