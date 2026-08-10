from __future__ import annotations

import json
from pathlib import Path

from evidence_schema import PrimarySourceStatus, SourceRole
from source_msn_adapter_manifest import (
    MSN_SOURCE_ADAPTER_NAME,
    build_msn_source_adapter_bundle,
    extract_msn_article_from_html,
)


SOURCE_URL = "https://www.msn.com/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"


def _msn_repost_html() -> str:
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


def test_extracts_msn_repost_article_as_secondary_framing() -> None:
    article = extract_msn_article_from_html(_msn_repost_html(), source_url=SOURCE_URL)

    assert article.title == "Arrest made after shot fired outside York mosque"
    assert article.publisher_name == "The Independent"
    assert article.author == "Tom Wilkinson"
    assert article.source_role == SourceRole.SECONDARY_OUTSIDE_PERSPECTIVE
    assert article.primary_source_status == PrimarySourceStatus.SECONDARY_FRAMING_ONLY
    assert article.source_chain_gap is True
    assert "Do not substitute MSN" in article.verification_notes
    assert article.visible_source_credit == "Google Street View"
    assert any("independent.co.uk" in link["url"] for link in article.extracted_links)


def test_builds_complete_msn_adapter_manifest_with_article_comments_archive_media_and_roles(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    rendered = archive_dir / "rendered-page.html"
    rendered.write_text(_msn_repost_html(), encoding="utf-8")
    (archive_dir / "rendered-page.warc.gz").write_bytes(b"warc-fixture")
    (archive_dir / "archive.viewable-live-capture.wacz").write_bytes(b"strict-wacz-fixture")
    (archive_dir / "validation.json").write_text('{"strict_wacz_status":"STRICT_WACZ_EXPERIMENTAL_POSSIBLY_UNSUPPORTED"}', encoding="utf-8")
    (archive_dir / "capture-manifest.json").write_text("{}", encoding="utf-8")
    (archive_dir / "local_viewer").mkdir()
    (archive_dir / "local_viewer" / "open_local_viewer.cmd").write_text("@echo off\n", encoding="utf-8")
    (archive_dir / "local_viewer" / "index.html").write_text("<html>viewer</html>", encoding="utf-8")

    comments_export = {
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
    comments_file = tmp_path / "msn-comments-v35-profile-stats.json"
    comments_file.write_text(json.dumps(comments_export), encoding="utf-8")

    local_image = tmp_path / "hero.jpg"
    local_image.write_bytes(b"image-fixture")
    bundle = build_msn_source_adapter_bundle(
        source_url=SOURCE_URL,
        rendered_html_path=rendered,
        comments_export=comments_export,
        comments_export_files={"json_path": str(comments_file)},
        offline_archive_dir=archive_dir,
        media_download_results=(
            {
                "resource_id": "not-matching",
                "status": "success",
                "output_path": str(local_image),
                "sha256": "fixture-hash",
            },
        ),
        package_id="msn_complete_adapter",
        capture_session_id="session-1",
    )
    payload = bundle.to_dict()
    manifest = payload["manifest"]

    assert payload["schema_version"] == "msn_source_adapter_bundle_v1"
    assert payload["adapter_name"] == MSN_SOURCE_ADAPTER_NAME
    assert payload["article"]["publisher_name"] == "The Independent"
    assert payload["article"]["primary_source_status"] == "SECONDARY_FRAMING_ONLY"
    assert "msn_article_extraction" in manifest["capture_options"]
    assert "msn_comments_profile_extraction" in manifest["capture_options"]
    assert "msn_offline_archive_viewer" in manifest["capture_options"]
    assert "msn_media_discovery" in manifest["capture_options"]
    assert "msn_source_role_provenance" in manifest["capture_options"]

    asset_descriptions = [asset["description"] for asset in manifest["assets"]]
    assert "MSN best viewable rendered HTML article backup" in asset_descriptions
    assert "MSN partial ReplayWeb WARC.GZ archive" in asset_descriptions
    assert "MSN strict WACZ artifact, experimental/possibly unsupported" in asset_descriptions
    assert any("comments/profile export" in description for description in asset_descriptions)

    provenance = manifest["provenance_records"]
    assert any(record["capture_purpose"] == "MSN article extraction with source-role provenance" for record in provenance)
    assert any(record["capture_purpose"] == "MSN user comment/profile extraction" and record["source_role"] == "PRIMARY_ORIGINAL_AUTHORED" for record in provenance)
    assert any(record["capture_purpose"] == "MSN media discovery/download registration" for record in provenance)

    media_notes = manifest["media_source_chain_notes"]
    assert media_notes
    assert any(note["publisher_name"] == "The Independent" for note in media_notes)
    assert any("Do not assume" in note["notes_on_context_dispute"] for note in media_notes)
    assert any(record["source_chain_gap"] for record in payload["media_records"])


if __name__ == "__main__":
    test_extracts_msn_repost_article_as_secondary_framing()
    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        test_builds_complete_msn_adapter_manifest_with_article_comments_archive_media_and_roles(Path(folder))
    print("MSN source adapter manifest self-test passed.")
