from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from source_msn_vertical_live_validation import (
    DEFAULT_MSN_VERTICAL_URL,
    STATUS_BLOCKED,
    STATUS_LIVE_SITE_MANUALLY_TESTED,
    HttpFetchResult,
    run_msn_vertical_live_validation,
)


HTML = """<!doctype html>
<html>
  <head>
    <title>Fixture MSN Story</title>
    <meta property="og:image" content="https://img-s-msn-com.akamaized.net/fixture.jpg">
  </head>
  <body>
    <article>
      <h1>Fixture MSN Story</h1>
      <p>Article sentence one.</p>
      <p>Article sentence two.</p>
    </article>
    <img src="https://img-s-msn-com.akamaized.net/hero.webp" alt="Hero">
    <video poster="https://img-s-msn-com.akamaized.net/poster.jpg"></video>
  </body>
</html>
"""


def _fake_fetch(url: str) -> HttpFetchResult:
    if "archive.org/wayback/available" in url:
        return HttpFetchResult(
            url=url,
            final_url=url,
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(
                {
                    "archived_snapshots": {
                        "closest": {
                            "available": True,
                            "status": "200",
                            "timestamp": "20260808010101",
                            "url": "https://web.archive.org/web/20260808010101/https://www.msn.com/",
                        }
                    }
                }
            ).encode("utf-8"),
        )
    return HttpFetchResult(
        url=url,
        final_url=url,
        status_code=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
        body=HTML.encode("utf-8"),
    )


def _fake_download(url: str, output_path: Path, max_bytes: int) -> HttpFetchResult:
    payload = b"image fixture"
    assert len(payload) <= max_bytes
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    return HttpFetchResult(
        url=url,
        final_url=url,
        status_code=200,
        headers={"Content-Type": "image/jpeg"},
        body=payload,
    )


def test_msn_vertical_validation_writes_local_archive_bundle_and_manifest() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = run_msn_vertical_live_validation(
            output_directory=temp_dir,
            fetcher=_fake_fetch,
            wayback_fetcher=_fake_fetch,
            download_fetcher=_fake_download,
            timestamp_utc="2026-08-08T00:00:00Z",
        )
        root = Path(result.output_directory)
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

        assert result.source_url == DEFAULT_MSN_VERTICAL_URL
        assert result.status_matrix["source_identification"] == STATUS_LIVE_SITE_MANUALLY_TESTED
        assert result.status_matrix["local_web_archive"] == STATUS_LIVE_SITE_MANUALLY_TESTED
        assert result.status_matrix["faithful_screenshot"] == STATUS_BLOCKED
        assert manifest["summary"]["live_actions"]["wayback_submit_performed"] is False
        assert manifest["summary"]["local_web_archive"]["local_web_archive_default"] is True
        assert (root / "local_web_archive" / "msn_article.warc").is_file()
        assert (root / "local_web_archive" / "msn_article.wacz").is_file()
        assert (root / "local_web_archive" / "local_evidence_bundle.zip").is_file()
        assert (root / "downloads" / "fixture.jpg").is_file() or any((root / "downloads").iterdir())

        with zipfile.ZipFile(root / "local_web_archive" / "msn_article.wacz", "r") as bundle:
            assert "datapackage.json" in bundle.namelist()
            assert "archive/msn_article.warc" in bundle.namelist()
        with zipfile.ZipFile(root / "local_web_archive" / "local_evidence_bundle.zip", "r") as bundle:
            assert "article/article_text.txt" in bundle.namelist()
            assert "article/visible_page_outline.txt" in bundle.namelist()
            assert "archive/archive_results.json" in bundle.namelist()


def test_msn_vertical_validation_preserves_query_fragment_and_marks_comments_blocked() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = run_msn_vertical_live_validation(
            output_directory=temp_dir,
            fetcher=_fake_fetch,
            wayback_fetcher=_fake_fetch,
            download_fetcher=_fake_download,
            timestamp_utc="2026-08-08T00:00:00Z",
        )
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

        assert "ocid=edgemobile" in manifest["summary"]["provenance"]["query"]
        assert manifest["summary"]["provenance"]["fragment"] == "comments"
        assert result.canonical_url.endswith("/ar-AA29207o")
        assert result.status_matrix["comments_shadow_dom"] == STATUS_BLOCKED
        assert manifest["summary"]["comments"]["browser_runtime_required"] is True


def test_msn_vertical_validation_action_log_is_hash_chained_and_secret_free() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = run_msn_vertical_live_validation(
            output_directory=temp_dir,
            fetcher=_fake_fetch,
            wayback_fetcher=_fake_fetch,
            download_fetcher=_fake_download,
            timestamp_utc="2026-08-08T00:00:00Z",
        )
        lines = [
            json.loads(line)
            for line in (Path(result.output_directory) / "action_log.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        assert len(lines) >= 6
        for previous, current in zip(lines, lines[1:]):
            assert current["previous_event_hash"] == previous["event_hash"]
        rendered = json.dumps(lines, sort_keys=True).lower()
        assert "cookie" not in rendered
        assert "authorization" not in rendered


def run_self_test() -> None:
    test_msn_vertical_validation_writes_local_archive_bundle_and_manifest()
    test_msn_vertical_validation_preserves_query_fragment_and_marks_comments_blocked()
    test_msn_vertical_validation_action_log_is_hash_chained_and_secret_free()


if __name__ == "__main__":
    run_self_test()
    print("source_msn_vertical_live_validation.py: OK")
