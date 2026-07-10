from capture_options import CAPTURE_ARCHIVE_CHECK, CAPTURE_COMMENTS
from source_capture_plan import (
    PLAN_STATUS_READY,
    PLAN_STATUS_UNSUPPORTED_SOURCE,
    build_source_capture_plan,
)


def run_self_test() -> None:
    plan = build_source_capture_plan(
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
        source_label="YouTube clip",
        title="Nicolas Cage ZoneX trailer",
        selected_capture_options=[
            "comments",
            "archive_check",
            "unknown_option",
            "comments",
        ],
        user_terms=["Nyxara", "Freckelston"],
    )

    assert plan.status == PLAN_STATUS_READY
    assert plan.source_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s"
    assert plan.normalized_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert plan.source_id == "dQw4w9WgXcQ"
    assert plan.adapter_name == "youtube"
    assert plan.adapter_display_name == "YouTube"
    assert plan.selected_capture_options == (CAPTURE_COMMENTS, CAPTURE_ARCHIVE_CHECK)
    assert plan.unknown_capture_options == ("unknown_option",)
    assert plan.duplicate_capture_options == (CAPTURE_COMMENTS,)
    assert (
        "Unknown capture options ignored: unknown_option",
        "Duplicate capture options ignored: comments",
    ) == plan.warnings
    assert plan.context_result.source_label == "YouTube clip"
    assert plan.context_result.source_url == plan.normalized_url
    assert [hint.value for hint in plan.context_result.context_hints] == [
        "YouTube clip",
        plan.normalized_url,
        "Nicolas Cage ZoneX trailer",
    ]
    assert [term.text for term in plan.context_result.glossary_terms] == [
        "Nyxara",
        "Freckelston",
    ]

    news_plan = build_source_capture_plan(
        source_url="https://www.telegraph.co.uk/news/2026/07/10/example-story/?utm_source=x#comments",
        source_label="Telegraph article",
        title="Example news article",
        selected_capture_options=["visible_page_text"],
        user_terms=["Reporter Name"],
    )
    assert news_plan.status == PLAN_STATUS_READY
    assert news_plan.normalized_url == (
        "https://www.telegraph.co.uk/news/2026/07/10/example-story/"
    )
    assert news_plan.source_id == "www.telegraph.co.uk/news/2026/07/10/example-story/"
    assert news_plan.adapter_name == "news_website"
    assert news_plan.adapter_display_name == "News Website"
    assert news_plan.selected_capture_options == ("visible_page_text",)
    assert news_plan.context_result.source_url == news_plan.normalized_url
    assert news_plan.context_result.source_label == "Telegraph article"
    assert [term.text for term in news_plan.context_result.glossary_terms] == [
        "Reporter Name",
    ]

    unsupported = build_source_capture_plan(
        source_url="https://example.com/watch?v=dQw4w9WgXcQ",
        selected_capture_options=["comments"],
    )
    assert unsupported.status == PLAN_STATUS_UNSUPPORTED_SOURCE
    assert unsupported.source_url == "https://example.com/watch?v=dQw4w9WgXcQ"
    assert unsupported.normalized_url == ""
    assert unsupported.source_id == ""
    assert unsupported.adapter_name == ""
    assert unsupported.selected_capture_options == (CAPTURE_COMMENTS,)
    assert unsupported.warnings == (
        "No source adapter supports the URL: https://example.com/watch?v=dQw4w9WgXcQ",
    )

    empty = build_source_capture_plan(source_url="")
    assert empty.status == PLAN_STATUS_UNSUPPORTED_SOURCE
    assert empty.warnings == ("No source adapter supports the URL: (empty)",)
    assert empty.selected_capture_options == ()


if __name__ == "__main__":
    run_self_test()
    print("Source capture plan self-test passed.")
