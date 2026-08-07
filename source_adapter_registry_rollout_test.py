from source_adapter_registry_rollout import (
    REGISTRY_RELEASE_PACKAGE_SCHEMA_VERSION,
    SourceAdapterRegistryRolloutError,
    build_source_adapter_registry_rollout,
)


def _registry_release_package():
    return {
        "schema_version": REGISTRY_RELEASE_PACKAGE_SCHEMA_VERSION,
        "source_adapter_registry_release_id": "source_adapter_registry_release.example",
        "source_adapter_registry_update_id": "source_adapter_registry_update.example",
        "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
        "registry_release_status": "ADAPTER_REGISTRY_RELEASE_READY",
        "source_adapter_frozen_registry": {
            "adapters": [
                {
                    "adapter_id": "article",
                    "display_name": "Article",
                    "source_kind": "web",
                    "domains": ["article.example"],
                    "artifact_roles": ["metadata_json", "article_html_or_text"],
                    "shared_stage_coverage": ["pipeline_closeout", "content_extraction"],
                    "adapter_specific_module_required": False,
                    "release_status": "RELEASED_FOR_SHARED_PIPELINE",
                }
            ]
        },
        "source_adapter_registry_rollout_handoff": {
            "handoff_status": "READY_FOR_APP_SOURCE_SELECTION_WIRING",
            "registry_mutation_applied": False,
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


def test_build_ready_registry_rollout():
    package = build_source_adapter_registry_rollout(_registry_release_package())
    assert package["registry_rollout_status"] == "ADAPTER_REGISTRY_ROLLOUT_READY"
    assert package["adapter_count"] == 1
    assert package["issue_count"] == 0
    assert package["source_adapter_source_selection_wiring_plan"]["app_files_mutated"] is False
    assert package["source_adapter_registry_rollout_app_handoff"]["handoff_status"] == "READY_FOR_SOURCE_SELECTION_IMPLEMENTATION"
    assert package["operator_summary"]["manual_or_live_actions_started"] is False


def test_blocks_non_ready_release():
    source = _registry_release_package()
    source["registry_release_status"] = "ADAPTER_REGISTRY_RELEASE_BLOCKED"
    package = build_source_adapter_registry_rollout(source)
    assert package["registry_rollout_status"] == "ADAPTER_REGISTRY_ROLLOUT_BLOCKED"
    assert package["issue_count"] == 1


def test_blocks_non_ready_handoff():
    source = _registry_release_package()
    source["source_adapter_registry_rollout_handoff"]["handoff_status"] = "WAITING"
    package = build_source_adapter_registry_rollout(source)
    assert package["registry_rollout_status"] == "ADAPTER_REGISTRY_ROLLOUT_BLOCKED"
    assert "handoff_status" in package["issues"][0]


def test_duplicate_adapter_id_is_error():
    source = _registry_release_package()
    source["source_adapter_frozen_registry"]["adapters"].append(dict(source["source_adapter_frozen_registry"]["adapters"][0]))
    _assert_raises(SourceAdapterRegistryRolloutError, "duplicate adapter_id", build_source_adapter_registry_rollout, source)


def test_rejects_local_path_fields():
    source = _registry_release_package()
    source["absolute_path"] = "T:/secret"
    _assert_raises(SourceAdapterRegistryRolloutError, "local path", build_source_adapter_registry_rollout, source)


if __name__ == "__main__":
    test_build_ready_registry_rollout()
    test_blocks_non_ready_release()
    test_blocks_non_ready_handoff()
    test_duplicate_adapter_id_is_error()
    test_rejects_local_path_fields()
    print("Source Adapter Registry Rollout self-test passed.")
