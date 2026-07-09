from capture_options import CAPTURE_ARCHIVE_CHECK, CAPTURE_COMMENTS
from source_capture_plan import (
    PLAN_STATUS_READY,
    PLAN_STATUS_UNSUPPORTED_SOURCE,
    build_source_capture_plan,
)


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


def run_self_test() -> None:
    plan = build_source_capture_plan(
        source_url=f" https://www.youtube.com/watch?v={VALID_ID}&t=30s ",
        source_label=" YouTube clip ",
        title=" Stream Highlights ",
        selected_capture_options=[
            " comments ",
            "archive_check",
            "comments",
            "unknown_option",
        ],
        user_terms=["Nyxara", " nyxara ", "Freckelston"],
    )
    assert plan.status == PLAN_STATUS_READY
    assert plan.source_url == f"https://www.youtube.com/watch?v={VALID_ID}&t=30s"
    assert plan.normalized_url == CANONICAL_URL
    assert plan.source_id == VALID_ID
    assert plan.adapter_name == "youtube"
    assert plan.adapter_display_name == "YouTube"
    assert plan.selected_capture_options == (CAPTURE_COMMENTS, CAPTURE_ARCHIVE_CHECK)
    assert plan.unknown_capture_options == ("unknown_option",)
    assert plan.duplicate_capture_options == (CAPTURE_COMMENTS,)
    assert plan.warnings == (
        "Unknown capture options ignored: unknown_option",
        "Duplicate capture options ignored: comments",
    )
    assert plan.context_result is not None
    assert plan.context_result.source_label == "YouTube clip"
    assert plan.context_result.source_url == CANONICAL_URL
    assert [hint.label for hint in plan.context_result.context_hints] == [
        "source_label",
        "source_url",
        "title",
    ]
    assert [term.text for term in plan.context_result.glossary_terms] == [
        "Nyxara",
        "Freckelston",
    ]

    unsupported = build_source_capture_plan(
        source_url="https://example.com/article",
        source_label="Example article",
        title="Example Title",
        selected_capture_options=["comments"],
        user_terms=["ExampleTerm"],
    )
    assert unsupported.status == PLAN_STATUS_UNSUPPORTED_SOURCE
    assert unsupported.source_url == "https://example.com/article"
    assert unsupported.normalized_url == ""
    assert unsupported.source_id == ""
    assert unsupported.adapter_name == ""
    assert unsupported.selected_capture_options == (CAPTURE_COMMENTS,)
    assert "No source adapter supports the URL" in unsupported.warnings[0]
    assert unsupported.context_result is not None
    assert unsupported.context_result.source_url == "https://example.com/article"
    assert unsupported.context_result.context_hints[2].value == "Example Title"
    assert unsupported.context_result.glossary_terms[0].text == "ExampleTerm"

    empty = build_source_capture_plan(source_url="   ")
    assert empty.status == PLAN_STATUS_UNSUPPORTED_SOURCE
    assert empty.source_url == ""
    assert empty.selected_capture_options == ()
    assert empty.context_result is not None
    assert empty.context_result.context_hints == ()
    assert empty.warnings == ("No source adapter supports the URL: (empty)",)


if __name__ == "__main__":
    run_self_test()
    print("Source capture plan self-test passed.")
