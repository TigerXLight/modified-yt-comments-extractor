from source_adapter_registry_update import SourceAdapterRegistryUpdateError, build_source_adapter_registry_update


def _accepted_handoff():
    return {
        "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
        "handoff_status": "READY_FOR_ADAPTER_REGISTRY_UPDATE",
        "adapters": [
            {
                "adapter_id": "article",
                "coverage_status": "ACCEPTED_SHARED_FIXTURE_COVERAGE",
                "shared_stage_coverage": ["content_extraction", "pipeline_closeout"],
                "accepted_for_shared_pipeline": True,
                "display_name": "Article",
                "source_kind": "web",
                "domains": ["article.example"],
                "artifact_roles": ["article_html_or_text", "metadata_json"],
            }
        ],
    }


def _assert_raises(expected_error, expected_text, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except expected_error as exc:
        assert expected_text in str(exc), str(exc)
        return
    raise AssertionError(f"expected {expected_error.__name__}")


def test_build_ready_registry_update():
    package = build_source_adapter_registry_update(_accepted_handoff())
    assert package["registry_update_status"] == "ADAPTER_REGISTRY_UPDATE_READY"
    assert package["adapter_count"] == 1
    assert package["accepted_adapter_count"] == 1
    assert package["issue_count"] == 0
    assert package["registry_rows"][0]["adapter_id"] == "article"
    assert package["registry_rows"][0]["registered_for_shared_pipeline"] is True
    assert package["adapter_registry_release_handoff"]["handoff_status"] == "READY_FOR_SOURCE_ADAPTER_RELEASE_REVIEW"
    assert package["operator_summary"]["manual_or_live_actions_started"] is False


def test_existing_registry_rows_are_merged():
    existing = {
        "adapters": [
            {
                "adapter_id": "article",
                "display_name": "Existing Article",
                "source_kind": "web",
                "domains": ["old.example"],
                "artifact_roles": ["screenshot"],
                "shared_stage_coverage": ["artifact_collection"],
            }
        ]
    }
    package = build_source_adapter_registry_update(_accepted_handoff(), existing_registry=existing)
    row = package["registry_rows"][0]
    assert row["domains"] == ["article.example", "old.example"]
    assert row["artifact_roles"] == ["article_html_or_text", "metadata_json", "screenshot"]
    assert row["shared_stage_coverage"] == ["artifact_collection", "content_extraction", "pipeline_closeout"]


def test_blocked_handoff_does_not_mark_ready():
    handoff = _accepted_handoff()
    handoff["handoff_status"] = "BLOCKED_BY_FIXTURE_PIPELINE"
    package = build_source_adapter_registry_update(handoff)
    assert package["registry_update_status"] == "ADAPTER_REGISTRY_UPDATE_BLOCKED"
    assert package["issue_count"] == 1


def test_rejects_local_path_fields():
    handoff = _accepted_handoff()
    handoff["local_path"] = "C:/secret"
    _assert_raises(SourceAdapterRegistryUpdateError, "local path", build_source_adapter_registry_update, handoff)


def test_missing_acceptance_id_is_error():
    handoff = _accepted_handoff()
    handoff["source_adapter_coverage_acceptance_id"] = ""
    _assert_raises(SourceAdapterRegistryUpdateError, "source_adapter_coverage_acceptance_id", build_source_adapter_registry_update, handoff)


if __name__ == "__main__":
    test_build_ready_registry_update()
    test_existing_registry_rows_are_merged()
    test_blocked_handoff_does_not_mark_ready()
    test_rejects_local_path_fields()
    test_missing_acceptance_id_is_error()
    print("Source Adapter Registry Update self-test passed.")
