import json
import tempfile
from pathlib import Path

from profile_media_source_package_preview import (
    extract_preserved_youtube_comment_threads,
    format_youtube_comment_threads_for_review_display,
)

from profile_media_youtube_proven_capability_registration_r42go import (
    PROMOTION_NONE,
    ROLE_STATUS_COMPAT,
    R42GO_PASS_STATUS,
    TEXT_DATA_REFERENCE_METRICS,
    YOUTUBE_PROVEN_VIDEO_URL,
    build_live_source_inventory,
    build_msn_comparison_table,
    build_youtube_capability_registrations,
    source_row_summary_url_fields_are_plain,
    validate_youtube_proven_capability_registration,
    write_report,
    _plain_machine_url,
)


EXPECTED_YOUTUBE_MACHINE_URL = "https://" + "www.youtube.com/watch?v=qGNKkvxE61Q"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_plain_machine_url(value: object, label: str) -> None:
    text = str(value or "")
    _assert(text == EXPECTED_YOUTUBE_MACHINE_URL, f"{label} unexpected value: {text!r}")
    _assert(not text.startswith("["), f"{label} starts with markdown bracket: {text!r}")
    _assert("](" not in text, f"{label} contains markdown link syntax: {text!r}")
    _assert(r"]\(" not in text, f"{label} contains escaped markdown link syntax: {text!r}")
    _assert("](" not in text and r"]\(" not in text and not text.startswith("["), f"{label} is markdown-wrapped: {text!r}")


def _capability(capability_id: str):
    return next(item for item in build_youtube_capability_registrations() if item.capability_id == capability_id)


def test_live_repo_symbols_and_source_row_boundary_are_registered() -> None:
    inventory = build_live_source_inventory(".")
    _assert(inventory["all_required_symbols_present"] is True, str(inventory))
    files = inventory["files"]
    _assert("_youtube_comment_source_role_records_from_review_sections" in files["profile_media_source_package_preview.py"]["present_symbols"], str(files))
    _assert("youtube_media_transcript_comment" in files["source_adapters.py"]["present_symbols"], str(files))
    _assert("youtube_comments" in files["capture_controller.py"]["present_symbols"], str(files))


def test_youtube_text_data_and_visual_paths_are_separate() -> None:
    text = _capability("comment_text_capture_proven")
    visual = _capability("screenshot_capture_proven")

    _assert(text.evidence_path == "text_data_path", str(text))
    _assert(visual.evidence_path == "visual_screenshot_path", str(visual))
    _assert("does_not_depend_on_screenshot_expansion" == text.dependency_boundary, str(text))
    _assert("visual_path_separate_from_fast_text_data_path" == visual.dependency_boundary, str(visual))
    _assert(TEXT_DATA_REFERENCE_METRICS["continuationResponses"] == 305, str(TEXT_DATA_REFERENCE_METRICS))
    _assert(TEXT_DATA_REFERENCE_METRICS["continuationErrors"] == 0, str(TEXT_DATA_REFERENCE_METRICS))


def test_thread_indentation_format_is_preserved() -> None:
    comments_text = """
@Parent
1 month ago
Parent text.
Reply

@RevBrettMurphy
1 month ago
Reply text from Brett.
Reply
"""
    threads = extract_preserved_youtube_comment_threads(comments_text, author_handle="@RevBrettMurphy")
    rendered = format_youtube_comment_threads_for_review_display(threads)

    _assert(rendered.startswith("------\nYouTube Comments\n\n@Parent | 1 month ago"), rendered)
    _assert("\n    @RevBrettMurphy | 1 month ago\n    Reply text from Brett." in rendered, rendered)
    _assert("\nReply\n" not in rendered, rendered)


def test_optional_profile_url_and_searchable_html_are_registered_without_forcing_engine_changes() -> None:
    profile = _capability("optional_author_profile_url_export")
    html = _capability("searchable_html_export_capability")
    no_engine = _capability("no_engine_changes")

    _assert("optional" in profile.method_slot, str(profile))
    _assert("author_channel_url_optional" in profile.expected_artifacts, str(profile))
    _assert("future_optional" in html.method_slot, str(html))
    _assert(no_engine.capture_executed_by_r42go is False, str(no_engine))
    _assert("no_live_capture" in no_engine.dependency_boundary, str(no_engine))


def test_msn_comparison_is_reference_only_and_does_not_replace_youtube_format() -> None:
    table = build_msn_comparison_table()
    areas = {row.capability_area for row in table}

    _assert("searchable_html_output" in areas, str(areas))
    _assert("author_profile_or_channel_url" in areas, str(areas))
    _assert(all(row.replaces_youtube_format is False for row in table), str(table))
    _assert(any("V34" in row.msn_reference_strength and "searchBox" in row.msn_reference_strength for row in table), str(table))
    _assert(any("V35" in row.msn_reference_strength and "sidecars" in row.msn_reference_strength for row in table), str(table))


def test_report_preserves_bridge_guardrails_and_plain_urls() -> None:
    report = validate_youtube_proven_capability_registration(".")
    payload = report.to_dict()

    _assert(report.status == R42GO_PASS_STATUS, str(payload["checks"]))
    source_row_summary = payload["source_row_summary"]
    _assert(source_row_summary["canonical_url"] == EXPECTED_YOUTUBE_MACHINE_URL, str(source_row_summary))
    _assert(source_row_summary["raw_url"] == EXPECTED_YOUTUBE_MACHINE_URL, str(source_row_summary))
    _assert(source_row_summary_url_fields_are_plain(source_row_summary), str(source_row_summary))
    for key, value in source_row_summary.items():
        if "url" in key.lower() or key.lower().endswith("path"):
            _assert_plain_machine_url(value, key)
    _assert(payload["source_method_profile_summary"]["profile_id"] == "youtube_media_transcript_comment", str(payload["source_method_profile_summary"]))
    for registration in payload["registrations"]:
        _assert(registration["source_role_bridge_status"] == ROLE_STATUS_COMPAT, str(registration))
        _assert(registration["promotion_status"] == PROMOTION_NONE, str(registration))
        _assert(registration["role_assignment_performed"] is False, str(registration))
        _assert(registration["capture_executed_by_r42go"] is False, str(registration))
        for value in registration.values():
            if isinstance(value, str) and "http" in value:
                _assert(not value.strip().startswith("[") and "](" not in value, value)


def test_plain_machine_url_unwraps_markdown_url_forms() -> None:
    wrapped_same = "[https://www.youtube.com/watch?v=qGNKkvxE61Q](https://www.youtube.com/watch?v=qGNKkvxE61Q)"
    wrapped_named = "[Example](https://www.youtube.com/watch?v=qGNKkvxE61Q&utm_source=test)"
    bracket_only = "[https://www.youtube.com/watch?v=qGNKkvxE61Q]"

    for value in (wrapped_same, wrapped_named, bracket_only):
        plain = _plain_machine_url(value)
        _assert(plain == EXPECTED_YOUTUBE_MACHINE_URL, plain)
        _assert(not plain.startswith("["), plain)
        _assert("](" not in plain, plain)
        _assert(r"]\(" not in plain, plain)

    bad_summary = {"canonical_url": wrapped_same, "raw_url": EXPECTED_YOUTUBE_MACHINE_URL}
    escaped_bad_summary = {"canonical_url": r"[https://www.youtube.com/watch?v=qGNKkvxE61Q]\(https://www.youtube.com/watch?v=qGNKkvxE61Q)", "raw_url": EXPECTED_YOUTUBE_MACHINE_URL}
    _assert(source_row_summary_url_fields_are_plain(bad_summary) is False, str(bad_summary))
    _assert(source_row_summary_url_fields_are_plain(escaped_bad_summary) is False, str(escaped_bad_summary))


def test_written_report_json_source_row_urls_are_plain_machine_fields() -> None:
    report = validate_youtube_proven_capability_registration(".")
    with tempfile.TemporaryDirectory() as tmp:
        output_root = Path(tmp)
        write_report(report, output_root)
        report_path = output_root / "R42GO_YOUTUBE_PROVEN_CAPABILITY_REGISTRATION_REPORT.json"
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    summary = payload["source_row_summary"]
    _assert_plain_machine_url(summary["canonical_url"], "source_row_summary.canonical_url")
    _assert_plain_machine_url(summary["raw_url"], "source_row_summary.raw_url")
    _assert(source_row_summary_url_fields_are_plain(summary), str(summary))


def run_all_tests() -> None:
    test_live_repo_symbols_and_source_row_boundary_are_registered()
    test_youtube_text_data_and_visual_paths_are_separate()
    test_thread_indentation_format_is_preserved()
    test_optional_profile_url_and_searchable_html_are_registered_without_forcing_engine_changes()
    test_msn_comparison_is_reference_only_and_does_not_replace_youtube_format()
    test_report_preserves_bridge_guardrails_and_plain_urls()
    test_plain_machine_url_unwraps_markdown_url_forms()
    test_written_report_json_source_row_urls_are_plain_machine_fields()


if __name__ == "__main__":
    run_all_tests()
    print("profile_media_youtube_proven_capability_registration_r42go_test: PASS")
