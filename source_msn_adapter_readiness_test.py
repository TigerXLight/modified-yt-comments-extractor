from __future__ import annotations

import json
from pathlib import Path

from source_msn_adapter_manifest import build_msn_source_adapter_bundle
from source_msn_adapter_readiness import (
    READINESS_MISSING,
    READINESS_PARTIAL,
    READINESS_STRUCTURALLY_COMPLETE,
    evaluate_msn_source_adapter_readiness,
    write_msn_source_adapter_readiness_report,
)


SOURCE_URL = "https://www.msn.com/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"


def _msn_complete_html() -> str:
    return """
    <!doctype html>
    <html>
    <head>
      <title>Arrest made after shot fired outside York mosque</title>
      <meta property="og:site_name" content="The Independent">
      <meta property="og:title" content="Arrest made after shot fired outside York mosque">
      <meta property="og:image" content="https://img-s-msn-com.akamaized.net/hero.jpg">
    </head>
    <body>
      <main>
        <section>The Independent <button>Follow</button> <span>2.4M Followers</span></section>
        <h1>Arrest made after shot fired outside York mosque</h1>
        <p>Story by Tom Wilkinson • 1w • 1 min read</p>
        <figure>
          <img src="https://assets.msn.com/hero.jpg" alt="York Mosque">
          <figcaption>Screenshot 2025-07-31 at 07.50 copy © Google Street View</figcaption>
        </figure>
        <ul>
          <li>A 44-year-old man has been arrested after a firearm was discharged outside York Mosque and Islamic Centre.</li>
          <li>No one was injured in the incident, and the firearm is believed to have been an air weapon.</li>
        </ul>
        <p>IN FULL <a href="https://www.independent.co.uk/news/uk/example-source">Man arrested after incident outside York mosque</a></p>
        <video poster="/video-poster.jpg"><source src="/video/stream.m3u8" type="application/x-mpegURL"></video>
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
    (archive_dir / "rendered-page.html").write_text(_msn_complete_html(), encoding="utf-8")
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
    preview_bundle = build_msn_source_adapter_bundle(
        source_url=SOURCE_URL,
        rendered_html_path=archive_dir / "rendered-page.html",
        comments_export=_comments_export(),
        comments_export_files={"json_path": str(comments_file)},
        offline_archive_dir=archive_dir,
        package_id="msn_complete_adapter",
        capture_session_id="session-1",
    )
    first_resource_id = preview_bundle.media_records[0].resource["resource_id"]
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
        package_id="msn_complete_adapter",
        capture_session_id="session-1",
    )


def test_msn_adapter_readiness_marks_complete_bundle_structurally_complete(tmp_path: Path) -> None:
    report = evaluate_msn_source_adapter_readiness(_bundle(tmp_path))
    payload = report.to_dict()

    assert payload["overall_status"] == READINESS_STRUCTURALLY_COMPLETE
    assert payload["article_status"] == "CONFIDENT"
    assert payload["comments_status"] == "CONFIDENT"
    assert payload["offline_viewer_status"] == "CONFIDENT"
    assert payload["media_status"] == "CONFIDENT"
    assert payload["provenance_status"] == "CONFIDENT"
    assert payload["counts"]["comment_provenance_records"] == 2
    assert payload["counts"]["local_media_assets"] >= 1
    assert any("The Independent" in limitation for limitation in payload["limitations"])


def test_msn_adapter_readiness_remains_partial_when_media_is_discovered_but_not_downloaded(tmp_path: Path) -> None:
    archive_dir = _archive_dir(tmp_path)
    bundle = build_msn_source_adapter_bundle(
        source_url=SOURCE_URL,
        rendered_html_path=archive_dir / "rendered-page.html",
        comments_export=_comments_export(),
        offline_archive_dir=archive_dir,
        package_id="msn_complete_adapter",
        capture_session_id="session-1",
    )

    report = evaluate_msn_source_adapter_readiness(bundle).to_dict()

    assert report["overall_status"] == READINESS_STRUCTURALLY_COMPLETE
    assert report["media_status"] == READINESS_PARTIAL
    assert report["counts"]["media_records"] >= 1
    assert report["counts"]["local_media_assets"] == 0
    assert any("not downloaded evidence files" in limitation for limitation in report["limitations"])


def test_msn_adapter_readiness_blocks_missing_comments_and_archive(tmp_path: Path) -> None:
    bundle = build_msn_source_adapter_bundle(
        source_url=SOURCE_URL,
        rendered_html=_msn_complete_html(),
        package_id="msn_incomplete_adapter",
        capture_session_id="session-1",
    )

    report = evaluate_msn_source_adapter_readiness(bundle).to_dict()

    assert report["overall_status"] == "NOT_COMPLETE"
    assert report["comments_status"] == READINESS_MISSING
    assert report["offline_viewer_status"] == READINESS_PARTIAL
    assert any(finding["blocking"] for finding in report["findings"])


def test_write_msn_adapter_readiness_report_json(tmp_path: Path) -> None:
    report = evaluate_msn_source_adapter_readiness(_bundle(tmp_path))
    path = write_msn_source_adapter_readiness_report(report, tmp_path / "readiness.json")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    assert payload["schema_version"] == "msn_source_adapter_readiness_v1"
    assert payload["overall_status"] == READINESS_STRUCTURALLY_COMPLETE


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        test_msn_adapter_readiness_marks_complete_bundle_structurally_complete(Path(folder) / "complete")
    with tempfile.TemporaryDirectory() as folder:
        test_msn_adapter_readiness_remains_partial_when_media_is_discovered_but_not_downloaded(Path(folder) / "partial")
    with tempfile.TemporaryDirectory() as folder:
        test_msn_adapter_readiness_blocks_missing_comments_and_archive(Path(folder) / "missing")
    with tempfile.TemporaryDirectory() as folder:
        test_write_msn_adapter_readiness_report_json(Path(folder) / "write")
    print("MSN source adapter readiness self-test passed.")
