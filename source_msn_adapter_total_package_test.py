from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from source_msn_adapter_total_package import (
    MSN_BUNDLE_JSON,
    MSN_TOTAL_PACKAGE_INDEX_MD,
    write_msn_source_adapter_total_package,
)


def test_total_package_joins_article_comments_archive_media_and_reports() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        html_path = root / "rendered-page.html"
        media_url = "https://img-s-msn-com.akamaized.net/example/hero.jpg"
        html_path.write_text(
            "\n".join(
                [
                    "<html><head>",
                    "<meta property='og:title' content='Twelve arrested over terror threat at Islamic festival'>",
                    "<meta property='og:site_name' content='The Independent'>",
                    f"<meta property='og:image' content='{media_url}'>",
                    "</head><body>",
                    "<h1>Twelve arrested over terror threat at Islamic festival</h1>",
                    "<p>Story by Example Reporter • 2 min read</p>",
                    "<p>Article body line with enough detail to pass the structural article extraction gate.</p>",
                    "<p>Image credit: Google Street View</p>",
                    "</body></html>",
                ]
            ),
            encoding="utf-8",
        )
        (root / "rendered-page.warc.gz").write_bytes(b"warc")
        (root / "archive.viewable-live-capture.wacz").write_bytes(b"wacz")
        (root / "capture-manifest.json").write_text("{}", encoding="utf-8")
        (root / "validation.json").write_text('{"article_completeness_status":"partial"}', encoding="utf-8")
        viewer = root / "local_viewer"
        viewer.mkdir()
        (viewer / "index.html").write_text("viewer", encoding="utf-8")
        (viewer / "open_local_viewer.cmd").write_text("echo viewer", encoding="utf-8")
        comments_path = root / "msn-comments-v35-profile-stats.json"
        comments_path.write_text(
            json.dumps(
                {
                    "comments": [
                        {
                            "human_id": "C0001",
                            "author": "Commenter",
                            "date": "13 Jul",
                            "text": "Visible MSN comment text.",
                            "author_profile_cid": "cid-example",
                            "replies": [
                                {"human_id": "C0001-R0001", "parent_human_id": "C0001", "author": "Reply", "text": "Reply text."}
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (root / "msn-profiles.json").write_text('{"profiles":[{"profile_cid":"cid-example"}]}', encoding="utf-8")
        media_file = root / "hero.jpg"
        payload = b"downloaded image"
        media_file.write_bytes(payload)
        (root / "msn-media-download-results.json").write_text(
            json.dumps(
                {
                    "download_results": [
                        {
                            "resource_id": "manual-known-url",
                            "url": media_url,
                            "status": "SUCCESS",
                            "output_path": str(media_file),
                            "sha256": hashlib.sha256(payload).hexdigest(),
                            "size_bytes": len(payload),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        result = write_msn_source_adapter_total_package(
            root,
            source_url="https://www.msn.com/en-gb/news/uknews/twelve-arrested-over-terror-threat-at-islamic-festival/ar-AA27OIhw",
        )
        out = Path(result.inputs.output_dir)
        assert (out / MSN_BUNDLE_JSON).is_file()
        assert (out / MSN_TOTAL_PACKAGE_INDEX_MD).is_file()
        assert Path(result.output_paths["final_validation_markdown"]).is_file()
        bundle = json.loads((out / MSN_BUNDLE_JSON).read_text(encoding="utf-8"))
        assert bundle["article"]["publisher_name"] == "The Independent"
        assert bundle["media_records"]
        assert any(record["local_file_hash"] == hashlib.sha256(payload).hexdigest() for record in bundle["media_records"])
        assert result.counts["comments_supplied"] == 1
        assert result.counts["local_media_assets"] >= 1
        index = (out / MSN_TOTAL_PACKAGE_INDEX_MD).read_text(encoding="utf-8")
        assert "article extraction" in index.lower()
        assert "source-role provenance" in json.dumps(bundle).lower() or bundle["manifest"]["provenance_records"]


def run_tests() -> None:
    test_total_package_joins_article_comments_archive_media_and_reports()
    print("MSN total package self-test passed.")


if __name__ == "__main__":
    run_tests()
