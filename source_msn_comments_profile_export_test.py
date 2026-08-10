from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from source_local_webpage_viewer import write_local_webpage_viewer
from source_msn_comments_profile_export import (
    MSN_COMMENTS_PROFILE_EXPORTER,
    MSN_DELETED_PLACEHOLDER_TEXT,
    build_msn_comments_profile_export,
    build_offline_article_comments_integration_manifest,
    canonicalize_profile_url,
    extract_profile_cid,
    render_msn_comments_html,
    render_msn_comments_text,
    write_msn_comments_profile_exports,
)


SOURCE_URL = (
    "https://www.msn.com"
    "/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"
    "?ocid=edgemobile&PC=EMMX01#comments"
)


def _sanitized_captures() -> list[dict[str, object]]:
    pete_profile = "https://www.msn.com/en-gb/community/profile/cid-a6e6cba6625dfecb?ocid=unit#card"
    alex_profile = "https://www.msn.com/en-gb/community/profile/cid-profilealex?cvid=unit"
    return [
        {
            "file": "top.json",
            "source_url": SOURCE_URL,
            "title": "Arrest made after shot fired outside York mosque",
            "sort_filter": "Top",
            "shown_msn_count": 4,
            "comments": [
                {
                    "source_comment_id": "pete-parent",
                    "type": "Parent Comment",
                    "author": "Pete S",
                    "date": "13 Jul",
                    "author_profile_url": pete_profile,
                    "author_profile_url_raw": pete_profile,
                    "profile_card_text": "Pete S Comments 704 Likes 4,920 Followers 1",
                    "likes": "69",
                    "dislikes": "4",
                    "text": "Stand against hatred but maybe only one way Shabana?\nSuccessive Governments have brought this upon the country.",
                    "replies": [
                        {
                            "source_comment_id": "alex-reply",
                            "type": "Reply",
                            "author": "Alex Example",
                            "date": "13 Jul",
                            "author_profile_url": alex_profile,
                            "likes": "2",
                            "dislikes": "0",
                            "text": "A nested reply with profile stats embedded elsewhere.",
                            "_header_for_hover": {
                                "user": {
                                    "id": "cid-profilealex",
                                    "primaryName": "Alex Example",
                                    "commentSummary": {"totalCount": "12"},
                                    "reactionSummary": {"totalCount": "34"},
                                    "followSummary": {
                                        "subFollowSummaries": [
                                            {"type": "Followers", "totalCount": "5"},
                                        ]
                                    },
                                }
                            },
                        }
                    ],
                },
                {
                    "source_comment_id": "deleted-parent",
                    "type": "Parent Comment",
                    "author": "Unknown",
                    "date": "13 Jul",
                    "text": MSN_DELETED_PLACEHOLDER_TEXT,
                    "deleted_placeholder": True,
                    "likes": "",
                    "dislikes": "",
                    "replies": [],
                },
            ],
        },
        {
            "file": "newest.json",
            "source_url": SOURCE_URL,
            "title": "Arrest made after shot fired outside York mosque",
            "sort_filter": "Newest",
            "shown_msn_count": 4,
            "comments": [
                {
                    "source_comment_id": "alex-parent",
                    "type": "Parent Comment",
                    "author": "Alex Example",
                    "date": "14 Jul",
                    "author_profile_url": "https://www.msn.com/en-gb/community/profile/cid-profilealex",
                    "text": "Same profile appears again and should receive propagated account stats.",
                    "likes": "7",
                    "dislikes": "1",
                    "replies": [],
                },
                {
                    "source_comment_id": "pete-parent",
                    "type": "Parent Comment",
                    "author": "Pete S",
                    "date": "13 Jul",
                    "author_profile_url": "https://www.msn.com/en-gb/community/profile/cid-a6e6cba6625dfecb",
                    "text": "Stand against hatred but maybe only one way Shabana?\nSuccessive Governments have brought this upon the country.",
                    "likes": "69",
                    "dislikes": "4",
                    "replies": [],
                },
            ],
        },
    ]


def test_profile_url_canonicalization_and_cid_extraction() -> None:
    raw = "https://www.msn.com/en-gb/community/profile/cid-a6e6cba6625dfecb?cvid=abc#x"
    assert canonicalize_profile_url(raw) == "https://www.msn.com/en-gb/community/profile/cid-a6e6cba6625dfecb"
    assert extract_profile_cid(raw) == "cid-a6e6cba6625dfecb"


def test_nested_comments_deleted_placeholders_votes_and_profile_propagation() -> None:
    export = build_msn_comments_profile_export(_sanitized_captures())

    assert export.exporter == MSN_COMMENTS_PROFILE_EXPORTER
    assert export.parents_captured == 3
    assert export.items_captured == 4
    assert export.deleted_placeholders == 1
    assert export.items_with_comment_votes == 3
    assert len(export.profiles) == 2
    assert export.profiles_with_account_stats == 2

    pete = export.comments[0]
    assert pete["human_id"] == "C0001"
    assert pete["likes"] == "69"
    assert pete["dislikes"] == "4"
    assert pete["account_comments"] == "704"
    assert pete["account_likes"] == "4920"
    assert pete["account_followers"] == "1"
    assert pete["replies"][0]["account_comments"] == "12"
    assert pete["replies"][0]["account_likes"] == "34"
    assert pete["replies"][0]["account_followers"] == "5"

    alex_parent = [item for item in export.comments if item["source_comment_id"] == "alex-parent"][0]
    assert alex_parent["account_comments"] == "12"
    assert alex_parent["account_likes"] == "34"
    assert alex_parent["account_followers"] == "5"

    deleted = [item for item in export.comments if item["deleted_placeholder"]][0]
    assert MSN_DELETED_PLACEHOLDER_TEXT in deleted["text"]


def test_html_plain_copy_and_additional_info_rules() -> None:
    export = build_msn_comments_profile_export(_sanitized_captures())
    compact = render_msn_comments_text(export, full=False)
    full = render_msn_comments_text(export, full=True)
    html = render_msn_comments_html(export)

    assert "[1] Parent Comment C0001" not in compact
    assert "Comment label: [1] Parent Comment C0001" in full
    assert "id=\"searchBox\"" in html
    assert "value=\"all\">all words" in html
    assert "value=\"any\">any word" in html
    assert "id=\"searchAdditionalInfo\"" in html
    assert "id=\"fullAdditionalInfo\"" in html
    assert "copySearchPlain" in html
    assert "downloadSearchJson" in html
    assert "<textarea id=\"fullExportBox\"" in html
    assert "Comment label: [1] Parent Comment C0001" in html
    assert "Stand against hatred" in html


def test_export_files_and_article_archive_integration_manifest() -> None:
    export = build_msn_comments_profile_export(_sanitized_captures())
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article_dir = root / "article_archive"
        article_dir.mkdir()
        for name in (
            "rendered-page.html",
            "rendered-page.warc.gz",
            "archive.viewable-live-capture.wacz",
            "capture-manifest.json",
            "validation.json",
        ):
            (article_dir / name).write_text(name, encoding="utf-8")
        local_viewer = article_dir / "local_viewer"
        local_viewer.mkdir()
        (local_viewer / "open_local_viewer.cmd").write_text("@echo off\r\n", encoding="utf-8")

        files = write_msn_comments_profile_exports(
            export,
            article_dir,
            base_name="msn-comments-v35-profile-stats-test",
            generated_at="2026-08-10T00:00:00+00:00",
        )
        manifest = build_offline_article_comments_integration_manifest(
            article_archive_dir=article_dir,
            comments_export_files=files,
        )

        for path in files.to_dict().values():
            if str(path).endswith((".json", ".txt", ".md", ".html", ".csv")):
                assert Path(path).is_file()
        assert manifest["offline_article_archive_preserved"] is True
        assert manifest["article_archive_files"]["rendered-page.html"]["present"] is True
        assert manifest["article_archive_files"]["rendered-page.warc.gz"]["present"] is True
        assert manifest["article_archive_files"]["archive.viewable-live-capture.wacz"]["present"] is True
        payload = json.loads(Path(files.json_path).read_text(encoding="utf-8"))
        assert payload["parents_captured"] == 3
        assert payload["profiles_with_account_stats"] == 2
        csv_rows = list(csv.DictReader(Path(files.profiles_csv_path).open(encoding="utf-8-sig")))
        assert {row["profile_cid"] for row in csv_rows} == {"cid-a6e6cba6625dfecb", "cid-profilealex"}

        viewer = write_local_webpage_viewer(capture_output_dir=article_dir, source_url=SOURCE_URL)
        viewer_html = Path(viewer.index_path).read_text(encoding="utf-8")
        assert "MSN comments/profile export: msn-comments-v35-profile-stats-test.json" in viewer_html
        assert "msn-comments-v35-profile-stats-test-profiles.csv" in viewer_html


def run_self_test() -> None:
    test_profile_url_canonicalization_and_cid_extraction()
    test_nested_comments_deleted_placeholders_votes_and_profile_propagation()
    test_html_plain_copy_and_additional_info_rules()
    test_export_files_and_article_archive_integration_manifest()


if __name__ == "__main__":
    run_self_test()
    print("source_msn_comments_profile_export.py: OK")
