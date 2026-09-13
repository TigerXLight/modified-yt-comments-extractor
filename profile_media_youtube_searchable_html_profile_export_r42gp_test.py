from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_youtube_proven_capability_registration_r42go import R42GO_PASS_STATUS, validate_youtube_proven_capability_registration
from profile_media_youtube_searchable_html_profile_export_r42gp import (
    DEFAULT_SAMPLE_VIDEO_URL,
    R42GP_MARKER,
    R42GP_PASS_STATUS,
    all_machine_url_fields_plain,
    build_profile_sidecar_rows,
    html_has_no_remote_script_or_style_urls,
    normalize_comment_records,
    plain_machine_url,
    render_existing_readable_txt_reference,
    render_searchable_comments_html,
    sample_youtube_comment_records,
    write_youtube_searchable_export_surface,
)


EXPECTED_VIDEO_URL = "https://" + "www.youtube.com/watch?v=qGNKkvxE61Q"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_plain_url(value: object, label: str) -> None:
    text = str(value or "")
    _assert(text == EXPECTED_VIDEO_URL, f"{label} unexpected URL: {text!r}")
    _assert(not text.startswith("["), f"{label} starts with markdown bracket: {text!r}")
    _assert("](" not in text, f"{label} contains markdown link syntax: {text!r}")
    _assert(r"]\(" not in text, f"{label} contains escaped markdown link syntax: {text!r}")


def _records():
    return sample_youtube_comment_records()


def test_searchable_html_is_generated_from_static_records_without_remote_assets() -> None:
    records = _records()
    html = render_searchable_comments_html(records, source_video_url=DEFAULT_SAMPLE_VIDEO_URL)

    _assert("<!doctype html>" in html, html[:120])
    _assert('id="searchBox"' in html, html)
    _assert("copySearchResults" in html, html)
    _assert("downloadSearchResults" in html, html)
    _assert("Parent Comment" in html, html)
    _assert("Reply" in html, html)
    _assert("data-depth=\"1\"" in html, html)
    _assert("yt-parent-001" in html and "yt-reply-001" in html, html)
    _assert(html_has_no_remote_script_or_style_urls(html), html)
    _assert("<script src=" not in html.lower(), html)
    _assert("<link" not in html.lower(), html)


def test_existing_readable_txt_indentation_is_preserved_as_separate_artifact() -> None:
    txt = render_existing_readable_txt_reference(_records())

    _assert("YouTube Comments - Readable Evidence Export" in txt, txt)
    _assert("[1] Parent Comment" in txt, txt)
    _assert("\u21b3 Reply" in txt, txt)
    _assert("Parent ID: yt-parent-001" in txt, txt)
    _assert("Indented reply text that remains easy to read in Notepad." in txt, txt)


def test_author_profile_sidecar_is_optional_and_disabled_by_default() -> None:
    records = _records()
    disabled = build_profile_sidecar_rows(records, include_author_profile_urls=False)
    enabled = build_profile_sidecar_rows(records, include_author_profile_urls=True)

    _assert(disabled == (), str(disabled))
    _assert(len(enabled) == 2, str([row.to_dict() for row in enabled]))
    first = enabled[0].to_dict()
    _assert(first["comment_id"] == "yt-parent-001", str(first))
    _assert(first["author_channel_id"] == "UCexampleParent0001", str(first))
    _assert(first["author_channel_url"] == "https://www.youtube.com/channel/UCexampleParent0001", str(first))
    reply = enabled[1].to_dict()
    _assert(reply["url_source"] == "derived_from_stable_youtube_channel_id", str(reply))
    _assert(reply["author_channel_url"] == "https://www.youtube.com/channel/UCreplyExample0002", str(reply))


def test_plain_url_sanitizer_rejects_markdown_machine_fields() -> None:
    wrapped = "[Example](https://www.youtube.com/watch?v=qGNKkvxE61Q&utm_source=test)"
    bracketed = "[https://www.youtube.com/watch?v=qGNKkvxE61Q]"
    escaped = r"[https://www.youtube.com/watch?v=qGNKkvxE61Q]\(https://www.youtube.com/watch?v=qGNKkvxE61Q)"

    for value in (wrapped, bracketed, escaped):
        plain = plain_machine_url(value)
        _assert_plain_url(plain, "plain_machine_url")

    _assert(all_machine_url_fields_plain({"canonical_url": EXPECTED_VIDEO_URL}), "expected plain field accepted")
    _assert(not all_machine_url_fields_plain({"canonical_url": wrapped}), "markdown URL should be rejected")


def test_write_export_surface_creates_html_sidecars_report_and_plain_json_urls() -> None:
    records = _records()
    with tempfile.TemporaryDirectory() as tmp:
        files, report = write_youtube_searchable_export_surface(
            records,
            tmp,
            source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
            include_author_profile_urls=True,
            generated_at="2026-09-14T00:00:00+00:00",
        )
        report_payload = json.loads(Path(files.report_json_path).read_text(encoding="utf-8"))
        manifest_payload = json.loads(Path(files.manifest_path).read_text(encoding="utf-8"))
        html_text = Path(files.searchable_html_path).read_text(encoding="utf-8")
        readable_txt = Path(files.readable_txt_reference_path).read_text(encoding="utf-8")
        sidecar_rows = json.loads(Path(files.profile_sidecar_json_path).read_text(encoding="utf-8"))

    _assert(report.marker == R42GP_MARKER, report.to_dict())
    _assert(report.status == R42GP_PASS_STATUS, report.to_dict())
    _assert(report_payload["status"] == R42GP_PASS_STATUS, report_payload)
    _assert_plain_url(report_payload["canonical_video_url"], "report.canonical_video_url")
    _assert_plain_url(report_payload["source_video_url"], "report.source_video_url")
    _assert(manifest_payload["report"]["status"] == R42GP_PASS_STATUS, manifest_payload)
    _assert("id=\"searchBox\"" in html_text, html_text)
    _assert("Parent Comment" in readable_txt and "\u21b3 Reply" in readable_txt, readable_txt)
    _assert(len(sidecar_rows) == 2, sidecar_rows)
    _assert(all_machine_url_fields_plain(report_payload), json.dumps(report_payload, indent=2))
    _assert(all_machine_url_fields_plain(manifest_payload), json.dumps(manifest_payload, indent=2))


def test_disabled_profile_option_writes_empty_sidecar_without_forcing_urls() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        files, report = write_youtube_searchable_export_surface(
            _records(),
            tmp,
            source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
            include_author_profile_urls=False,
            generated_at="2026-09-14T00:00:00+00:00",
        )
        rows = json.loads(Path(files.profile_sidecar_json_path).read_text(encoding="utf-8"))
    _assert(report.include_author_profile_urls_default is False, report.to_dict())
    _assert(report.include_author_profile_urls_effective is False, report.to_dict())
    _assert(rows == [], str(rows))


def test_youtube_records_with_existing_profile_metadata_are_preserved_without_capture_side_effects() -> None:
    records = normalize_comment_records(
        [
            {
                "comment_id": "existing-profile",
                "author": "Existing Metadata Author",
                "author_channel_id": "UCexistingMetadata",
                "author_channel_url": "https://www.youtube.com/channel/UCexistingMetadata",
                "text": "Existing metadata only; no live fetch.",
            }
        ],
        source_video_url=DEFAULT_SAMPLE_VIDEO_URL,
    )
    sidecars = build_profile_sidecar_rows(records, include_author_profile_urls=True)

    _assert(sidecars[0].author_channel_url == "https://www.youtube.com/channel/UCexistingMetadata", sidecars[0].to_dict())
    _assert(sidecars[0].url_source == "existing_metadata", sidecars[0].to_dict())


def test_r42go_remains_compatible() -> None:
    report = validate_youtube_proven_capability_registration(".")
    _assert(report.status == R42GO_PASS_STATUS, report.to_dict())


def run_all_tests() -> None:
    test_searchable_html_is_generated_from_static_records_without_remote_assets()
    test_existing_readable_txt_indentation_is_preserved_as_separate_artifact()
    test_author_profile_sidecar_is_optional_and_disabled_by_default()
    test_plain_url_sanitizer_rejects_markdown_machine_fields()
    test_write_export_surface_creates_html_sidecars_report_and_plain_json_urls()
    test_disabled_profile_option_writes_empty_sidecar_without_forcing_urls()
    test_youtube_records_with_existing_profile_metadata_are_preserved_without_capture_side_effects()
    test_r42go_remains_compatible()


if __name__ == "__main__":
    run_all_tests()
    print("profile_media_youtube_searchable_html_profile_export_r42gp_test: PASS")
