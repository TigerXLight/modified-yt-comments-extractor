from __future__ import annotations

from source_adapter_fixture_authoring import SourceAdapterFixtureAuthoringError, build_source_adapter_fixture_authoring


def _matrix() -> dict:
    return {
        "adapter_fixture_matrix_id": "source_adapter_fixture_matrix.1234",
        "fixture_matrix": {
            "rows": [
                {
                    "adapter_id": "article",
                    "display_name": "Article",
                    "source_kind": "web",
                    "fixture_types": [
                        "saved_article_html_or_text",
                        "expected_content_extraction_json",
                        "expected_total_export_package_json",
                        "expected_pipeline_closeout_json",
                    ],
                    "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot"],
                    "shared_pipeline_stages": ["artifact_collection", "content_extraction", "pipeline_closeout"],
                }
            ]
        },
    }


def test_builds_templates_and_handoff() -> None:
    result = build_source_adapter_fixture_authoring(_matrix())
    assert result["schema_version"] == "source_adapter_fixture_authoring_package_v1"
    assert result["adapter_count"] == 1
    assert result["fixture_template_count"] == 4
    assert result["operator_summary"]["manual_or_live_actions_started"] is False
    assert result["fixture_review_handoff"]["handoff_status"] == "AWAITING_OPERATOR_FIXTURE_FILES"
    basenames = result["fixture_review_handoff"]["required_next_artifacts"]
    assert all("/" not in item and "\\" not in item for item in basenames)


def test_selects_adapter_ids() -> None:
    matrix = _matrix()
    matrix["fixture_matrix"]["rows"].append(
        {
            "adapter_id": "social",
            "fixture_types": ["saved_comments_json_or_text", "expected_comment_extraction_json"],
            "shared_pipeline_stages": ["comments_extraction", "pipeline_closeout"],
        }
    )
    result = build_source_adapter_fixture_authoring(matrix, adapter_ids=["social"])
    assert result["adapter_count"] == 1
    assert result["adapter_packets"][0]["adapter_id"] == "social"


def test_rejects_local_path_fields() -> None:
    matrix = _matrix()
    matrix["path"] = "C:/unsafe"
    try:
        build_source_adapter_fixture_authoring(matrix)
    except SourceAdapterFixtureAuthoringError as exc:
        assert "path" in str(exc)
    else:
        raise AssertionError("expected SourceAdapterFixtureAuthoringError")


if __name__ == "__main__":
    test_builds_templates_and_handoff()
    test_selects_adapter_ids()
    test_rejects_local_path_fields()
    print("Source Adapter Fixture Authoring self-test passed.")
