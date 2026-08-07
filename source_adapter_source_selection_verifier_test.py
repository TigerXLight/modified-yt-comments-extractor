from __future__ import annotations

from source_adapter_source_selection import build_source_adapter_source_selection, demo_rollout_package
from source_adapter_source_selection_verifier import verify_source_adapter_source_selection_package


def test_verifier_accepts_ready_package() -> None:
    package = build_source_adapter_source_selection(demo_rollout_package())
    verification = verify_source_adapter_source_selection_package(package)
    assert verification["verified"] is True
    assert verification["issue_count"] == 0
    assert verification["selection_status"] == "SOURCE_ADAPTER_SELECTION_READY"


def test_verifier_rejects_app_mutation() -> None:
    package = build_source_adapter_source_selection(demo_rollout_package())
    package["capture_route_index"] = dict(package["capture_route_index"])
    package["capture_route_index"]["app_files_mutated"] = True
    verification = verify_source_adapter_source_selection_package(package)
    assert verification["verified"] is False
    assert any("app_files_mutated" in issue for issue in verification["issues"])


def test_verifier_rejects_embedded_path() -> None:
    package = build_source_adapter_source_selection(demo_rollout_package())
    package["operator_summary"] = dict(package["operator_summary"])
    package["operator_summary"]["path"] = "C:/tmp"
    verification = verify_source_adapter_source_selection_package(package)
    assert verification["verified"] is False
    assert any("forbidden local path" in issue for issue in verification["issues"])


if __name__ == "__main__":
    test_verifier_accepts_ready_package()
    test_verifier_rejects_app_mutation()
    test_verifier_rejects_embedded_path()
    print("Source Adapter Source Selection verifier self-test passed.")
