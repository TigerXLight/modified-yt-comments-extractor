from source_adapter_registry_release import build_source_adapter_registry_release
from source_adapter_registry_release_test import _registry_update_package
from source_adapter_registry_release_verifier import verify_source_adapter_registry_release


def test_verifier_accepts_ready_release():
    package = build_source_adapter_registry_release(_registry_update_package())
    result = verify_source_adapter_registry_release(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_mutating_record():
    package = build_source_adapter_registry_release(_registry_update_package())
    package["adapter_registry_release_record"]["registry_mutation_applied"] = True
    result = verify_source_adapter_registry_release(package)
    assert result["verified"] is False
    assert any("mutate registry" in issue for issue in result["issues"])


def test_verifier_rejects_path_fields():
    package = build_source_adapter_registry_release(_registry_update_package())
    package["source_adapter_frozen_registry"]["local_path"] = "C:/secret"
    result = verify_source_adapter_registry_release(package)
    assert result["verified"] is False
    assert any("local path" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_ready_release()
    test_verifier_rejects_mutating_record()
    test_verifier_rejects_path_fields()
    print("Source Adapter Registry Release verifier self-test passed.")
