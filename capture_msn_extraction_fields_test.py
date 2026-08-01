import json

from capture_live_smoke_plan import (
    MANUAL_ACTION_SCOPE_COMMENTS,
    MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
    MANUAL_ACTION_SCOPE_MEDIA,
    MANUAL_ACTION_SCOPE_WEBPAGE,
    MSN_MANUAL_SMOKE_SOURCE_URL,
    build_msn_article_manual_operator_observation_fixture,
    import_msn_article_manual_operator_observation_fixture,
)
from capture_msn_extraction_fields import (
    MSN_ARTICLE_FIELD_KIND,
    MSN_COMMENTS_FIELD_KIND,
    MSN_EXTRACTION_FIELD_SCHEMA_VERSION,
    extract_msn_article_comment_fields_from_supplied_html,
)


def _article_html() -> str:
    return """
    <html><head><title>MSN Fixture Title</title></head>
    <body>
      <article>
        <h1>MSN article headline</h1>
        <p>MSN article body paragraph.</p>
        <section id="comments"><article data-comment-id="hidden">Hidden comment</article></section>
      </article>
      <aside class="advert">Advertisement text</aside>
    </body></html>
    """


def _comments_html() -> str:
    return """
    <section id="comments" data-scroll-container="true">
      <article data-comment-id="c1" data-author="Reader A" data-thread-id="t1"
        data-posted-at="2026-07-17T12:00:00Z" data-reactions="7"
        data-reply-count="1" data-permalink="/comments/c1">First MSN comment.</article>
      <article data-comment-id="c2" data-author="Reader B" data-parent-id="c1"
        data-depth="1" data-thread-id="t1">Reply MSN comment.</article>
    </section>
    """


def test_msn_article_comment_fields_keep_article_and_comments_separate() -> None:
    bundle = extract_msn_article_comment_fields_from_supplied_html(
        article_html=_article_html(),
        comments_html=_comments_html(),
    )
    data = bundle.to_dict()

    assert data["schema_version"] == MSN_EXTRACTION_FIELD_SCHEMA_VERSION
    assert data["source_url"] == MSN_MANUAL_SMOKE_SOURCE_URL
    assert data["site_label"] == "MSN"
    assert data["adapter_family"] == "msn"
    assert data["article"]["field_kind"] == MSN_ARTICLE_FIELD_KIND
    assert data["comments"]["field_kind"] == MSN_COMMENTS_FIELD_KIND
    assert data["article"]["separated_from_comments"] is True
    assert data["comments"]["separated_from_article"] is True
    assert data["comments"]["article_text_included"] is False
    assert "MSN article body paragraph." in data["article"]["text"]
    assert "First MSN comment" not in data["article"]["text"]
    assert data["comments"]["comment_count"] == 2
    assert data["comments"]["thread_records"][1]["parent_id"] == "c1"
    assert data["comments"]["thread_records"][1]["depth"] == 1
    assert data["comments"]["thread_records"][0]["article_text_included"] is False


def test_msn_extraction_fields_remain_user_review_metadata_only() -> None:
    imports = import_msn_article_manual_operator_observation_fixture()
    bundle = extract_msn_article_comment_fields_from_supplied_html(
        article_html=_article_html(),
        comments_html=_comments_html(),
        manual_observation_imports=imports,
    )
    data = bundle.to_dict()
    rendered = json.dumps(data, sort_keys=True)

    assert data["user_review_required"] is True
    assert data["manual_operator_only"] is True
    assert data["automation_performed"] is False
    assert data["network_actions_performed"] == "none"
    assert data["artifact_files_claimed"] is False
    assert data["article"]["user_review_required"] is True
    assert data["comments"]["user_review_required"] is True
    assert data["manual_observation_scopes"] == [
        MANUAL_ACTION_SCOPE_WEBPAGE,
        MANUAL_ACTION_SCOPE_COMMENTS,
        MANUAL_ACTION_SCOPE_MEDIA,
        MANUAL_ACTION_SCOPE_EXPORT_QUEUE,
    ]
    for forbidden in (
        "LIVE_SITE_MANUALLY_VERIFIED",
        "completed_manually",
        "execution_commands",
        "requests.get",
        "playwright",
        "archivebox",
        "yt-dlp",
        "ffmpeg",
    ):
        assert forbidden not in rendered


def test_msn_extraction_fields_reject_unapproved_url() -> None:
    try:
        extract_msn_article_comment_fields_from_supplied_html(
            article_html=_article_html(),
            comments_html=_comments_html(),
            source_url="https://www.msn.com/",
        )
    except ValueError as exc:
        assert MSN_MANUAL_SMOKE_SOURCE_URL in str(exc)
    else:
        raise AssertionError("non-approved MSN URL should be rejected")


def test_msn_extraction_fields_ignore_rejected_manual_imports() -> None:
    accepted = import_msn_article_manual_operator_observation_fixture()[0]
    rejected_source = build_msn_article_manual_operator_observation_fixture()[0]
    rejected = type(accepted)(
        is_accepted=False,
        errors=("not accepted",),
        observation=rejected_source,
    )
    bundle = extract_msn_article_comment_fields_from_supplied_html(
        article_html=_article_html(),
        comments_html=_comments_html(),
        manual_observation_imports=(rejected, accepted),
    )

    assert bundle.manual_observation_scopes == (MANUAL_ACTION_SCOPE_WEBPAGE,)
    assert bundle.manual_observation_count == 1


def run_self_test() -> None:
    test_msn_article_comment_fields_keep_article_and_comments_separate()
    test_msn_extraction_fields_remain_user_review_metadata_only()
    test_msn_extraction_fields_reject_unapproved_url()
    test_msn_extraction_fields_ignore_rejected_manual_imports()


if __name__ == "__main__":
    run_self_test()
    print("Capture MSN extraction fields self-test passed.")
