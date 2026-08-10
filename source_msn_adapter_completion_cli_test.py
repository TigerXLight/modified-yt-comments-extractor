from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_completion_cli import run_msn_source_adapter_completion


def _write_fixture(root: Path) -> tuple[Path, Path, Path]:
    html = root / "rendered-page.html"
    html.write_text(
        """
        <html><head>
        <meta property="og:title" content="MSN reposted test story">
        <meta property="og:image" content="https://img-s-msn-com.akamaized.net/test-hero.jpg">
        <meta property="og:video" content="https://videos.example.test/clip.mp4">
        <script type="application/ld+json">{"@type":"NewsArticle","publisher":{"name":"The Independent"},"image":"https://static.independent.co.uk/news.jpg"}</script>
        </head><body>
        <article><h1>MSN reposted test story</h1><p>By Test Reporter</p><p>13 July 2026</p><p>This is a long enough rendered MSN article body used by the source adapter completion self-test. It preserves publisher framing and media credits.</p><img src="hero-local.jpg" alt="Google Street View example"></article>
        </body></html>
        """,
        encoding="utf-8",
    )
    comments = root / "msn-comments-v35-profile-stats.json"
    comments.write_text(
        json.dumps(
            {
                "comments": [
                    {
                        "id": "C0001",
                        "author": "Reader One",
                        "body": "A parent comment.",
                        "likes": 2,
                        "dislikes": 1,
                        "profile_url": "https://www.msn.com/en-gb/community/profile/cid-abc",
                        "profile_cid": "cid-abc",
                        "account_comments": 10,
                        "account_likes": 20,
                        "account_followers": 1,
                        "replies": [
                            {"id": "C0002", "parent_id": "C0001", "author": "Reader Two", "body": "A reply."}
                        ],
                    }
                ],
                "profiles": [
                    {"profile_cid": "cid-abc", "author": "Reader One", "account_comments": 10, "account_likes": 20, "account_followers": 1}
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    request_log = root / "request-log.json"
    request_log.write_text(
        json.dumps(
            {
                "requests": [
                    {"url": "https://img-s-msn-com.akamaized.net/test-hero.jpg", "resource_type": "image", "status": 200},
                    {"url": "https://videos.example.test/clip.m3u8", "resource_type": "media", "status": 200},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "rendered-page.warc.gz").write_bytes(b"fixture warc")
    (root / "archive.viewable-live-capture.wacz").write_bytes(b"fixture strict wacz")
    viewer = root / "local_viewer"
    viewer.mkdir()
    (viewer / "open_local_viewer.cmd").write_text("@echo off\necho viewer\n", encoding="utf-8")
    return html, comments, request_log


def test_completion_cli_builds_operator_facing_package() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        html, comments, request_log = _write_fixture(root)
        run = run_msn_source_adapter_completion(
            root,
            source_url="https://www.msn.com/en-gb/news/example/ar-AA123",
            rendered_html_path=html,
            comments_json_path=comments,
            request_log_path=request_log,
            select_all_images=True,
        )
        data = run.to_dict()
        assert data["schema_version"] == "msn_source_adapter_completion_run_v1"
        assert data["overall_status"] in {"CONFIDENT_WITH_MANUAL_REVIEW", "PARTIAL_NEEDS_REVIEW"}
        assert data["counts"]["media_resources"] >= 2
        assert data["counts"]["total_manifest_assets"] >= 1
        assert Path(data["completion_json"]).is_file()
        assert Path(data["completion_markdown"]).is_file()
        assert Path(data["output_paths"]["media_inventory_json"]).is_file()
        assert Path(data["output_paths"]["total_package_index_markdown"]).is_file()
        assert "The Independent" in Path(data["completion_markdown"]).read_text(encoding="utf-8")


if __name__ == "__main__":
    test_completion_cli_builds_operator_facing_package()
    print("MSN adapter completion CLI self-test passed.")
