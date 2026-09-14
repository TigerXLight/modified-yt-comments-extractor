from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

from evidence_exporter import create_evidence_package
from main import App
from profile_media_youtube_comment_sort_spam_review_r42gs import (
    R42GS_PASS_STATUS,
    YouTubeCommentSortSpamSettings,
    collect_youtube_comment_sort_spam_settings_from_vars,
    generate_r42gs_report,
    normalize_youtube_comment_sort_order,
    normalize_youtube_spam_handling,
)

class FakeVar:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value

def _assert(condition: bool, detail: object = "") -> None:
    if not condition:
        raise AssertionError(detail)

def test_defaults_and_validation() -> None:
    defaults = YouTubeCommentSortSpamSettings()
    _assert(defaults.youtube_comment_sort_order == "newest", defaults)
    _assert(defaults.youtube_spam_handling == "review", defaults)
    _assert(defaults.filter_spam is True, defaults)
    _assert(defaults.api_comment_order == "time", defaults)
    _assert(defaults.sort_by_value_for_engine == "Date (Newest)", defaults)
    _assert(normalize_youtube_comment_sort_order("Date (Newest)") == "newest")
    _assert(normalize_youtube_comment_sort_order("Newest / Date") == "newest")
    _assert(normalize_youtube_comment_sort_order("Likes") == "top")
    _assert(normalize_youtube_comment_sort_order("Date (Oldest)") == "oldest")
    try:
        normalize_youtube_comment_sort_order("unsupported sort")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid sort was accepted")
    _assert(normalize_youtube_spam_handling("Review suspected spam separately") == "review")
    _assert(normalize_youtube_spam_handling("", filter_spam=True) == "review")
    _assert(normalize_youtube_spam_handling("", filter_spam=False) == "include_inline")

def test_collect_from_vars_and_source_info_settings() -> None:
    settings = collect_youtube_comment_sort_spam_settings_from_vars(FakeVar("Likes"), FakeVar(True))
    _assert(settings.youtube_comment_sort_order == "top", settings)
    _assert(settings.youtube_spam_handling == "review", settings)
    payload = settings.to_source_info_settings()
    for key in ("youtube_comment_sort_order", "youtube_spam_handling", "youtube_spam_review_default", "spam_review_default", "default_preserves_existing_sort", "newest_sort_supported_or_blocked", "no_capture_executed_by_r42gs"):
        _assert(key in payload, payload)
    _assert(payload["youtube_comment_sort_api_order"] == "relevance", payload)
    _assert(payload["youtube_spam_review_default"] is True, payload)
    _assert(payload["spam_review_default"] is True, payload)

def test_main_plumbing_is_static_and_visible() -> None:
    init_source = inspect.getsource(App.__init__)
    filters_source = inspect.getsource(App._create_filters_section)
    fetch_source = inspect.getsource(App.start_fetching)
    save_source = inspect.getsource(App._save_settings)
    load_source = inspect.getsource(App._load_settings)
    export_source = inspect.getsource(App.export_evidence_folder)
    _assert("youtube_spam_handling_var = ctk.StringVar" in init_source, init_source)
    _assert("ctk.BooleanVar(value=True)" in filters_source, filters_source)
    _assert("Review suspected spam separately" in filters_source, filters_source)
    _assert("spam_comments.csv/readable exports" in filters_source, filters_source)
    _assert("youtube_comment_sort_spam_settings.filter_spam" in fetch_source, fetch_source)
    _assert("youtube_comment_sort_spam_settings.sort_by_value_for_engine" in fetch_source, fetch_source)
    _assert("YouTube comment sort order" in fetch_source, fetch_source)
    _assert("YouTube spam handling" in fetch_source, fetch_source)
    _assert("youtube_spam_handling=" in save_source, save_source)
    _assert("spam_handling_value=getattr(settings, \"youtube_spam_handling\", \"\")" in load_source, load_source)
    _assert("settings.update(youtube_comment_sort_spam_settings.to_source_info_settings())" in export_source, export_source)

def test_evidence_exporter_keeps_spam_review_artifact() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        package = Path(create_evidence_package(
            output_parent=tmp,
            metadata=[{"title": "R42GS Spam Review", "video_id": "abc123"}],
            comments=[{"id": "c1", "author": "Clean", "text": "ordinary comment", "published_at": "2026-09-14T00:00:00Z", "likes": 1, "type": "Parent Comment"}],
            spam=[{"id": "s1", "author": "Flagged", "text": "visit http://example.invalid", "published_at": "2026-09-14T00:00:01Z", "likes": 0, "type": "Parent Comment", "spam_reason": "Contains External Link"}],
            screenshots=[],
            source_urls=["https://www.youtube.com/watch?v=abc123"],
            app_version="test",
            settings=YouTubeCommentSortSpamSettings().to_source_info_settings(),
        ))
        _assert((package / "comments_readable.txt").exists(), package)
        _assert((package / "comments.csv").exists(), package)
        _assert((package / "spam_comments.csv").exists(), package)
        source_info = (package / "source_info.txt").read_text(encoding="utf-8")
        _assert("youtube_comment_sort_order" in source_info, source_info)
        _assert("youtube_spam_handling" in source_info, source_info)

def test_generate_report() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = generate_r42gs_report(".", tmp)
        _assert(report["status"] == R42GS_PASS_STATUS, report)
        _assert(report["passed"] is True, report)
        _assert(report["youtube_comment_sort_order"] == "newest", report)
        _assert(report["youtube_spam_handling"] == "review", report)
        _assert(report["spam_review_default"] is True, report)
        _assert(report["no_capture_executed_by_r42gs"] is True, report)
        report_path = Path(tmp) / "R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_REPORT.json"
        sample_path = Path(tmp) / "R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_DEFAULTS_SAMPLE.json"
        _assert(report_path.exists(), tmp)
        _assert(sample_path.exists(), tmp)
        reloaded = json.loads(report_path.read_text(encoding="utf-8"))
        _assert(reloaded["status"] == R42GS_PASS_STATUS, reloaded)
        _assert(reloaded["youtube_comment_sort_order"] == "newest", reloaded)
        _assert(reloaded["youtube_spam_handling"] == "review", reloaded)
        _assert(reloaded["spam_review_default"] is True, reloaded)
        _assert(reloaded["no_capture_executed_by_r42gs"] is True, reloaded)
        _assert("](" not in json.dumps(reloaded), reloaded)

def run_self_test() -> None:
    test_defaults_and_validation()
    test_collect_from_vars_and_source_info_settings()
    test_main_plumbing_is_static_and_visible()
    test_evidence_exporter_keeps_spam_review_artifact()
    test_generate_report()

if __name__ == "__main__":
    run_self_test()
    print("profile_media_youtube_comment_sort_spam_review_r42gs_test: PASS")
