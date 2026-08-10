from __future__ import annotations

import json
from pathlib import Path

from source_msn_adapter_final_validator import (
    OVERALL_CONFIDENT_WITH_MANUAL_REVIEW,
    OVERALL_NOT_READY,
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_PARTIAL,
    build_msn_adapter_final_validation_report,
    main,
    render_msn_adapter_final_validation_markdown,
    write_msn_adapter_final_validation_outputs,
)
from source_msn_adapter_manifest import build_msn_source_adapter_bundle, write_msn_source_adapter_bundle_json
from source_msn_adapter_readiness import evaluate_msn_source_adapter_readiness, write_msn_source_adapter_readiness_report
from source_msn_adapter_release_report import build_msn_source_adapter_release_report, write_msn_source_adapter_release_outputs


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
      <meta name="twitter:player:stream" content="https://video.msn.com/york/master.m3u8">
      <script type="application/ld+json">
      {"@context":"https://schema.org","@type":"NewsArticle","headline":"Arrest made after shot fired outside York mosque","image":["https://cdn.independent.co.uk/york.jpg"],"video":{"@type":"VideoObject","thumbnailUrl":"https://cdn.independent.co.uk/poster.jpg","contentUrl":"https://cdn.independent.co.uk/york/master.m3u8"}}
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


def _complete_folder(tmp_path: Path) -> Path:
    root = tmp_path / "msn_output"
    root.mkdir(parents=True)
    (root / "rendered-page.html").write_text(_html(), encoding="utf-8")
    (root / "rendered-page.warc.gz").write_bytes(b"warc-fixture")
    (root / "archive.viewable-live-capture.wacz").write_bytes(b"strict-wacz-fixture")
    (root / "validation.json").write_text('{"strict_wacz_status":"STRICT_WACZ_EXPERIMENTAL_POSSIBLY_UNSUPPORTED"}', encoding="utf-8")
    (root / "capture-manifest.json").write_text("{}", encoding="utf-8")
    (root / "local_viewer").mkdir()
    (root / "local_viewer" / "open_local_viewer.cmd").write_text("@echo off\n", encoding="utf-8")
    (root / "local_viewer" / "index.html").write_text("<html>viewer</html>", encoding="utf-8")

    comments = _comments_export()
    comments_path = root / "msn-comments-v35-profile-stats.json"
    comments_path.write_text(json.dumps(comments), encoding="utf-8")
    (root / "msn-comments-v35-profile-stats.txt").write_text("Commenter · 13 Jul\n\nVisible authored comment.\n", encoding="utf-8")
    (root / "msn-comments-v35-profile-stats.html").write_text("<html>comments</html>", encoding="utf-8")
    (root / "msn-profiles.json").write_text(json.dumps({"profiles": [{"author": "Commenter", "profile_cid": "cid-example"}]}), encoding="utf-8")
    (root / "msn-profiles.csv").write_text("author,profile_cid\nCommenter,cid-example\n", encoding="utf-8")

    media_dir = root / "media"
    media_dir.mkdir()
    local_image = media_dir / "hero.jpg"
    local_image.write_bytes(b"image-fixture")

    preview = build_msn_source_adapter_bundle(
        source_url=SOURCE_URL,
        rendered_html_path=root / "rendered-page.html",
        comments_export=comments,
        comments_export_files={"json_path": str(comments_path)},
        offline_archive_dir=root,
        package_id="msn_final_adapter",
        capture_session_id="session-1",
    )
    first_resource_id = preview.media_records[0].resource["resource_id"]
    bundle = build_msn_source_adapter_bundle(
        source_url=SOURCE_URL,
        rendered_html_path=root / "rendered-page.html",
        comments_export=comments,
        comments_export_files={"json_path": str(comments_path)},
        offline_archive_dir=root,
        media_download_results=(
            {
                "resource_id": first_resource_id,
                "status": "success",
                "output_path": str(local_image),
                "sha256": "fixture-hash",
            },
        ),
        package_id="msn_final_adapter",
        capture_session_id="session-1",
    )
    write_msn_source_adapter_bundle_json(bundle, root / "msn-source-adapter-bundle.json")
    readiness = evaluate_msn_source_adapter_readiness(bundle)
    write_msn_source_adapter_readiness_report(readiness, root / "msn-source-adapter-readiness.json")
    release = build_msn_source_adapter_release_report(bundle, readiness=readiness)
    assert release.release_status == "READY_FOR_MANUAL_LIVE_VALIDATION"
    write_msn_source_adapter_release_outputs(bundle=bundle, output_dir=root, base_name="msn-source-adapter-release")
    return root


def test_final_validator_marks_complete_msn_output_confident(tmp_path: Path) -> None:
    root = _complete_folder(tmp_path)
    report = build_msn_adapter_final_validation_report(root, source_url=SOURCE_URL).to_dict()

    assert report["overall_status"] == OVERALL_CONFIDENT_WITH_MANUAL_REVIEW
    statuses = {area["name"]: area["status"] for area in report["areas"]}
    assert statuses["article_extraction"] == STATUS_PASS
    assert statuses["comments_profile_extraction"] == STATUS_PASS
    assert statuses["offline_webpage_viewer"] == STATUS_PASS
    assert statuses["media_discovery_download_registration"] == STATUS_PASS
    assert statuses["source_role_and_media_source_chain"] == STATUS_PASS
    assert statuses["total_export_manifest_and_release_outputs"] == STATUS_PASS
    assert report["counts"]["comment_items"] == 2
    assert report["counts"]["local_media_files"] >= 1
    assert "The Independent" in report["msn_republisher_note"]
    assert "Google Street View" in report["msn_republisher_note"]


def test_final_validator_blocks_missing_comments_and_manifest_outputs(tmp_path: Path) -> None:
    root = tmp_path / "partial"
    root.mkdir(parents=True)
    (root / "rendered-page.html").write_text(_html(), encoding="utf-8")
    (root / "rendered-page.warc.gz").write_bytes(b"warc-fixture")

    report = build_msn_adapter_final_validation_report(root, source_url=SOURCE_URL).to_dict()
    statuses = {area["name"]: area["status"] for area in report["areas"]}

    assert report["overall_status"] == OVERALL_NOT_READY
    assert statuses["comments_profile_extraction"] == STATUS_FAIL
    assert statuses["offline_webpage_viewer"] == STATUS_PARTIAL
    assert statuses["total_export_manifest_and_release_outputs"] == STATUS_FAIL


def test_final_validation_markdown_and_output_files(tmp_path: Path) -> None:
    root = _complete_folder(tmp_path)
    report = build_msn_adapter_final_validation_report(root, source_url=SOURCE_URL)
    markdown = render_msn_adapter_final_validation_markdown(report)

    assert "MSN Adapter Final Validation Report" in markdown
    assert "CONFIDENT_WITH_MANUAL_REVIEW" in markdown
    assert "MSN republisher/source-chain note" in markdown
    assert "The Independent" in markdown

    paths = write_msn_adapter_final_validation_outputs(root, source_url=SOURCE_URL)
    assert Path(paths["final_validation_json"]).exists()
    assert Path(paths["final_validation_markdown"]).exists()
    payload = json.loads(Path(paths["final_validation_json"]).read_text(encoding="utf-8"))
    assert payload["overall_status"] == OVERALL_CONFIDENT_WITH_MANUAL_REVIEW


def test_final_validator_cli_returns_zero_for_confident_output(tmp_path: Path) -> None:
    root = _complete_folder(tmp_path)
    output_dir = tmp_path / "reports"
    code = main([str(root), "--source-url", SOURCE_URL, "--output-dir", str(output_dir)])

    assert code == 0
    assert (output_dir / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.json").exists()
    assert (output_dir / "MSN_ADAPTER_FINAL_VALIDATION_REPORT.md").exists()


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        test_final_validator_marks_complete_msn_output_confident(Path(folder) / "complete")
    with tempfile.TemporaryDirectory() as folder:
        test_final_validator_blocks_missing_comments_and_manifest_outputs(Path(folder) / "missing")
    with tempfile.TemporaryDirectory() as folder:
        test_final_validation_markdown_and_output_files(Path(folder) / "outputs")
    with tempfile.TemporaryDirectory() as folder:
        test_final_validator_cli_returns_zero_for_confident_output(Path(folder) / "cli")
    print("MSN adapter final validator self-test passed.")
