from source_adapter_registry_release import (
    SourceAdapterRegistryReleaseError,
    UPDATE_PACKAGE_SCHEMA_VERSION,
    build_source_adapter_registry_release,
)


def _registry_update_package():
    return {
        "schema_version": UPDATE_PACKAGE_SCHEMA_VERSION,
        "source_adapter_registry_update_id": "source_adapter_registry_update.example",
        "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
        "registry_update_status": "ADAPTER_REGISTRY_UPDATE_READY",
        "registry_rows": [
            {
                "adapter_id": "article",
                "display_name": "Article",
                "source_kind": "web",
                "domains": ["article.example"],
                "artifact_roles": ["metadata_json", "article_html_or_text"],
                "shared_stage_coverage": ["pipeline_closeout", "content_extraction"],
                "registered_for_shared_pipeline": True,
                "adapter_specific_module_required": False,
                "coverage_status": "ACCEPTED_SHARED_FIXTURE_COVERAGE",
            }
        ],
        "adapter_registry_release_handoff": {
            "handoff_status": "READY_FOR_SOURCE_ADAPTER_RELEASE_REVIEW",
            "manual_or_live_actions_started": False,
        },
    }


def _assert_raises(expected_error, expected_text, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except expected_error as exc:
        assert expected_text in str(exc), str(exc)
        return
    raise AssertionError(f"expected {expected_error.__name__}")


def test_build_ready_registry_release():
    package = build_source_adapter_registry_release(_registry_update_package())
    assert package["registry_release_status"] == "ADAPTER_REGISTRY_RELEASE_READY"
    assert package["adapter_count"] == 1
    assert package["released_adapter_count"] == 1
    assert package["issue_count"] == 0
    assert package["source_adapter_frozen_registry"]["registry_mutation_applied"] is False
    assert package["source_adapter_registry_rollout_handoff"]["handoff_status"] == "READY_FOR_APP_SOURCE_SELECTION_WIRING"
    assert package["operator_summary"]["manual_or_live_actions_started"] is False


def test_blocks_non_ready_update():
    source = _registry_update_package()
    source["registry_update_status"] = "ADAPTER_REGISTRY_UPDATE_BLOCKED"
    package = build_source_adapter_registry_release(source)
    assert package["registry_release_status"] == "ADAPTER_REGISTRY_RELEASE_BLOCKED"
    assert package["issue_count"] == 1


def test_blocks_unregistered_adapter():
    source = _registry_update_package()
    source["registry_rows"][0]["registered_for_shared_pipeline"] = False
    package = build_source_adapter_registry_release(source)
    assert package["registry_release_status"] == "ADAPTER_REGISTRY_RELEASE_BLOCKED"
    assert "not registered_for_shared_pipeline" in package["issues"][0]


def test_duplicate_adapter_id_is_error():
    source = _registry_update_package()
    source["registry_rows"].append(dict(source["registry_rows"][0]))
    _assert_raises(SourceAdapterRegistryReleaseError, "duplicate adapter_id", build_source_adapter_registry_release, source)


def test_rejects_local_path_fields():
    source = _registry_update_package()
    source["local_path"] = "C:/secret"
    _assert_raises(SourceAdapterRegistryReleaseError, "local path", build_source_adapter_registry_release, source)


if __name__ == "__main__":
    test_build_ready_registry_release()
    test_blocks_non_ready_update()
    test_blocks_unregistered_adapter()
    test_duplicate_adapter_id_is_error()
    test_rejects_local_path_fields()
    print("Source Adapter Registry Release self-test passed.")
