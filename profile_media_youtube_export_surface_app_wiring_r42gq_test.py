from __future__ import annotations

import json
import tempfile
from pathlib import Path

from evidence_exporter import create_evidence_package
from profile_media_youtube_export_surface_app_wiring_r42gq import (
    DEFAULT_SAMPLE_VIDEO_URL,
    R42GQ_MARKER,
    R42GQ_PASS_STATUS,
    write_sample_existing_evidence_package,
    write_youtube_optional_export_surface,
)
from profile_media_youtube_proven_capability_registration_r42go import R42GO_PASS_STATUS, validate_youtube_proven_capability_registration
from profile_media_youtube_searchable_html_profile_export_r42gp import (
    R42GP_PASS_STATUS,
    all_machine_url_fields_plain,
    html_has_no_remote_script_or_style_urls,
    sample_youtube_comment_records,
)


EXPECTED_VIDEO_URL = "https://" + "www.youtube.com/watch?v=qGNKkvxE61Q"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _comments() -> list[dict[str, object]]:
    flat: list[dict[str, object]] = []

    def add(record: dict[str, object]) -> None:
        item = dict(record)
        replies = item.pop("replies", [])
        item["type"] = "Reply" if int(item.get("depth") or 0) else "Parent Comment"
        item["published_at"] = item.get("published_at") or item.get("publishedAt") or ""
        flat.append(item)
        for reply in replies if isinstance(replies, list) else []:
            if isinstance(reply, dict):
                add(reply)

    for record in sample_youtube_comment_records():
        add(record.to_dict())
    return flat


def test_wiring_generates_searchable_html_sibling_without_profile_sidecars_by_default() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        package_dir = write_sample_existing_evidence_package(Path(tmp) / "package")
        report = write_youtube_optional_export_surface(
            _comments(),
            package_dir,
            source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
            include_searchable_html=True,
            include_author_profile_urls=False,
            generated_at="2026-09-14T00:00:00+00:00",
        )
        html_path = package_dir / "youtube-comments-searchable.html"
        readable_path = package_dir / "comments_readable.txt"
        sidecar_path = package_dir / "youtube-author-profile-sidecar.json"
        report_payload = json.loads((package_dir / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.json").read_text(encoding="utf-8"))
        manifest_payload = json.loads((package_dir / "R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_MANIFEST.json").read_text(encoding="utf-8"))
        _assert(html_path.exists(), str(html_path))
        _assert(readable_path.exists(), str(readable_path))
        _assert(not sidecar_path.exists(), "profile sidecar should not be forced by default")
        readable_text = readable_path.read_text(encoding="utf-8")
        html_text = html_path.read_text(encoding="utf-8")

    _assert(report.marker == R42GQ_MARKER, report.to_dict())
    _assert(report.status == R42GQ_PASS_STATUS, report.to_dict())
    _assert("YouTube Comments - Readable Evidence Export" in readable_text, readable_text)
    _assert("Parent Comment" in readable_text, readable_text)
    _assert("Reply" in readable_text, readable_text)
    _assert('id="searchBox"' in html_text, html_text)
    _assert(html_has_no_remote_script_or_style_urls(html_text), html_text)
    _assert(report_payload["include_author_profile_urls_default"] is False, report_payload)
    _assert(report_payload["include_author_profile_urls_effective"] is False, report_payload)
    _assert(report_payload["source_video_url"] == EXPECTED_VIDEO_URL, report_payload)
    _assert(manifest_payload["export_surface_version"], manifest_payload)
    _assert(all_machine_url_fields_plain(report_payload), json.dumps(report_payload, indent=2))
    _assert(all_machine_url_fields_plain(manifest_payload), json.dumps(manifest_payload, indent=2))


def test_enabling_profile_urls_writes_optional_sidecars_from_existing_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        package_dir = write_sample_existing_evidence_package(Path(tmp) / "package")
        report = write_youtube_optional_export_surface(
            _comments(),
            package_dir,
            source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
            include_searchable_html=True,
            include_author_profile_urls=True,
            generated_at="2026-09-14T00:00:00+00:00",
        )
        rows = json.loads((package_dir / "youtube-author-profile-sidecar.json").read_text(encoding="utf-8"))
        csv_text = (package_dir / "youtube-author-profile-sidecar.csv").read_text(encoding="utf-8-sig")
        sidecar_html = (package_dir / "youtube-author-profile-sidecar.html").read_text(encoding="utf-8")

    _assert(report.status == R42GQ_PASS_STATUS, report.to_dict())
    _assert(report.include_author_profile_urls_effective is True, report.to_dict())
    _assert(len(rows) == 2, str(rows))
    _assert(rows[0]["comment_id"] == "yt-parent-001", str(rows))
    _assert(rows[0]["author_channel_id"] == "UCexampleParent0001", str(rows))
    _assert(rows[0]["author_channel_url"] == "https://www.youtube.com/channel/UCexampleParent0001", str(rows))
    _assert(rows[1]["url_source"] == "derived_from_stable_youtube_channel_id", str(rows))
    _assert("comment_id,parent_id,thread_id" in csv_text, csv_text)
    _assert("YouTube author profile/channel URL sidecar" in sidecar_html, sidecar_html)
    _assert(all_machine_url_fields_plain({"sidecars": rows}), str(rows))


def test_evidence_package_default_output_is_unchanged_and_optional_hook_adds_siblings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        default_package = Path(
            create_evidence_package(
                output_parent=tmp,
                metadata=[{"title": "R42GQ Default"}],
                comments=_comments(),
                spam=[],
                screenshots=[],
                source_urls=[DEFAULT_SAMPLE_VIDEO_URL],
                app_version="test",
                settings={},
            )
        )
        optional_package = Path(
            create_evidence_package(
                output_parent=tmp,
                metadata=[{"title": "R42GQ Optional"}],
                comments=_comments(),
                spam=[],
                screenshots=[],
                source_urls=[DEFAULT_SAMPLE_VIDEO_URL],
                app_version="test",
                settings={},
                include_youtube_searchable_html=True,
                include_author_profile_urls=True,
            )
        )

        _assert((default_package / "comments_readable.txt").exists(), str(default_package))
        _assert((default_package / "comments.csv").exists(), str(default_package))
        _assert(not (default_package / "youtube-comments-searchable.html").exists(), "default evidence export should be unchanged")
        _assert((optional_package / "comments_readable.txt").exists(), str(optional_package))
        _assert((optional_package / "comments.csv").exists(), str(optional_package))
        _assert((optional_package / "youtube-comments-searchable.html").exists(), str(optional_package))
        _assert((optional_package / "youtube-author-profile-sidecar.json").exists(), str(optional_package))
        source_info = (optional_package / "source_info.txt").read_text(encoding="utf-8")
    _assert("R42GQ YouTube Optional Export Surface" in source_info, source_info)
    _assert("Screenshots remain separate attached visual evidence" in source_info, source_info)


def test_screenshots_remain_separate_and_not_required_for_text_export() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        shot = Path(tmp) / "attached.png"
        shot.write_bytes(b"not a real png but enough for copy test")
        package = Path(
            create_evidence_package(
                output_parent=tmp,
                metadata=[{"title": "R42GQ Screenshot"}],
                comments=_comments(),
                spam=[],
                screenshots=[str(shot)],
                source_urls=[DEFAULT_SAMPLE_VIDEO_URL],
                app_version="test",
                settings={},
                include_youtube_searchable_html=True,
            )
        )
        _assert((package / "screenshots" / "page_screenshot_001.png").exists(), str(package))
        _assert((package / "youtube-comments-searchable.html").exists(), str(package))
        _assert(not (package / "youtube-author-profile-sidecar.json").exists(), "profile URLs remain disabled by default")


def test_r42go_and_r42gp_compatibility_contracts_remain_green() -> None:
    r42go = validate_youtube_proven_capability_registration(".")
    _assert(r42go.status == R42GO_PASS_STATUS, r42go.to_dict())
    # R42GP status is also exercised through the standalone self-test; assert the
    # pass-status constant here so accidental import drift is visible.
    _assert(R42GP_PASS_STATUS == "PASS_R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_URL_EXPORT_SURFACE", R42GP_PASS_STATUS)


def run_all_tests() -> None:
    test_wiring_generates_searchable_html_sibling_without_profile_sidecars_by_default()
    test_enabling_profile_urls_writes_optional_sidecars_from_existing_metadata()
    test_evidence_package_default_output_is_unchanged_and_optional_hook_adds_siblings()
    test_screenshots_remain_separate_and_not_required_for_text_export()
    test_r42go_and_r42gp_compatibility_contracts_remain_green()


if __name__ == "__main__":
    run_all_tests()
    print("profile_media_youtube_export_surface_app_wiring_r42gq_test: PASS")
