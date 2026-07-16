from urllib.request import urlopen

from capture_comments import (
    COMMENT_ROUTE_CHALLENGE,
    COMMENT_ROUTE_CLOSED_SHADOW_PAYLOAD,
    COMMENT_ROUTE_CURSOR,
    COMMENT_ROUTE_ENCODED_STATE,
    COMMENT_ROUTE_IFRAME,
    COMMENT_ROUTE_INFINITE_SCROLL,
    COMMENT_ROUTE_LOAD_MORE,
    COMMENT_ROUTE_LOGIN_REQUIRED,
    COMMENT_ROUTE_NESTED_CONTAINER,
    COMMENT_ROUTE_OPEN_SHADOW,
    COMMENT_ROUTE_VIRTUALIZED,
    COMMENT_STATUS_DELETED,
    COMMENT_STATUS_VISIBLE,
    CommentRecord,
    extract_comments_from_html,
    extract_comments_from_html_sequence,
    merge_comment_records,
)
from capture_article import extract_article_text_from_html
from capture_fixture_server import CaptureFixtureServer
from capture_fixture_server import fixture_by_id
from capture_status import (
    CAPTURE_STATUS_CHALLENGE_REQUIRES_USER,
    CAPTURE_STATUS_LOGIN_REQUIRED,
    CAPTURE_STATUS_PARTIAL,
    CAPTURE_STATUS_SUCCESS,
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL_LOGIN_REQUIRED,
    COMPLETENESS_PARTIAL_VIRTUALIZED,
)


def test_extract_comments_from_supplied_html() -> None:
    result = extract_comments_from_html(
        """
        <section id="comments">
          <article data-comment-id="c1" data-author="Alice" data-thread-id="t1"
            data-posted-at="2026-07-16T10:00:00Z" data-reactions="5"
            data-reply-count="1" data-permalink="/comments/c1">First comment</article>
          <article data-comment-id="c2" data-author="Bob" data-parent-id="c1" data-depth="1"
            data-thread-id="t1">
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
    assert result.comments[0].thread_id == "t1"
    assert result.comments[0].posted_at == "2026-07-16T10:00:00Z"
    assert result.comments[0].reaction_count == 5
    assert result.comments[0].reply_count == 1
    assert result.comments[0].permalink == "/comments/c1"
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
    assert result.comments[1].parent_id == "c1"


def test_extract_comments_handles_load_more_cursor_and_infinite_sequence() -> None:
    load_more = fixture_by_id("comments_load_more").body
    cursor = fixture_by_id("comments_cursor").body
    infinite = fixture_by_id("comments_infinite").body

    result = extract_comments_from_html_sequence((load_more, cursor, infinite), source_url="http://fixture/comments")

    assert result.status == CAPTURE_STATUS_SUCCESS
    assert result.incremental_batches == 3
    assert [comment.comment_id for comment in result.comments] == ["lm1", "cur1", "inf1", "inf2"]
    assert COMMENT_ROUTE_LOAD_MORE in result.capture_routes
    assert COMMENT_ROUTE_CURSOR in result.capture_routes
    assert COMMENT_ROUTE_INFINITE_SCROLL in result.capture_routes
    assert result.cursor == "end"
    assert result.stop_reason == "no-new-id"


def test_extract_comments_handles_frame_shadow_nested_and_encoded_fixture_routes() -> None:
    cases = {
        "comments_iframe": COMMENT_ROUTE_IFRAME,
        "comments_shadow_open": COMMENT_ROUTE_OPEN_SHADOW,
        "comments_shadow_closed": COMMENT_ROUTE_CLOSED_SHADOW_PAYLOAD,
        "comments_scroll_container": COMMENT_ROUTE_NESTED_CONTAINER,
        "comments_encoded": COMMENT_ROUTE_ENCODED_STATE,
    }

    for fixture_id, expected_route in cases.items():
        result = extract_comments_from_html(fixture_by_id(fixture_id).body)
        assert expected_route in result.capture_routes
        if fixture_id != "comments_iframe":
            assert result.comments


def test_extract_comments_handles_virtualized_disappearing_and_deleted_states() -> None:
    virtualized = extract_comments_from_html(fixture_by_id("comments_virtualized").body)
    disappearing = extract_comments_from_html(fixture_by_id("comments_disappearing").body)

    assert virtualized.completeness == COMPLETENESS_PARTIAL_VIRTUALIZED
    assert virtualized.duplicate_comment_ids == ("visible-1",)
    assert [comment.comment_id for comment in virtualized.comments] == ["visible-1", "visible-2"]
    assert disappearing.capture_routes == ("disappearing",)
    assert disappearing.comments[0].status == COMMENT_STATUS_DELETED


def test_extract_comments_reports_login_and_challenge_without_bypass() -> None:
    login = extract_comments_from_html(fixture_by_id("comments_login_required").body)
    challenge = extract_comments_from_html(fixture_by_id("comments_challenge").body)

    assert login.status == CAPTURE_STATUS_LOGIN_REQUIRED
    assert login.completeness == COMPLETENESS_PARTIAL_LOGIN_REQUIRED
    assert login.login_required is True
    assert COMMENT_ROUTE_LOGIN_REQUIRED in login.capture_routes
    assert any("bypass was not attempted" in warning for warning in login.warnings)
    assert challenge.status == CAPTURE_STATUS_CHALLENGE_REQUIRES_USER
    assert challenge.challenge_required is True
    assert COMMENT_ROUTE_CHALLENGE in challenge.capture_routes


def test_comment_regions_are_not_silently_mixed_into_article_text() -> None:
    result = extract_article_text_from_html(
        """
        <article><h1>Article title</h1><p>Article body.</p></article>
        <section id="comments"><article data-comment-id="c1">Comment text</article></section>
        """
    )

    assert "Article body" in result.text
    assert "Comment text" not in result.text
    assert any("Comment/discussion regions were excluded" in warning for warning in result.warnings)


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
    test_extract_comments_handles_load_more_cursor_and_infinite_sequence()
    test_extract_comments_handles_frame_shadow_nested_and_encoded_fixture_routes()
    test_extract_comments_handles_virtualized_disappearing_and_deleted_states()
    test_extract_comments_reports_login_and_challenge_without_bypass()
    test_comment_regions_are_not_silently_mixed_into_article_text()
    test_merge_comment_records_preserves_first_seen_and_updates_last_seen()


if __name__ == "__main__":
    run_self_test()
    print("Capture comments self-test passed.")
