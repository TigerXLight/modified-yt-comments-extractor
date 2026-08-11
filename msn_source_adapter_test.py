from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from msn_source_adapter import (
    AA27_EXPECTED_MANUAL_COMMENT_COUNT,
    AA27_EXPECTED_V35_ITEMS,
    ACCEPTED_ARTICLE_SCREENSHOT_NAME,
    ACCEPTED_COMMENTS_SCREENSHOT_NAME,
    MSN_MEDIA_SATISFIED,
    MSN_PRODUCTION_READY,
    YORK_ARTICLE_URL,
    YORK_COMMENTS_URL,
    YORK_EXPECTED_COMMENT_COUNT,
    YORK_REQUIRED_IMAGE_IDENTITY,
    YORK_REQUIRED_IMAGE_URL,
    build_msn_url_parts,
    normalize_msn_image_identity,
    production_output_names,
    promote_accepted_screenshot_outputs,
    render_msn_comments_html_export,
    run_msn_closeout_validation,
)
from source_msn_comments_profile_export import build_msn_comments_profile_export


def _write(path: Path, payload: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, bytes):
        path.write_bytes(payload)
    else:
        path.write_text(payload, encoding="utf-8")
    return path


def _png_payload(width: int = 420, height: int = 1200) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x00" * 2048


def _capture_with_count(count: int, *, source_url: str = YORK_COMMENTS_URL) -> dict[str, object]:
    comments = []
    for index in range(1, count + 1):
        cid = f"cid-profile-{index:02d}"
        comments.append(
            {
                "source_comment_id": f"comment-{index:02d}",
                "type": "Parent Comment",
                "author": f"Author {index:02d}",
                "date": "13 Jul",
                "author_profile_url": f"https://www.msn.com/en-gb/community/profile/{cid}?cvid=unit",
                "profile_card_text": f"Author {index:02d} Comments {index} Likes {index + 10} Followers {index + 20}",
                "likes": str(index),
                "dislikes": "0",
                "text": f"Fixture comment body {index}",
                "replies": [],
            }
        )
    return {
        "file": "fixture.json",
        "source_url": source_url,
        "title": "Arrest made after shot fired outside York mosque",
        "sort_filter": "Top",
        "shown_msn_count": count,
        "comments": comments,
    }


def test_msn_url_and_media_identity_normalization() -> None:
    article = build_msn_url_parts(YORK_ARTICLE_URL)
    comments = build_msn_url_parts(YORK_COMMENTS_URL)
    assert article.article_url == YORK_ARTICLE_URL
    assert article.comments_url == YORK_COMMENTS_URL
    assert comments.article_url == YORK_ARTICLE_URL
    assert comments.comments_url == YORK_COMMENTS_URL
    assert comments.target_id == "AA29207o"
    assert normalize_msn_image_identity(YORK_REQUIRED_IMAGE_URL) == YORK_REQUIRED_IMAGE_IDENTITY
    assert normalize_msn_image_identity("AA292lx3.img?w=100") == "AA292lx3.img"


def test_v34_search_ui_and_v35_profile_data_are_in_final_html() -> None:
    export = build_msn_comments_profile_export([_capture_with_count(2)])
    html = render_msn_comments_html_export(export)
    assert "Search comments and replies" in html
    assert "Additional information for search results" in html
    assert "Copy search results" in html
    assert "Download TXT" in html
    assert "Additional information for full export box" in html
    assert "Copy visible TXT export" in html
    assert "Profiles" in html
    assert "Account comments" in html
    assert "Profiles with account stats" in html


def test_normal_output_policy_keeps_diagnostics_debug_only() -> None:
    normal = production_output_names(debug=False)
    debug = production_output_names(debug=True)
    assert "diagnostic_before_internal_loading.png" not in normal
    assert "comments_stitch_segments" not in normal
    assert "diagnostic_before_internal_loading.png" in debug
    assert "comments_stitch_segments" in debug


def test_screenshot_promotion_uses_accepted_names_without_segments() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "screenshots" / "article-top.png", _png_payload(412, 900))
        _write(root / "screenshots" / "full-comments-thread.png", _png_payload(1082, 13362))
        _write(root / "screenshots" / "diagnostic_before_internal_loading.png", b"debug")
        (root / "screenshots" / "comments_stitch_segments").mkdir()
        promoted = promote_accepted_screenshot_outputs(root, debug=False)
        assert Path(promoted["article"]).name == ACCEPTED_ARTICLE_SCREENSHOT_NAME
        assert Path(promoted["comments"]).name == ACCEPTED_COMMENTS_SCREENSHOT_NAME
        assert (root / "screenshots" / ACCEPTED_ARTICLE_SCREENSHOT_NAME).is_file()
        assert (root / "screenshots" / ACCEPTED_COMMENTS_SCREENSHOT_NAME).is_file()
        assert promoted["diagnostics_written"] == "false"


def test_york_and_aa27_count_boundaries_are_distinct() -> None:
    york = build_msn_comments_profile_export([_capture_with_count(YORK_EXPECTED_COMMENT_COUNT, source_url=YORK_COMMENTS_URL)])
    aa27 = build_msn_comments_profile_export([_capture_with_count(AA27_EXPECTED_V35_ITEMS, source_url="https://www.msn.com/en-gb/news/uknews/twelve-arrested-over-terror-threat-at-islamic-festival/ar-AA27OIhw?#comments")])
    assert york.items_captured == 25
    assert aa27.items_captured == 88
    assert AA27_EXPECTED_MANUAL_COMMENT_COUNT == 87
    assert york.source_url != aa27.source_url


def test_closeout_validation_writes_clean_york_report_from_fixture_inputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        capture_path = root / "top.json"
        _write(capture_path, json.dumps(_capture_with_count(YORK_EXPECTED_COMMENT_COUNT), ensure_ascii=False))
        _write(root / "screenshots" / ACCEPTED_ARTICLE_SCREENSHOT_NAME, _png_payload(412, 1400))
        _write(root / "screenshots" / ACCEPTED_COMMENTS_SCREENSHOT_NAME, _png_payload(1082, 13362))
        result = run_msn_closeout_validation(
            target_url=YORK_COMMENTS_URL,
            output_dir=root,
            comments_capture_paths=(capture_path,),
            expected_comment_count=YORK_EXPECTED_COMMENT_COUNT,
            download_media=True,
            media_downloader=lambda _url: b"image-bytes",
        )
        assert result.decision == MSN_PRODUCTION_READY
        assert result.comment_count == YORK_EXPECTED_COMMENT_COUNT
        assert result.expected_comment_count == YORK_EXPECTED_COMMENT_COUNT
        assert result.media_satisfied is True
        assert result.media_required[0]["status"] == MSN_MEDIA_SATISFIED
        assert Path(result.html_export).name == "comments.html"
        assert Path(result.json_export).name == "comments.json"
        assert Path(result.md_export).name == "comments.md"
        assert Path(result.txt_export).name == "comments.txt"
        assert Path(result.profiles_json).name == "profiles.json"
        assert Path(result.profiles_txt).name == "profiles.txt"
        assert "WARNINGS: NONE" in result.final_block()
        assert (root / "msn-closeout-report.json").is_file()
        assert (root / "media" / YORK_REQUIRED_IMAGE_IDENTITY).is_file()


def test_live_capture_wrapper_defaults_to_headless_and_promotes_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        seen: dict[str, object] = {}

        def fake_live_capture_runner(**kwargs):
            seen.update(kwargs)
            out = Path(kwargs["output_dir"])
            _write(out / "screenshots" / "article-top.png", _png_payload(412, 1000))
            _write(out / "screenshots" / "full-comments-thread.png", _png_payload(1082, 13362))
            return SimpleNamespace()

        result = run_msn_closeout_validation(
            target_url=YORK_COMMENTS_URL,
            output_dir=root,
            expected_comment_count=0,
            capture_msn_screenshots=True,
            live_capture_runner=fake_live_capture_runner,
        )
        assert seen["headed"] is False
        assert seen["write_screenshots"] is True
        assert (root / "screenshots" / ACCEPTED_ARTICLE_SCREENSHOT_NAME).is_file()
        assert (root / "screenshots" / ACCEPTED_COMMENTS_SCREENSHOT_NAME).is_file()
        assert "comments_stitch_segments" not in production_output_names(debug=False)
        assert result.article_screenshot.endswith(ACCEPTED_ARTICLE_SCREENSHOT_NAME)
        assert result.comments_screenshot.endswith(ACCEPTED_COMMENTS_SCREENSHOT_NAME)


def run_self_test() -> None:
    test_msn_url_and_media_identity_normalization()
    test_v34_search_ui_and_v35_profile_data_are_in_final_html()
    test_normal_output_policy_keeps_diagnostics_debug_only()
    test_screenshot_promotion_uses_accepted_names_without_segments()
    test_york_and_aa27_count_boundaries_are_distinct()
    test_closeout_validation_writes_clean_york_report_from_fixture_inputs()
    test_live_capture_wrapper_defaults_to_headless_and_promotes_outputs()


if __name__ == "__main__":
    run_self_test()
    print("msn_source_adapter.py: OK")
