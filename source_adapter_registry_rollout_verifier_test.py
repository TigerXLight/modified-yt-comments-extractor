from source_adapter_registry_rollout import build_source_adapter_registry_rollout
from source_adapter_registry_rollout_test import _registry_release_package
from source_adapter_registry_rollout_verifier import verify_source_adapter_registry_rollout


def test_verifier_accepts_ready_rollout_package():
    package = build_source_adapter_registry_rollout(_registry_release_package())
    result = verify_source_adapter_registry_rollout(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_app_file_mutation():
    package = build_source_adapter_registry_rollout(_registry_release_package())
    package["source_adapter_source_selection_wiring_plan"]["app_files_mutated"] = True
    result = verify_source_adapter_registry_rollout(package)
    assert result["verified"] is False
    assert any("mutate app files" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_ready_rollout_package()
    test_verifier_rejects_app_file_mutation()
    print("Source Adapter Registry Rollout verifier self-test passed.")
