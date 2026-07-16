from urllib.request import urlopen

from capture_comments import (
    COMMENT_STATUS_VISIBLE,
    CommentRecord,
    extract_comments_from_html,
    merge_comment_records,
)
from capture_fixture_server import CaptureFixtureServer
from capture_status import CAPTURE_STATUS_PARTIAL, CAPTURE_STATUS_SUCCESS, COMPLETENESS_COMPLETE


def test_extract_comments_from_supplied_html() -> None:
    result = extract_comments_from_html(
        """
        <section id="comments">
          <article data-comment-id="c1" data-author="Alice">First comment</article>
          <article data-comment-id="c2" data-author="Bob" data-parent-id="c1" data-depth="1">
            Reply comment
          </article>
        </section>
        """,
        source_url="http://127.0.0.1/comments/static",
    )

    assert result.status == CAPTURE_STATUS_SUCCESS
    assert result.completeness == COMPLETENESS_COMPLETE
    assert [comment.comment_id for comment in result.comments] == ["c1", "c2"]
    assert result.comments[0].author == "Alice"
    assert result.comments[1].parent_id == "c1"
    assert result.comments[1].depth == 1
    assert result.comments[1].text == "Reply comment"
    assert result.comments[1].status == COMMENT_STATUS_VISIBLE
    assert "no fetch" in result.scope


def test_extract_comments_detects_duplicate_ids_and_ignores_scripts() -> None:
    result = extract_comments_from_html(
        """
        <article data-comment-id="c1">Keep this</article>
        <article data-comment-id="c1">Duplicate this</article>
        <script><article data-comment-id="hidden">Hidden</article></script>
        """
    )

    assert [comment.comment_id for comment in result.comments] == ["c1"]
    assert result.duplicate_comment_ids == ("c1",)
    assert "hidden" not in repr(result.to_dict())
    assert any("Duplicate comment IDs" in warning for warning in result.warnings)


def test_extract_comments_reports_empty_html_as_partial() -> None:
    result = extract_comments_from_html("<html><body>No comments here</body></html>")

    assert result.status == CAPTURE_STATUS_PARTIAL
    assert result.comments == ()
    assert "No comment records found" in result.warnings[0]


def test_extract_comments_from_localhost_fixture() -> None:
    with CaptureFixtureServer() as server:
        url = server.url_for_fixture("comments_static")
        with urlopen(url, timeout=5) as response:
            html = response.read().decode("utf-8")

    result = extract_comments_from_html(html, source_url=url)
    assert [comment.text for comment in result.comments] == ["First comment", "Reply comment"]


def test_merge_comment_records_preserves_first_seen_and_updates_last_seen() -> None:
    existing = (
        CommentRecord(comment_id="c1", text="Old", first_seen_ordinal=1, last_seen_ordinal=1),
    )
    new = (
        CommentRecord(comment_id="c1", text="Updated", first_seen_ordinal=2, last_seen_ordinal=5),
        CommentRecord(comment_id="c2", text="New", first_seen_ordinal=3, last_seen_ordinal=3),
    )

    merged = merge_comment_records(existing, new)
    assert [(comment.comment_id, comment.text, comment.first_seen_ordinal, comment.last_seen_ordinal) for comment in merged] == [
        ("c1", "Updated", 1, 5),
        ("c2", "New", 3, 3),
    ]


def run_self_test() -> None:
    test_extract_comments_from_supplied_html()
    test_extract_comments_detects_duplicate_ids_and_ignores_scripts()
    test_extract_comments_reports_empty_html_as_partial()
    test_extract_comments_from_localhost_fixture()
    test_merge_comment_records_preserves_first_seen_and_updates_last_seen()


if __name__ == "__main__":
    run_self_test()
    print("Capture comments self-test passed.")
