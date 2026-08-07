from __future__ import annotations

from source_adapter_capture_setup import build_source_adapter_capture_setup, demo_source_selection_package
from source_adapter_capture_setup_verifier import verify_source_adapter_capture_setup_package


def test_verifier_accepts_ready_capture_setup_package() -> None:
    package = build_source_adapter_capture_setup(demo_source_selection_package())
    verification = verify_source_adapter_capture_setup_package(package)
    assert verification["verified"] is True
    assert verification["issue_count"] == 0


def test_verifier_rejects_started_actions() -> None:
    package = build_source_adapter_capture_setup(demo_source_selection_package())
    package["lightweight_browser_capture_setup_handoff"] = dict(package["lightweight_browser_capture_setup_handoff"])
    package["lightweight_browser_capture_setup_handoff"]["manual_or_live_actions_started"] = True
    verification = verify_source_adapter_capture_setup_package(package)
    assert verification["verified"] is False
    assert verification["issue_count"] >= 1


if __name__ == "__main__":
    test_verifier_accepts_ready_capture_setup_package()
    test_verifier_rejects_started_actions()
    print("Source Adapter Capture Setup verifier self-test passed.")
