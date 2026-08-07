from __future__ import annotations

from source_adapter_fixture_matrix import SourceAdapterFixtureMatrixError, build_source_adapter_fixture_matrix
from source_adapter_fixture_matrix_verifier import verify_source_adapter_fixture_matrix


def _adapter_specs():
    return [
        {
            "adapter_id": "news_site",
            "display_name": "News Site",
            "source_kind": "web",
            "domains": ["news.example"],
            "url_patterns": ["https://news.example/*"],
            "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot"],
        },
        {
            "adapter_id": "social_thread",
            "display_name": "Social Thread",
            "source_kind": "social_thread",
            "domains": ["social.example"],
            "capture_surfaces": ["thread", "replies"],
            "unique_extraction_surface": True,
        },
    ]


def test_fixture_matrix_maps_many_adapters_to_shared_pipeline() -> None:
    matrix = build_source_adapter_fixture_matrix(_adapter_specs(), pipeline_closeout={"pipeline_closeout_id": "source_pipeline_closeout.1234"})
    assert matrix["schema_version"] == "source_adapter_fixture_matrix_v1"
    assert matrix["adapter_count"] == 2
    assert matrix["coverage_strategy"] == "one_framework_many_adapter_specs"
    assert matrix["pipeline_closeout_id"] == "source_pipeline_closeout.1234"
    assert matrix["operator_summary"]["manual_or_live_actions_started"] is False
    assert matrix["operator_summary"]["live_network_default"] is False
    assert matrix["shared_pipeline_binding"]["stage_count"] == 16
    rows = {row["adapter_id"]: row for row in matrix["fixture_matrix"]["rows"]}
    assert "expected_content_extraction_json" in rows["news_site"]["fixture_types"]
    assert "saved_comments_json_or_text" in rows["social_thread"]["fixture_types"]
    assert rows["social_thread"]["coverage_status"] == "NEEDS_ADAPTER_MODULE"
    assert verify_source_adapter_fixture_matrix(matrix)["verified"] is True


def test_rejects_duplicate_adapter_ids() -> None:
    try:
        build_source_adapter_fixture_matrix([{"adapter_id": "dup", "domains": ["one.example"]}, {"adapter_id": "dup", "domains": ["two.example"]}])
    except SourceAdapterFixtureMatrixError as exc:
        assert "duplicate adapter_id" in str(exc)
    else:
        raise AssertionError("duplicate adapter IDs should be rejected")


def test_rejects_local_path_fields() -> None:
    try:
        build_source_adapter_fixture_matrix([{"adapter_id": "bad", "domains": ["bad.example"], "local_path": "C:/secret"}])
    except SourceAdapterFixtureMatrixError as exc:
        assert "local path" in str(exc)
    else:
        raise AssertionError("local path fields should be rejected")


if __name__ == "__main__":
    test_fixture_matrix_maps_many_adapters_to_shared_pipeline()
    test_rejects_duplicate_adapter_ids()
    test_rejects_local_path_fields()
    print("Source Adapter Fixture Matrix self-test passed.")
