from __future__ import annotations

from source_adapter_operator_named_site_smoke_execution_closeout import (
    HANDOFF_STATUS,
    STATUS,
    build_source_adapter_operator_named_site_smoke_execution_closeout,
    example_priority_site_pack_execution_closeout_package,
)


def main() -> None:
    package = build_source_adapter_operator_named_site_smoke_execution_closeout(
        example_priority_site_pack_execution_closeout_package(),
        named_site_selections={
            "generic_news_article": {
                "operator_named_site_id": "operator_named_site.telegraph_article",
                "source_url": "https://www.telegraph.co.uk/news/example/",
                "fixture_root": "fixtures/source_adapter/telegraph_article",
            }
        },
        operator_id="test_operator",
    ).as_dict()
    assert package["operator_named_site_smoke_execution_closeout_status"] == STATUS
    assert package["source_adapter_operator_named_site_smoke_execution_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["priority_site_pack_count"] >= 7
    assert package["manual_smoke_execution_count"] >= package["priority_site_pack_count"]
    acceptance = package["source_adapter_operator_named_site_receipt_acceptance_index"]
    assert acceptance["receipt_acceptance_status"] == "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_RECEIPTS_ACCEPTED"
    assert acceptance["keys_accounts_redacted_credential_references_ok"] is True
    rows = package["source_adapter_operator_named_site_local_fixture_execution_batch"]["local_fixture_execution_rows"]
    assert any(row["source_url"] == "https://www.telegraph.co.uk/news/example/" for row in rows)
    print("Source Adapter Operator Named Site Smoke Execution Closeout self-test passed.")


if __name__ == "__main__":
    main()
