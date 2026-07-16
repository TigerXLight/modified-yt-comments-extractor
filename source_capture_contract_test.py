from source_capture_contract import (
    COMPLETENESS_EXTERNAL_APPROVAL_REQUIRED,
    COMPLETENESS_METADATA_ONLY,
    COMPLETENESS_RUNTIME_DEPENDENT,
    COMPLETENESS_UNSUPPORTED,
    CONTRACT_STATUS_PLANNED_CONTRACT_ONLY,
    CONTRACT_STATUS_REQUIRES_EXTERNAL_SERVICE,
    CONTRACT_STATUS_SUPPORTED_BY_ADAPTER,
    CONTRACT_STATUS_UNKNOWN_OPTION,
    CONTRACT_STATUS_UNSUPPORTED_BY_ADAPTER,
    EXECUTION_EXISTING_RUNTIME_ELSEWHERE,
    EXECUTION_FUTURE_USER_TRIGGERED,
    EXECUTION_NO_RUNTIME_CAPTURE,
    build_source_capture_contract,
    source_capture_contract_to_dict,
    source_capture_contract_to_json,
    summarize_source_capture_contract,
)


VALID_ID = "aB3_dE-9xYz"
YOUTUBE_URL = f"https://www.youtube.com/watch?v={VALID_ID}"
NEWS_URL = "https://www.telegraph.co.uk/news/2026/07/10/example-story/?utm_source=x#comments"


def _item_by_option(contract):
    return {item.option_id: item for item in contract.items}


def test_youtube_comment_contract_is_existing_runtime_not_fetch() -> None:
    contract = build_source_capture_contract(
        source_url=YOUTUBE_URL,
        selected_capture_options=("comments", "replies", "live_chat"),
    )

    assert contract.plan_status == "ready"
    assert contract.adapter_name == "youtube"
    assert contract.normalized_url == YOUTUBE_URL
    items = _item_by_option(contract)
    for option_id in ("comments", "replies", "live_chat"):
        item = items[option_id]
        assert item.contract_status == CONTRACT_STATUS_SUPPORTED_BY_ADAPTER
        assert item.execution_mode == EXECUTION_EXISTING_RUNTIME_ELSEWHERE
        assert item.completeness_status == COMPLETENESS_RUNTIME_DEPENDENT
        assert item.adapter_supports_option is True
        assert item.requires_user_trigger is True
        assert any("does not fetch" in warning for warning in item.warnings)

    rendered = summarize_source_capture_contract(contract)
    assert "Source capture contract" in rendered
    assert "local source capture contract only" in rendered
    assert "comments: supported_by_adapter" in rendered


def test_news_website_contract_keeps_comments_unsupported_and_text_planned() -> None:
    contract = build_source_capture_contract(
        source_url=NEWS_URL,
        selected_capture_options=(
            "comments",
            "visible_page_text",
            "readable_article_text",
            "html_snapshot",
        ),
    )

    assert contract.plan_status == "ready"
    assert contract.adapter_name == "news_website"
    assert contract.normalized_url == (
        "https://www.telegraph.co.uk/news/2026/07/10/example-story/"
    )
    items = _item_by_option(contract)
    comments = items["comments"]
    assert comments.contract_status == CONTRACT_STATUS_UNSUPPORTED_BY_ADAPTER
    assert comments.execution_mode == EXECUTION_NO_RUNTIME_CAPTURE
    assert comments.completeness_status == COMPLETENESS_UNSUPPORTED
    assert comments.adapter_supports_option is False

    for option_id in ("visible_page_text", "readable_article_text", "html_snapshot"):
        item = items[option_id]
        assert item.contract_status == CONTRACT_STATUS_PLANNED_CONTRACT_ONLY
        assert item.execution_mode == EXECUTION_FUTURE_USER_TRIGGERED
        assert item.completeness_status == COMPLETENESS_METADATA_ONLY
        assert item.adapter_supports_option is False

    assert any(
        "comments-only capture must not force article-body extraction" in warning
        for warning in contract.warnings
    )
    assert any("raw saved HTML" in warning for warning in contract.warnings)


def test_archive_options_are_external_approval_boundaries() -> None:
    contract = build_source_capture_contract(
        source_url=YOUTUBE_URL,
        selected_capture_options=("archive_check", "archive_submit"),
    )

    items = _item_by_option(contract)
    check = items["archive_check"]
    submit = items["archive_submit"]

    assert check.contract_status == CONTRACT_STATUS_REQUIRES_EXTERNAL_SERVICE
    assert check.execution_mode == EXECUTION_NO_RUNTIME_CAPTURE
    assert check.completeness_status == COMPLETENESS_EXTERNAL_APPROVAL_REQUIRED
    assert check.sends_data_to_external_service is False

    assert submit.contract_status == CONTRACT_STATUS_REQUIRES_EXTERNAL_SERVICE
    assert submit.requires_user_confirmation is True
    assert submit.sends_data_to_external_service is True
    assert any("not executed" in warning for warning in submit.warnings)


def test_unknown_and_duplicate_options_are_reported_deterministically() -> None:
    contract = build_source_capture_contract(
        source_url=YOUTUBE_URL,
        selected_capture_options=("comments", "comments", "mystery_option"),
    )

    items = _item_by_option(contract)
    assert items["mystery_option"].contract_status == CONTRACT_STATUS_UNKNOWN_OPTION
    assert items["mystery_option"].completeness_status == COMPLETENESS_UNSUPPORTED
    assert any("Duplicate capture options ignored: comments" == warning for warning in contract.warnings)
    assert any("Unknown capture options ignored: mystery_option" == warning for warning in contract.warnings)


def test_unsupported_source_still_builds_local_contract() -> None:
    contract = build_source_capture_contract(
        source_url="https://example.invalid/post/123",
        selected_capture_options=("comments", "visible_page_text"),
    )

    assert contract.plan_status == "unsupported_source"
    assert contract.adapter_name == ""
    items = _item_by_option(contract)
    assert items["comments"].contract_status == CONTRACT_STATUS_UNSUPPORTED_BY_ADAPTER
    assert items["visible_page_text"].contract_status == CONTRACT_STATUS_PLANNED_CONTRACT_ONLY
    assert any("No source adapter supports" in warning for warning in contract.warnings)


def test_contract_dict_and_json_are_primitive_and_local_only() -> None:
    contract = build_source_capture_contract(
        source_url=NEWS_URL,
        selected_capture_options=("comments", "posts"),
    )

    data = source_capture_contract_to_dict(contract)
    assert data["adapter_name"] == "news_website"
    assert data["scope"] == contract.scope
    assert "no fetch" in data["scope"]
    assert data["provenance"]["adapter_name"] == "news_website"
    assert data["provenance"]["verification_notes"].startswith(
        "Source Capture Plan status:"
    )
    assert data["items"][0]["option_id"] == "comments"
    assert data["items"][1]["option_id"] == "posts"

    rendered_json = source_capture_contract_to_json(contract)
    assert '"adapter_name": "news_website"' in rendered_json
    assert '"option_id": "comments"' in rendered_json
    assert "fetch(" not in rendered_json
    assert "requests" not in rendered_json


def run_self_test() -> None:
    test_youtube_comment_contract_is_existing_runtime_not_fetch()
    test_news_website_contract_keeps_comments_unsupported_and_text_planned()
    test_archive_options_are_external_approval_boundaries()
    test_unknown_and_duplicate_options_are_reported_deterministically()
    test_unsupported_source_still_builds_local_contract()
    test_contract_dict_and_json_are_primitive_and_local_only()


if __name__ == "__main__":
    run_self_test()
    print("Source capture contract self-test passed.")
