from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_twitter_x_media_extraction_r42gt import (
    LOCAL_FIXTURE_COPIED,
    PROMOTION_NONE,
    R42GT_MARKER,
    R42GT_PASS_STATUS,
    REMOTE_NOT_DOWNLOADED,
    REVIEW_METADATA_ONLY,
    TwitterXMediaExtractionOptions,
    build_capability_metadata,
    build_report,
    build_sample_posts,
    machine_url_fields_are_plain,
    sanitize_plain_url,
    url_like_review_strings_are_plain,
    write_report,
    write_twitter_x_media_evidence_package,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _walk_values(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)
    else:
        yield value


def _assert_no_markdown_url_fields(value) -> None:
    _assert(machine_url_fields_are_plain(value), "machine URL fields must be plain")
    for item in _walk_values(value):
        text = str(item or "")
        _assert("](" not in text, f"markdown link syntax leaked: {text}")
        _assert("]\\(" not in text, f"escaped markdown link syntax leaked: {text}")


def test_sanitizer_outputs_plain_x_urls() -> None:
    _assert(
        sanitize_plain_url("[Example](https://twitter.com/BBCr4today/status/2097217541416308845?s=20&utm_source=test)")
        == "https://x.com/BBCr4today/status/2097217541416308845",
        "twitter markdown URL normalized to plain x.com",
    )
    _assert(
        sanitize_plain_url("[https://x.com/examaddaorg?utm_source=test&s=20](https://x.com/examaddaorg?utm_source=test&s=20)")
        == "https://x.com/examaddaorg",
        "markdown wrapped x.com URL normalized",
    )


def test_package_writer_creates_required_layout_and_metadata_only_remote_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture = root / "fixture.bin"
        fixture.write_bytes(b"local fixture\n")
        posts = build_sample_posts(str(fixture))
        package = write_twitter_x_media_evidence_package(
            posts,
            root / "out",
            TwitterXMediaExtractionOptions(account_or_unknown="BBCr4today", capture_timestamp="20260914T000000Z"),
        )
        package_root = Path(package.root_output_path)
        required = [
            package_root / "manifest.json",
            package_root / "media_index.json",
            package_root / "media_index.ndjson",
            package_root / "timeline.ndjson",
            package_root / "timeline.md",
            package_root / "review_strings.txt",
            package_root / "source_info.txt",
            package_root / "posts" / "2097217541416308845" / "post.json",
            package_root / "posts" / "2097217541416308845" / "post.md",
        ]
        _assert(all(path.exists() for path in required), "required package files")
        manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
        media_index = json.loads((package_root / "media_index.json").read_text(encoding="utf-8"))
        _assert(manifest["status"] == R42GT_PASS_STATUS, "manifest status")
        _assert(manifest["promotion_status"] == PROMOTION_NONE, "manifest no promotion")
        _assert(any(row["media_file_status"] == REMOTE_NOT_DOWNLOADED for row in media_index["media"]), "remote metadata-only row")
        _assert(any(row["media_file_status"] == LOCAL_FIXTURE_COPIED and row["sha256"] for row in media_index["media"]), "local fixture copied and hashed")
        _assert(all(row["promotion_status"] == PROMOTION_NONE for row in media_index["media"]), "media no promotion")
        _assert(all(row["review_status"] == REVIEW_METADATA_ONLY for row in media_index["media"]), "metadata review required")
        _assert_no_markdown_url_fields(manifest)
        _assert_no_markdown_url_fields(media_index)
        _assert(url_like_review_strings_are_plain((package_root / "review_strings.txt").read_text(encoding="utf-8").splitlines()), "plain review strings")


def test_capability_metadata_keeps_live_paths_disabled() -> None:
    capability = build_capability_metadata()
    _assert(capability["route_registered"] is True, "route registered")
    _assert(capability["live_capture_implemented_by_r42gt"] is False, "no live capture")
    _assert(capability["browser_or_cdp_network_capture_implemented_by_r42gt"] is False, "no browser network capture")
    _assert(capability["cookie_or_token_access_implemented_by_r42gt"] is False, "no token access")
    _assert(capability["challenge_bypass_implemented_by_r42gt"] is False, "no challenge bypass")
    _assert(capability["media_download_from_x_implemented_by_r42gt"] is False, "no X media download")
    _assert(capability["metadata_candidates_promoted_by_r42gt"] is False, "no metadata promotion")


def test_report_json_reload_has_marker_status_and_plain_machine_urls() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build_report(".", root)
        write_report(report, root)
        payload = json.loads((root / "R42GT_TWITTER_X_MEDIA_EXTRACTION_ROUTE_SCHEMA_REPORT.json").read_text(encoding="utf-8"))
        _assert(payload["marker"] == R42GT_MARKER, "marker")
        _assert(payload["status"] == R42GT_PASS_STATUS, payload["status"])
        _assert(payload["passed"] is True, "passed")
        _assert(payload["capability_metadata"]["live_capture_implemented_by_r42gt"] is False, "report no live capture")
        _assert(payload["capability_metadata"]["media_download_from_x_implemented_by_r42gt"] is False, "report no X download")
        _assert(
            any(
                item["media_file_status"] == LOCAL_FIXTURE_COPIED and item["sha256"]
                for post in payload["sample_posts"]
                for item in post["media_items"]
            ),
            "report sample post mirrors copied fixture media",
        )
        _assert_no_markdown_url_fields(payload)


def test_plain_urls_and_source_role_bridge_compatibility_for_sample_posts() -> None:
    posts = build_sample_posts()
    payloads = [post.to_dict() for post in posts]
    _assert(all(post["source_role_bridge_status"] == "compatible_bridge_not_role_assignment" for post in payloads), "bridge only")
    _assert(all(post["promotion_status"] == PROMOTION_NONE for post in payloads), "post promotion none")
    for post in payloads:
        _assert(post["canonical_post_url"].startswith("https://x.com/"), "plain x post URL")
        _assert(post["canonical_source_url"].startswith("https://x.com/"), "plain x source URL")
        _assert_no_markdown_url_fields(post)


def main() -> None:
    test_sanitizer_outputs_plain_x_urls()
    test_package_writer_creates_required_layout_and_metadata_only_remote_candidates()
    test_capability_metadata_keeps_live_paths_disabled()
    test_report_json_reload_has_marker_status_and_plain_machine_urls()
    test_plain_urls_and_source_role_bridge_compatibility_for_sample_posts()
    print("PASS profile_media_twitter_x_media_extraction_r42gt_test")


if __name__ == "__main__":
    main()
