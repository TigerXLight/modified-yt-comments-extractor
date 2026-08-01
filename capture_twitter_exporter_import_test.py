import json
import tempfile
import zipfile
from pathlib import Path

from capture_twitter_exporter_import import (
    TWITTER_EXPORTER_IMPORTER_SOURCE,
    TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT,
    TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED,
    build_twitter_exporter_queue_review_item,
    import_twitter_exporter_local_file,
    twitter_exporter_bundle_to_evidence_queue_item,
)
from evidence_item_queue import EvidenceItemRole, EvidenceItemStatus


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_plain_text_import_builds_local_review_bundle_without_live_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(
            Path(tmp) / "tweet.txt",
            """
Author: Example User
Handle: @example
Date: 2026-07-20
URL: https://x.com/example/status/111
Text: First local exported tweet.

Author: Other User
Handle: @other
Date: 2026-07-21
URL: https://twitter.com/other/status/222
Text: Second local exported tweet.
""".strip(),
        )

        bundle = import_twitter_exporter_local_file(source)
        data = bundle.to_dict()

        assert data["source_platform"] == "twitter_x"
        assert data["importer_source"] == TWITTER_EXPORTER_IMPORTER_SOURCE
        assert data["source_kind"] == "local_export"
        assert data["review_status"] == TWITTER_EXPORTER_REVIEW_STATUS_USER_REVIEW_REQUIRED
        assert data["provenance_status"] == TWITTER_EXPORTER_PROVENANCE_USER_SUPPLIED_LOCAL_EXPORT
        assert data["local_file_name"] == "tweet.txt"
        assert data["parsed_record_count"] == 2
        assert data["records"][0]["tweet_id"] == "111"
        assert data["records"][1]["author_handle"] == "other"
        assert data["api_capture_claimed"] is False
        assert data["browser_automation_claimed"] is False
        assert data["extension_automation_claimed"] is False
        assert data["live_verification_claimed"] is False
        assert "api_key" not in json.dumps(data, sort_keys=True)


def test_json_and_jsonl_import_parse_records_deterministically_and_track_missing_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        json_file = Path(tmp) / "tweets.json"
        json_file.write_text(
            json.dumps(
                [
                    {
                        "tweet_id": "333",
                        "text": "JSON tweet.",
                        "username": "json_user",
                        "created_at": "2026-07-22",
                        "url": "https://x.com/json_user/status/333",
                    },
                    {"id": "444", "full_text": "Missing URL JSON tweet."},
                ]
            ),
            encoding="utf-8",
        )
        jsonl_file = _write(
            Path(tmp) / "tweets.jsonl",
            "\n".join(
                (
                    json.dumps({"id_str": "555", "content": "JSONL tweet.", "screen_name": "line_user"}),
                    json.dumps({"text": "JSONL missing id."}),
                )
            ),
        )

        json_bundle = import_twitter_exporter_local_file(json_file)
        jsonl_bundle = import_twitter_exporter_local_file(jsonl_file)

        assert json_bundle.to_dict()["records"][0]["record_id"] == "twitter_x_tweet_333"
        assert json_bundle.to_dict()["records"][1]["tweet_id"] == "444"
        assert "url" in json_bundle.to_dict()["records"][1]["missing_fields"]
        assert jsonl_bundle.parsed_record_count == 2
        assert jsonl_bundle.to_dict()["records"][0]["tweet_id"] == "555"
        assert jsonl_bundle.to_dict() == import_twitter_exporter_local_file(jsonl_file).to_dict()


def test_sanitized_nested_rows_json_shape_maps_exporter_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "rows.json"
        source.write_text(
            json.dumps(
                {
                    "rows": [
                        {
                            "tweetId": "1200",
                            "fullText": "Sanitized nested row tweet.",
                            "screenName": "row_user",
                            "createdAt": "2026-08-01T10:00:00Z",
                            "tweetUrl": "https://x.com/row_user/status/1200",
                            "conversationId": "conversation-1200",
                            "likeCount": "12",
                            "retweetCount": "3",
                            "replyCount": "2",
                            "viewCount": "1,234",
                            "listName": "Synthetic List",
                            "listId": "list-1",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        data = import_twitter_exporter_local_file(source).to_dict()
        record = data["records"][0]

        assert data["parsed_record_count"] == 1
        assert record["record_type"] == "list_item"
        assert record["tweet_id"] == "1200"
        assert record["author_handle"] == "row_user"
        assert record["created_at_text"] == "2026-08-01T10:00:00Z"
        assert record["conversation_id"] == "conversation-1200"
        assert record["like_count"] == 12
        assert record["retweet_count"] == 3
        assert record["reply_count"] == 2
        assert record["view_count"] == 1234
        assert record["list_name"] == "Synthetic List"
        assert record["list_id"] == "list-1"


def test_sanitized_list_and_users_json_shapes_are_supported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        list_file = Path(tmp) / "list.json"
        users_file = Path(tmp) / "users.json"
        list_file.write_text(
            json.dumps(
                {
                    "list": [
                        {
                            "userId": "u-1",
                            "name": "Synthetic User",
                            "screenName": "@synthetic_member",
                            "listTitle": "Observed List Shape",
                            "listId": "list-2",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        users_file.write_text(
            json.dumps({"users": [{"userId": "u-2", "screenName": "only_user"}]}),
            encoding="utf-8",
        )

        list_record = import_twitter_exporter_local_file(list_file).to_dict()["records"][0]
        user_record = import_twitter_exporter_local_file(users_file).to_dict()["records"][0]

        assert list_record["record_type"] == "list_item"
        assert list_record["author_handle"] == "synthetic_member"
        assert list_record["author_display_name"] == "Synthetic User"
        assert list_record["list_name"] == "Observed List Shape"
        assert user_record["record_type"] == "user"
        assert user_record["author_id"] == "u-2"
        assert user_record["author_handle"] == "only_user"


def test_csv_and_tsv_import_handle_quoted_text_and_common_columns() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        csv_file = _write(
            Path(tmp) / "tweet 2.csv",
            'tweet_id,text,username,created_at,url,like_count\n'
            '666,"Quoted text\nwith newline",csv_user,2026-07-23,https://x.com/csv/status/666,"1,234"\n',
        )
        tsv_file = _write(
            Path(tmp) / "tweet.tsv",
            "id_str\tfull_text\tscreen_name\tretweet_count\n777\tTSV tweet.\ttsv_user\t12\n",
        )

        csv_bundle = import_twitter_exporter_local_file(csv_file)
        tsv_bundle = import_twitter_exporter_local_file(tsv_file)

        assert csv_bundle.parsed_record_count == 1
        assert "with newline" in csv_bundle.to_dict()["records"][0]["text"]
        assert csv_bundle.to_dict()["records"][0]["like_count"] == 1234
        assert tsv_bundle.to_dict()["records"][0]["tweet_id"] == "777"
        assert tsv_bundle.to_dict()["records"][0]["retweet_count"] == 12


def test_sanitized_camel_case_csv_export_columns_are_mapped() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        csv_file = _write(
            Path(tmp) / "tweet 2.csv",
            "tweetId,fullText,screenName,createdAt,tweetUrl,listName,listId,viewCount\n"
            '888,"Sanitized CSV row",csv_member,2026-08-01,https://x.com/csv/status/888,List A,list-a,"2,468"\n',
        )

        record = import_twitter_exporter_local_file(csv_file).to_dict()["records"][0]

        assert record["tweet_id"] == "888"
        assert record["text"] == "Sanitized CSV row"
        assert record["author_handle"] == "csv_member"
        assert record["created_at_text"] == "2026-08-01"
        assert record["url"] == "https://x.com/csv/status/888"
        assert record["record_type"] == "list_item"
        assert record["list_name"] == "List A"
        assert record["list_id"] == "list-a"
        assert record["view_count"] == 2468


def test_sanitized_plain_text_separator_shape_parses_multiple_records() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        txt_file = _write(
            Path(tmp) / "tweet.txt",
            "Tweet ID: 901\n"
            "Handle: @first_user\n"
            "Text: First sanitized text\n"
            "URL: https://x.com/first_user/status/901\n"
            "-----\n"
            "Tweet ID: 902\n"
            "Handle: @second_user\n"
            "Text: Second sanitized text\n"
            "URL: https://x.com/second_user/status/902\n",
        )

        data = import_twitter_exporter_local_file(txt_file).to_dict()

        assert data["parsed_record_count"] == 2
        assert [record["tweet_id"] for record in data["records"]] == ["901", "902"]
        assert [record["author_handle"] for record in data["records"]] == ["first_user", "second_user"]


def test_zip_import_parses_supported_members_in_deterministic_order() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "1.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("b/tweets.json", json.dumps([{"id": "900", "text": "Later member."}]))
            archive.writestr("a/tweets.csv", "tweet_id,text,username\n800,Earlier member,csv_user\n")
            archive.writestr("notes/readme.txt", "Text: Plain member\nURL: https://x.com/plain/status/700\n")

        bundle = import_twitter_exporter_local_file(zip_path)
        data = bundle.to_dict()

        assert data["archive_member_count"] == 3
        assert data["parsed_record_count"] == 3
        assert [member["member_name"] for member in data["members"]] == [
            "a/tweets.csv",
            "b/tweets.json",
            "notes/readme.txt",
        ]
        assert [record["tweet_id"] for record in data["records"]] == ["800", "900", "700"]
        assert all(member["sha256"] for member in data["members"])


def test_zip_path_traversal_and_absolute_members_are_rejected() -> None:
    unsafe_names = ("../evil.txt", "/absolute.txt", "C:/temp/evil.txt", "safe/../../evil.txt")
    with tempfile.TemporaryDirectory() as tmp:
        for index, unsafe_name in enumerate(unsafe_names, start=1):
            zip_path = Path(tmp) / f"unsafe-{index}.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr(unsafe_name, "Text: unsafe")
            try:
                import_twitter_exporter_local_file(zip_path)
            except ValueError as exc:
                assert "Unsafe zip" in str(exc)
            else:
                raise AssertionError(f"unsafe member should be rejected: {unsafe_name}")


def test_zip_unsupported_binary_member_is_skipped_with_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "2.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("tweets.jsonl", json.dumps({"id": "1000", "text": "Supported"}) + "\n")
            archive.writestr("media/image.png", b"\x89PNG\r\n")

        bundle = import_twitter_exporter_local_file(zip_path)
        data = bundle.to_dict()

        assert data["parsed_record_count"] == 1
        assert data["skipped_record_count"] == 1
        assert any(member["skipped"] for member in data["members"])
        assert any("Unsupported member skipped: media/image.png" == warning for warning in data["warnings"])


def test_zip_size_and_count_limits_fail_cleanly_without_extraction() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "3.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("one.txt", "Text: one")
            archive.writestr("two.txt", "Text: two")

        try:
            import_twitter_exporter_local_file(zip_path, max_zip_entries=1)
        except ValueError as exc:
            assert "max_zip_entries" in str(exc)
        else:
            raise AssertionError("zip entry count limit should fail")

        try:
            import_twitter_exporter_local_file(zip_path, max_total_uncompressed_bytes=1)
        except ValueError as exc:
            assert "max_total_uncompressed_bytes" in str(exc)
        else:
            raise AssertionError("zip uncompressed-size limit should fail")


def test_queue_review_metadata_is_user_review_required_and_metadata_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = _write(Path(tmp) / "tweet.txt", "Text: Queue review tweet\nURL: https://x.com/a/status/42\n")
        bundle = import_twitter_exporter_local_file(source)
        review_item = build_twitter_exporter_queue_review_item(bundle)
        queue_item = twitter_exporter_bundle_to_evidence_queue_item(bundle)
        review_data = review_item.to_dict()
        notes = json.loads(queue_item.user_notes)

        assert review_data["review_status"] == "USER_REVIEW_REQUIRED"
        assert review_data["provenance_status"] == "USER_SUPPLIED_LOCAL_EXPORT"
        assert review_data["api_capture_claimed"] is False
        assert review_data["browser_automation_claimed"] is False
        assert review_data["extension_automation_claimed"] is False
        assert review_data["archive_provider_result_claimed"] is False
        assert review_data["downloaded_media_claimed"] is False
        assert review_data["screenshot_claimed"] is False
        assert review_data["ocr_claimed"] is False
        assert review_data["automatic_classification"] is False
        assert queue_item.item_role is EvidenceItemRole.MANUAL_EVIDENCE_NOTE
        assert queue_item.item_status is EvidenceItemStatus.NEEDS_REVIEW
        assert queue_item.is_manual_import is True
        assert queue_item.local_path == ""
        assert queue_item.created_at_utc == ""
        assert notes == review_data


def test_unsupported_missing_and_directory_inputs_fail_cleanly() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        unsupported = _write(root / "export.exe", "not supported")
        missing = root / "missing.txt"

        for candidate in (unsupported, missing, root):
            try:
                import_twitter_exporter_local_file(candidate)
            except ValueError:
                pass
            else:
                raise AssertionError(f"candidate should fail: {candidate}")


def run_self_test() -> None:
    test_plain_text_import_builds_local_review_bundle_without_live_claims()
    test_json_and_jsonl_import_parse_records_deterministically_and_track_missing_fields()
    test_sanitized_nested_rows_json_shape_maps_exporter_fields()
    test_sanitized_list_and_users_json_shapes_are_supported()
    test_csv_and_tsv_import_handle_quoted_text_and_common_columns()
    test_sanitized_camel_case_csv_export_columns_are_mapped()
    test_sanitized_plain_text_separator_shape_parses_multiple_records()
    test_zip_import_parses_supported_members_in_deterministic_order()
    test_zip_path_traversal_and_absolute_members_are_rejected()
    test_zip_unsupported_binary_member_is_skipped_with_warning()
    test_zip_size_and_count_limits_fail_cleanly_without_extraction()
    test_queue_review_metadata_is_user_review_required_and_metadata_only()
    test_unsupported_missing_and_directory_inputs_fail_cleanly()


if __name__ == "__main__":
    run_self_test()
    print("Capture Twitter exporter import self-test passed.")
